"""Bounded independent steady mixture-fraction flamelets; no CFD restart input."""
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from common import failure, gas_and_streams, inputs, sha256, write_json


def arguments(parser):
    parser.add_argument("--branch-config", type=Path, required=True)
    parser.add_argument("--case-index", type=int)
    parser.add_argument("--upstream-patch-receipt", type=Path)
    parser.add_argument("--upstream-cold-patch-receipt", type=Path)


def validate(settings):
    if settings["schema"] != "spitfire-steady-branch/v1":
        raise ValueError("Unknown steady branch schema")
    rates = settings["chi_st_s_inverse"]
    if not rates or any(not math.isfinite(value) or value <= 0 for value in rates) or len(set(rates)) != len(rates):
        raise ValueError("Scalar dissipation rates must be distinct positive finite values")
    for key in ("grid_points", "newton_iterations", "psitc_iterations", "fallback_time_steps", "per_case_wall_seconds"):
        if type(settings[key]) is not int or settings[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if settings["grid_points"] < 10 or not 0 < settings["steady_tolerance"] < 1:
        raise ValueError("Invalid steady grid or tolerance")


def solve_case(args, config, receipt, settings):
    import cantera as ct
    import numpy as np
    from spitfire import ChemicalMechanismSpec, Flamelet, FlameletSpec
    from spitfire.sqa import gitinfo
    from transient_export import export_frames
    started = time.monotonic()
    flamelet = None
    try:
        from spitfire_identity import runtime_identity
        receipt["spitfire_runtime"] = runtime_identity(settings, args.upstream_patch_receipt, args.upstream_cold_patch_receipt)
        chi = settings["chi_st_s_inverse"][args.case_index]
        gas, streams = gas_and_streams(ct, args, config, receipt)
        mechanism = ChemicalMechanismSpec(cantera_solution=gas)
        fuel = mechanism.stream("TPX", (config["fuel"]["temperature_k"], config["pressure_pa"], config["fuel"]["mole_fractions"]))
        oxidizer = mechanism.stream("TPX", (config["oxidizer"]["temperature_k"], config["pressure_pa"], config["oxidizer"]["mole_fractions"]))
        flamelet = Flamelet(FlameletSpec(mech_spec=mechanism, fuel_stream=fuel, oxy_stream=oxidizer,
                            initial_condition="equilibrium", grid_points=settings["grid_points"], grid_type="clustered",
                            stoich_dissipation_rate=chi, dissipation_rate_form="Peters", heat_transfer="adiabatic",
                            include_enthalpy_flux=True, include_variable_cp=True))
        receipt["models"].update(transport="unity-Lewis mixture-fraction flamelet", upstream="Sandia Spitfire",
                                 upstream_revision=gitinfo.current_hexsha,
                                 low_temperature_policy="Griffon constant-Cp extension below species Tmin; Cantera diagnostic properties extrapolate NASA polynomials",
                                 temperature_diagnostic_interpretation="steady Griffon thermal model; not identical to Cantera cold extrapolation",
                                 upstream_negative_state_clipping=True)
        receipt.update(chi_st_s_inverse=chi, numerical_time_is_physical=False,
                       steady_initialization="independent fresh HP equilibrium; no previous case or CFD field loaded",
                       branch_config_sha256=sha256(args.branch_config))
        write_json(args.out / "receipt.json", receipt)
        np.savez_compressed(args.out / "initial.npz", Z=flamelet.mixfrac_grid,
                            interior_state=flamelet.initial_interior_state, chi=flamelet.dissipation_rate)
        solution = flamelet.compute_steady_state(tolerance=settings["steady_tolerance"], verbose=True,
                         newton_args={"max_iterations": settings["newton_iterations"]},
                         psitc_args={"max_iterations": settings["psitc_iterations"]},
                         transient_args={"extra_integrator_args": {"maximum_time_step_count": settings["fallback_time_steps"]}})
        temperature = solution["temperature"]
        fractions = np.stack([solution["mass fraction " + name] for name in gas.species_names], axis=1)
        np.savez_compressed(args.out / "steady.npz", Z=flamelet.mixfrac_grid, T_K=temperature,
                            Y=fractions, species=np.array(gas.species_names), pressure_pa=config["pressure_pa"], chi_st=chi)
        rhs = flamelet.rhs(0.0, flamelet.current_interior_state).reshape((-1, gas.n_species))
        scaled = rhs.copy()
        scaled[:, 0] /= 1000.0  # upstream temperature scale; species mass fractions have unit scale
        residual = float(np.max(abs(scaled)))
        finite = bool(np.all(np.isfinite(temperature)) and np.all(np.isfinite(fractions)) and math.isfinite(residual))
        numerical = finite and residual <= settings["steady_tolerance"]
        receipt.update(status="steady_returned", steady_numerically_converged=numerical,
                       scaled_rhs_max=residual if math.isfinite(residual) else None,
                       temperature_rhs_max_K_s=float(np.max(abs(rhs[:, 0]))) if finite else None,
                       species_rhs_max_per_s=float(np.max(abs(rhs[:, 1:]))) if finite else None,
                       peak_temperature_k=float(np.max(temperature)) if finite else None,
                       burning=bool(np.max(temperature) > max(config["fuel"]["temperature_k"], config["oxidizer"]["temperature_k"]) + 10) if finite else False,
                       artifacts={name: sha256(args.out / name) for name in ("initial.npz", "steady.npz")})
        write_json(args.out / "receipt.json", receipt)
        if not finite:
            raise ValueError("Nonfinite steady output; raw state retained")
        export_settings = {"max_export_frames": 3, "table_z_points": 201, "table_eta_points": 41}
        metrics = export_frames(ct, gas, mechanism, streams, config, export_settings, receipt, args,
                                flamelet.mixfrac_grid, np.array([0.0]), temperature[None, :], fractions[None, :, :],
                                snapshot_kind="steady_flamelet")
        write_json(args.out / "diagnostics.json", metrics)
        receipt.update(status="steady_profile_exported" if numerical else "steady_profile_unconverged",
                       elapsed_s=time.monotonic() - started, completed_at=datetime.now(timezone.utc).isoformat(),
                       artifacts={name: sha256(args.out / name) for name in
                                  ("initial.npz", "steady.npz", "diagnostics.json", "family-manifest.json", "phase-metadata.json")})
        write_json(args.out / "receipt.json", receipt)
        return 0 if numerical else 5
    except Exception as error:
        if flamelet is not None:
            np.savez_compressed(args.out / "available-state-on-failure.npz", Z=flamelet.mixfrac_grid,
                                interior_state=flamelet.current_interior_state)
            receipt["failure_state_note"] = "Last state exposed by upstream; may be the original initial guess"
        if hasattr(error, "times") and hasattr(error, "states"):
            np.savez_compressed(args.out / "partial-numerical-history.npz", times=error.times, interior_state=error.states)
        failure(args, receipt, error, time.monotonic() - started)
        return 4


def run_branch(args, receipt, settings):
    started = time.monotonic()
    summaries = []
    receipt["branch_settings"] = settings
    receipt["branch_config_sha256"] = sha256(args.branch_config)
    write_json(args.out / "receipt.json", receipt)
    for index, chi in enumerate(settings["chi_st_s_inverse"]):
        output = args.out / f"chi-{index:02d}"
        command = [sys.executable, str(Path(__file__).resolve()), "--config", str(args.config.resolve()),
                   "--branch-config", str(args.branch_config.resolve()), "--case-index", str(index),
                   "--mechanism", str(args.mechanism.resolve()), "--mechanism-sha256", args.mechanism_sha256,
                   "--source-commit", args.source_commit, "--environment-sha256", args.environment_sha256,
                   "--out", str(output.resolve())]
        if args.upstream_patch_receipt is not None:
            command += ["--upstream-patch-receipt", str(args.upstream_patch_receipt.resolve())]
        if args.upstream_cold_patch_receipt is not None:
            command += ["--upstream-cold-patch-receipt", str(args.upstream_cold_patch_receipt.resolve())]
        case_started = time.monotonic()
        with (args.out / f"chi-{index:02d}.log").open("w") as log:
            try:
                completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=settings["per_case_wall_seconds"])
                result = {"process_exit": completed.returncode, "wall_limited": False}
            except subprocess.TimeoutExpired:
                result = {"process_exit": None, "wall_limited": True}
        result.update(chi_st_s_inverse=chi, elapsed_s=time.monotonic() - case_started,
                      receipt_path=f"chi-{index:02d}/receipt.json")
        if (output / "receipt.json").is_file():
            actual = json.loads((output / "receipt.json").read_text())
            result.update(receipt_sha256=sha256(output / "receipt.json"), status=actual["status"],
                          steady_numerically_converged=actual.get("steady_numerically_converged", False),
                          peak_temperature_k=actual.get("peak_temperature_k"), scaled_rhs_max=actual.get("scaled_rhs_max"))
        summaries.append(result)
        write_json(args.out / "branch-summary.json", {"cases": summaries, "scientific_acceptance": False})
        print(json.dumps(result), flush=True)
    receipt.update(status="branch_completed_with_recorded_outcomes", elapsed_s=time.monotonic() - started,
                   completed_at=datetime.now(timezone.utc).isoformat(), cases=summaries,
                   artifacts={"branch-summary.json": sha256(args.out / "branch-summary.json")})
    write_json(args.out / "receipt.json", receipt)
    return 0 if all(row["process_exit"] == 0 for row in summaries) else 5


def main():
    args, config, receipt = inputs(__doc__, arguments)
    settings = json.loads(args.branch_config.read_text())
    validate(settings)
    if args.case_index is not None and not 0 <= args.case_index < len(settings["chi_st_s_inverse"]):
        raise ValueError("case-index outside configured branch")
    if args.plan:
        print(json.dumps({"branch": settings, "independent_initialization": True,
                          "upper_wall_seconds": len(settings["chi_st_s_inverse"]) * settings["per_case_wall_seconds"]}))
        return 0
    if args.case_index is not None:
        return solve_case(args, config, receipt, settings)
    return run_branch(args, receipt, settings)


if __name__ == "__main__":
    raise SystemExit(main())
