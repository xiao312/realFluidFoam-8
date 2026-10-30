"""Fresh physical mixture-fraction transient using pinned Sandia Spitfire."""
import json
import csv
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from common import failure, gas_and_streams, inputs, sha256, write_json


def arguments(parser):
    parser.add_argument("--integration-config", type=Path, required=True)


def main():
    args, config, receipt = inputs(__doc__, arguments)
    settings = json.loads(args.integration_config.read_text())
    if settings["schema"] != "spitfire-unsteady/v1":
        raise ValueError("Unknown unsteady settings schema")
    for name in ("steady_control_chi_st_s_inverse", "chi_st_s_inverse", "final_time_s", "first_step_s", "max_step_s", "temporal_tolerance", "nonlinear_tolerance"):
        if not isinstance(settings[name], (int, float)) or not 0 < settings[name] < float("inf"):
            raise ValueError(f"{name} must be positive and finite")
    for name in ("grid_points", "max_steps", "max_export_frames", "table_z_points", "table_eta_points"):
        if type(settings[name]) is not int or settings[name] < 3:
            raise ValueError(f"{name} must be an integer >= 3")
    if args.plan:
        print(json.dumps({"integration": settings, "initial_state": "fresh HP equilibrium", "physical_time_start_s": 0.0}))
        return 0
    started = time.monotonic()
    try:
        import cantera as ct
        import numpy as np
        import spitfire
        from spitfire import ChemicalMechanismSpec, Flamelet, FlameletSpec
        from spitfire.sqa import gitinfo
        from transient_export import check_rate_interface, export_frames
        from transient_monitor import ClippingMonitor
        if gitinfo.current_hexsha != settings["upstream_revision"]:
            raise ValueError("Spitfire installed revision differs from pinned integration settings")
        gas, streams = gas_and_streams(ct, args, config, receipt)
        mechanism = ChemicalMechanismSpec(cantera_solution=gas)
        fuel = mechanism.stream("TPX", (config["fuel"]["temperature_k"], config["pressure_pa"], config["fuel"]["mole_fractions"]))
        oxidizer = mechanism.stream("TPX", (config["oxidizer"]["temperature_k"], config["pressure_pa"], config["oxidizer"]["mole_fractions"]))
        flamelet = Flamelet(FlameletSpec(mech_spec=mechanism, fuel_stream=fuel, oxy_stream=oxidizer,
                            initial_condition="equilibrium", grid_points=settings["grid_points"], grid_type="clustered",
                            stoich_dissipation_rate=settings["chi_st_s_inverse"], dissipation_rate_form="Peters",
                            heat_transfer="adiabatic", include_enthalpy_flux=True, include_variable_cp=True))
        receipt["models"].update(transport="unity-Lewis mixture-fraction flamelet", upstream="Sandia Spitfire",
                                 upstream_revision=gitinfo.current_hexsha,
                                 low_temperature_policy="Griffon constant-Cp extension below species Tmin; differs from Cantera polynomial extrapolation",
                                 upstream_negative_state_clipping=True)
        receipt["integration"] = settings
        receipt["integration_config_sha256"] = sha256(args.integration_config)
        receipt["equations"] = "constant-pressure adiabatic unity-Lewis unsteady mixture-fraction species/temperature with variable-cp and enthalpy-flux terms"
        write_json(args.out / "receipt.json", receipt)
        rate_check = check_rate_interface(gas, mechanism, streams, config)
        write_json(args.out / "rate-interface.json", rate_check)
        if rate_check["max_peak_scaled_error"] > rate_check["limit"]:
            raise ValueError("Griffon/Cantera finite-rate kernel check failed; inspect rate-interface.json")
        np.savez_compressed(args.out / "initial.npz", Z=flamelet.mixfrac_grid,
                            interior_state=flamelet.initial_interior_state, chi=flamelet.dissipation_rate)
        control = Flamelet(FlameletSpec(mech_spec=mechanism, fuel_stream=fuel, oxy_stream=oxidizer,
                           initial_condition="equilibrium", grid_points=settings["grid_points"], grid_type="clustered",
                           stoich_dissipation_rate=settings["steady_control_chi_st_s_inverse"],
                           heat_transfer="adiabatic", include_enthalpy_flux=True, include_variable_cp=True))
        try:
            steady = control.compute_steady_state(tolerance=1e-6, verbose=True,
                        newton_args={"max_iterations": 20}, psitc_args={"max_iterations": 100},
                        transient_args={"extra_integrator_args": {"maximum_time_step_count": 1000}})
            np.savez_compressed(args.out / "steady-control.npz", Z=steady.mixture_fraction_values,
                                T_K=steady["temperature"], Y=np.stack([steady["mass fraction " + name] for name in gas.species_names], axis=1),
                                species=np.array(gas.species_names), chi_st=settings["steady_control_chi_st_s_inverse"])
            # The upstream time-step cap can return before steady convergence.
            # This diagnostic uses the exact pinned operator and its variable scales.
            residual = float(np.max(abs(control._adiabatic_rhs(0.0, control.current_interior_state) / control._variable_scales)))
            receipt["steady_control"] = {"solver_returned": True, "scaled_rhs_max": residual,
                                         "steady_residual_below_1e_minus_6": residual <= 1e-6,
                                         "peak_temperature_k": float(np.max(steady["temperature"])),
                                         "artifact_sha256": sha256(args.out / "steady-control.npz"),
                                         "scientific_acceptance": False, "reused_for_transient": False}
        except Exception as control_error:
            receipt["steady_control"] = {"solver_returned": False, "error_type": type(control_error).__name__,
                                         "error": str(control_error), "scientific_acceptance": False,
                                         "reused_for_transient": False}
            if hasattr(control_error, "times") and hasattr(control_error, "states"):
                np.savez_compressed(args.out / "steady-control-partial.npz", time_s=control_error.times,
                                    interior_state=control_error.states, Z=control.mixfrac_grid)
                receipt["steady_control"]["partial_sha256"] = sha256(args.out / "steady-control-partial.npz")
        write_json(args.out / "receipt.json", receipt)
        monitor = ClippingMonitor(gas)
        try:
            with monitor:
                solution = flamelet.integrate_to_time(settings["final_time_s"], first_time_step=settings["first_step_s"],
                      max_time_step=settings["max_step_s"], transient_tolerance=settings["temporal_tolerance"],
                      nonlinear_solve_tolerance=settings["nonlinear_tolerance"], write_log=True, log_rate=100,
                      extra_integrator_args={"maximum_time_step_count": settings["max_steps"]})
        except Exception as transient_error:
            if hasattr(transient_error, "times") and hasattr(transient_error, "states"):
                np.savez_compressed(args.out / "trajectory-partial.npz", time_s=transient_error.times,
                                    interior_state=transient_error.states, Z=flamelet.mixfrac_grid)
                receipt["partial_transient"] = {"artifact_sha256": sha256(args.out / "trajectory-partial.npz"),
                                                "physical_times_count": len(transient_error.times)}
            raise
        finally:
            write_json(args.out / "clipping.json", monitor.summary())
            with (args.out / "clipping.csv").open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["physical_time_s", "negative_species_entries", "minimum_species_before_clip",
                                 "minimum_temperature_before_clip_K", "maximum_species_correction", "maximum_element_correction"])
                writer.writerows(monitor.rows)
        times = solution.time_values
        z = solution.mixture_fraction_values
        temperatures = solution["temperature"]
        fractions = np.stack([solution["mass fraction " + name] for name in gas.species_names], axis=2)
        np.savez_compressed(args.out / "trajectory.npz", time_s=times, Z=z, T_K=temperatures, Y=fractions,
                            species=np.array(gas.species_names), pressure_pa=config["pressure_pa"])
        receipt.update(status="transient_integrated", actual_final_time_s=float(times[-1]), accepted_steps=len(times) - 1,
                       artifacts={name: sha256(args.out / name) for name in ("initial.npz", "steady-control.npz", "trajectory.npz", "clipping.json", "clipping.csv", "rate-interface.json") if (args.out / name).is_file()})
        write_json(args.out / "receipt.json", receipt)
        if not np.all(np.isfinite(temperatures)) or not np.all(np.isfinite(fractions)):
            raise ValueError("Nonfinite transient solution; raw trajectory retained")
        if times[0] != 0.0 or abs(times[-1] - settings["final_time_s"]) > 1e-10 * settings["final_time_s"]:
            raise ValueError("Integrator did not cover the requested physical time interval; raw trajectory retained")
        metrics = export_frames(ct, gas, mechanism, streams, config, settings, receipt, args, z, times, temperatures, fractions)
        write_json(args.out / "diagnostics.json", metrics)
        receipt.update(status="transient_exported_not_accepted", elapsed_s=time.monotonic() - started,
                       completed_at=datetime.now(timezone.utc).isoformat(),
                       artifacts={name: sha256(args.out / name) for name in
                                  ("initial.npz", "steady-control.npz", "trajectory.npz", "diagnostics.json", "family-manifest.json", "phase-metadata.json", "clipping.json", "clipping.csv", "rate-interface.json") if (args.out / name).is_file()})
        write_json(args.out / "receipt.json", receipt)
        print(json.dumps({"status": receipt["status"], "frames": metrics["selected_frames"],
                          "progress_st_start_end": metrics["progress_st_start_end"]}))
        return 0
    except Exception as error:
        failure(args, receipt, error, time.monotonic() - started)
        print(f"FAILED: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
