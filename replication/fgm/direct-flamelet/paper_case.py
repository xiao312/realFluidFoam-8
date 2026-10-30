"""One bounded flamelet continuation case with raw checkpoints and honest residuals."""
import json
from pathlib import Path
import time
from datetime import datetime, timezone
import numpy as np
from common import failure, gas_and_streams, sha256, write_json


def state_metrics(flamelet, state, species_count, chi):
    rhs = flamelet.rhs(0.0, state).reshape((-1, species_count))
    scaled = rhs.copy()
    scaled[:, 0] /= 1000.0
    finite = bool(np.all(np.isfinite(state)) and np.all(np.isfinite(rhs)))
    return {"finite_state_and_rhs": finite,
            "scaled_rhs_max": float(abs(scaled).max()) if finite else None,
            "scaled_rhs_over_chi": float(abs(scaled).max() / chi) if finite else None,
            "temperature_rhs_max_K_s": float(abs(rhs[:, 0]).max()) if finite else None,
            "species_rhs_max_per_s": float(abs(rhs[:, 1:]).max()) if finite else None,
            "peak_temperature_k": float(state[::species_count].max()) if finite else None,
            "residual_scale": "temperature / 1000 K; each transported species mass fraction / 1"}


def save_checkpoint(args, receipt, flamelet, state, local_time, kind, diagnostics):
    temporary = args.out / "checkpoint.tmp.npz"
    np.savez_compressed(temporary, Z=flamelet.mixfrac_grid, interior_state=state,
                        local_relaxation_time_s=local_time)
    temporary.replace(args.out / "checkpoint.npz")
    write_json(args.out / "checkpoint.json", {
        "schema": "flamelet-continuation-checkpoint/v1", "state_file": "checkpoint.npz",
        "state_sha256": sha256(args.out / "checkpoint.npz"), "state_kind": kind,
        "source_commit": receipt["source_commit"], "mechanism_sha256": receipt["mechanism_sha256"],
        "config_sha256": receipt["config_sha256"], "case_id": receipt["branch_case"]["id"],
        "chi_st_s_inverse": receipt["branch_case"]["chi_st_s_inverse"],
        "spitfire_extension_sha256": receipt["spitfire_runtime"]["extension_sha256"],
        "local_relaxation_time_s": local_time, "diagnostics": diagnostics,
        "scientific_acceptance": False, "CFD_restart": False})


def read_seed(args, receipt, flamelet, settings):
    if args.seed_receipt is None:
        return None, {"used": False, "reason": "No predecessor checkpoint available; fresh HP equilibrium"}
    record = json.loads(args.seed_receipt.read_text())
    source = args.seed_receipt.parent / record["state_file"]
    if (record.get("schema") != "flamelet-continuation-checkpoint/v1" or
            record["state_file"] != "checkpoint.npz" or record["state_sha256"] != sha256(source)):
        raise ValueError("Seed checkpoint identity differs")
    for key in ("source_commit", "mechanism_sha256", "config_sha256"):
        if record[key] != receipt[key]:
            raise ValueError(f"Seed {key} differs from this continuation")
    if (record["case_id"] != receipt["branch_case"]["seed"] or
            record["spitfire_extension_sha256"] != receipt["spitfire_runtime"]["extension_sha256"]):
        raise ValueError("Seed predecessor or compiled runtime differs")
    raw = np.load(source)
    state = raw["interior_state"]
    if (raw["Z"].shape != (settings["grid_points"],) or
            not np.array_equal(raw["Z"], flamelet.mixfrac_grid) or
            state.shape != flamelet.current_interior_state.shape or not np.all(np.isfinite(state))):
        raise ValueError("Seed grid/state is incompatible or nonfinite")
    return state.copy(), {"used": True, "receipt_path": str(args.seed_receipt),
                          "receipt_sha256": sha256(args.seed_receipt), "checkpoint": record,
                          "interpretation": "Numerical flamelet initial guess; not a CFD restart or continuous strain history"}


def solve_case(args, config, receipt, settings, case):
    import cantera as ct
    from spitfire import ChemicalMechanismSpec, Flamelet, FlameletSpec
    from spitfire_identity import runtime_identity
    from transient_export import export_frames
    from transient_monitor import ClippingMonitor
    started = time.monotonic()
    try:
        if args.upstream_patch_receipt is None or args.upstream_cold_patch_receipt is None:
            raise ValueError("This cold-paper sequence requires both explicit runtime patch receipts")
        receipt["spitfire_runtime"] = runtime_identity(settings, args.upstream_patch_receipt, args.upstream_cold_patch_receipt)
        receipt.update(branch_case=case, branch_config_sha256=sha256(args.branch_config), operations=[])
        gas, streams = gas_and_streams(ct, args, config, receipt)
        mechanism = ChemicalMechanismSpec(cantera_solution=gas)
        fuel = mechanism.stream("TPX", (config["fuel"]["temperature_k"], config["pressure_pa"], config["fuel"]["mole_fractions"]))
        oxidizer = mechanism.stream("TPX", (config["oxidizer"]["temperature_k"], config["pressure_pa"], config["oxidizer"]["mole_fractions"]))
        def construct(initial):
            return Flamelet(FlameletSpec(mech_spec=mechanism, fuel_stream=fuel, oxy_stream=oxidizer,
                initial_condition=initial, grid_points=settings["grid_points"], grid_type="clustered",
                stoich_dissipation_rate=case["chi_st_s_inverse"], dissipation_rate_form="Peters",
                heat_transfer="adiabatic", include_enthalpy_flux=True, include_variable_cp=True))
        flamelet = construct("equilibrium")
        seed, provenance = read_seed(args, receipt, flamelet, settings)
        if seed is not None:
            flamelet = construct(seed)
        receipt.update(fresh_start=seed is None, flamelet_seed=provenance,
                       initialization_description=("Recorded predecessor flamelet numerical initial guess; no evolved CFD state" if seed is not None
                                                   else "Independent fresh HP equilibrium initial guess; no evolved CFD state"),
                       physical_time_interpretation="Local relaxation at this chi only; Newton steps have no physical time")
        receipt["models"].update(transport="unity-Lewis mixture-fraction flamelet",
            low_temperature_policy="Griffon constant-Cp extension below each species Tmin; separate Cantera diagnostics extrapolate NASA polynomials")
        initial = flamelet.current_interior_state.copy()
        np.savez_compressed(args.out / "initial.npz", Z=flamelet.mixfrac_grid, interior_state=initial)
        metric = lambda state: state_metrics(flamelet, state, gas.n_species, case["chi_st_s_inverse"])
        initial_metrics = metric(initial)
        save_checkpoint(args, receipt, flamelet, initial, 0.0, "numerical_initial_guess", initial_metrics)
        receipt["initial_state_diagnostics"] = initial_metrics
        write_json(args.out / "receipt.json", receipt)

        def newton(label):
            before = time.monotonic()
            try:
                _, iterations, returned = flamelet.steady_solve_newton(
                    initial_guess=flamelet.current_interior_state.copy(), tolerance=settings["steady_tolerance"],
                    max_iterations=settings["newton_iterations"], verbose=True)
                operation = {"kind": label, "returned_converged": bool(returned), "iterations": iterations}
            except Exception as error:
                operation = {"kind": label, "returned_converged": False, "error_type": type(error).__name__, "error": str(error)}
            operation.update(elapsed_s=time.monotonic() - before, actual_state_diagnostics=metric(flamelet.current_interior_state))
            receipt["operations"].append(operation)
            write_json(args.out / "receipt.json", receipt)
            return operation["actual_state_diagnostics"]

        current = newton("initial_short_newton")
        actual_time = 0.0
        if current["scaled_rhs_max"] is None or current["scaled_rhs_max"] > settings["steady_tolerance"]:
            duration = min(settings["maximum_relaxation_s"], max(settings["minimum_relaxation_s"],
                           settings["physical_timescale_count"] / case["chi_st_s_inverse"]))
            stop = {"reason": None, "checks": []}
            def stop_criteria(t, state, residual, n_steps):
                wall = time.monotonic() - started
                if n_steps % 25 and wall < settings["soft_wall_seconds"]:
                    return False
                measured = metric(state)
                stop["checks"].append({"time_s": float(t), "step": int(n_steps), **measured})
                save_checkpoint(args, receipt, flamelet, state, float(t), "accepted_physical_relaxation", measured)
                if not measured["finite_state_and_rhs"]:
                    stop["reason"] = "nonfinite_state_or_rhs"
                elif measured["scaled_rhs_max"] <= settings["steady_tolerance"]:
                    stop["reason"] = "steady_rhs_reached"
                elif wall >= settings["soft_wall_seconds"]:
                    stop["reason"] = "soft_wall_limit"
                return stop["reason"] is not None
            monitor = ClippingMonitor(gas)
            before = time.monotonic()
            try:
                with monitor:
                    library = flamelet.integrate_to_time(duration, stop_criteria=stop_criteria,
                        first_time_step=settings["first_step_s"], max_time_step=min(settings["max_step_s"], duration / 10),
                        transient_tolerance=settings["temporal_tolerance"], nonlinear_solve_tolerance=settings["nonlinear_tolerance"],
                        write_log=True, log_rate=100, extra_integrator_args={"maximum_time_step_count": settings["max_steps"]})
                actual_time = float(library.time_values[-1])
                np.savez_compressed(args.out / "relaxation.npz", local_time_s=library.time_values, Z=flamelet.mixfrac_grid,
                    T_K=library["temperature"], Y=np.stack([library["mass fraction " + name] for name in gas.species_names], axis=2))
                operation = {"kind": "physical_relaxation", "returned": True, "requested_duration_s": duration,
                             "actual_final_time_s": actual_time, "accepted_steps": len(library.time_values) - 1,
                             "reached_requested_time": abs(actual_time - duration) <= 1e-10 * duration}
            except Exception as error:
                operation = {"kind": "physical_relaxation", "returned": False,
                             "error_type": type(error).__name__, "error": str(error)}
                if hasattr(error, "states") and len(error.states):
                    np.savez_compressed(args.out / "relaxation-partial.npz", local_time_s=error.times, interior_state=error.states)
                    candidate = np.asarray(error.states[-1])
                    if np.all(np.isfinite(candidate)):
                        flamelet = construct(candidate)
                        actual_time = float(error.times[-1])
                        operation["last_partial_state_retained"] = True
            write_json(args.out / "clipping.json", monitor.summary())
            operation.update(elapsed_s=time.monotonic() - before, stop=stop)
            receipt["operations"].append(operation)
            write_json(args.out / "receipt.json", receipt)
            if time.monotonic() - started < settings["soft_wall_seconds"]:
                newton("post_relaxation_short_newton")

        state = flamelet.current_interior_state.copy()
        current = metric(state)
        solution = flamelet.make_library_from_interior_state(state)
        temperature = solution["temperature"]
        fractions = np.stack([solution["mass fraction " + name] for name in gas.species_names], axis=1)
        numerical = bool(current["finite_state_and_rhs"] and current["scaled_rhs_max"] <= settings["steady_tolerance"])
        receipt.update(final_state_diagnostics=current, steady_numerically_converged=numerical,
            local_physical_relaxation_time_s=actual_time,
            burning=bool(temperature.max() > max(config["fuel"]["temperature_k"], config["oxidizer"]["temperature_k"]) + 10),
            status="steady_converged_before_export" if numerical else "approximate_profile_before_export")
        np.savez_compressed(args.out / "steady.npz", Z=flamelet.mixfrac_grid, T_K=temperature, Y=fractions,
                            species=np.array(gas.species_names), pressure_pa=config["pressure_pa"], chi_st=case["chi_st_s_inverse"])
        save_checkpoint(args, receipt, flamelet, state, actual_time, "final_numerical_profile", current)
        write_json(args.out / "receipt.json", receipt)
        if not current["finite_state_and_rhs"]:
            raise ValueError("Final state or RHS is nonfinite; checkpoint retained")
        griffon_h = np.array([mechanism.griffon.enthalpy_mix(float(t), y) for t, y in zip(temperature, fractions)])
        mixed_h = (flamelet.mixfrac_grid * mechanism.griffon.enthalpy_mix(fuel.T, fuel.Y) +
                   (1 - flamelet.mixfrac_grid) * mechanism.griffon.enthalpy_mix(oxidizer.T, oxidizer.Y))
        receipt["griffon_enthalpy_mixing_max_error_J_kg"] = float(abs(griffon_h - mixed_h).max())
        export_settings = {"max_export_frames": 3, "table_z_points": 201, "table_eta_points": 41}
        diagnostics = export_frames(ct, gas, mechanism, streams, config, export_settings, receipt, args,
            flamelet.mixfrac_grid, np.array([0.0]), temperature[None, :], fractions[None, :, :], snapshot_kind="steady_flamelet")
        write_json(args.out / "diagnostics.json", diagnostics)
        receipt.update(status="steady_profile_exported" if numerical else "approximate_profile_exported_not_qualified",
                       elapsed_s=time.monotonic() - started, completed_at=datetime.now(timezone.utc).isoformat(),
                       artifacts={p.name: sha256(p) for p in args.out.iterdir() if p.is_file() and p.name != "receipt.json"})
        write_json(args.out / "receipt.json", receipt)
        return 0 if numerical else 5
    except Exception as error:
        failure(args, receipt, error, time.monotonic() - started)
        return 4
