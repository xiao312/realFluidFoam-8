"""Fresh canonical Cantera counterflow; no saved-state or Gaussian-kernel import."""
import sys
import time
from datetime import datetime, timezone
from common import failure, gas_and_streams, inputs, sha256, write_json


def main():
    args, config, receipt = inputs(__doc__)
    if args.plan:
        return 0
    started = time.monotonic()
    try:
        import cantera as ct
        from diagnostics import export_flame
        gas, streams = gas_and_streams(ct, args, config, receipt)
        flame = ct.CounterflowDiffusionFlame(gas, width=config["width_m"])
        flame.P = config["pressure_pa"]
        for name, inlet in (("fuel", flame.fuel_inlet), ("oxidizer", flame.oxidizer_inlet)):
            inlet.T = config[name]["temperature_k"]
            inlet.X = config[name]["mole_fractions"]
            inlet.mdot = config[name + "_mdot_kg_m2_s"]
        lower_bound = 0.5 * min(config[name]["temperature_k"] for name in ("fuel", "oxidizer"))
        flame.flame.set_bounds(T=(lower_bound, 2 * gas.max_temp))
        flame.max_grid_points = config["max_grid_points"]
        flame.max_time_step_count = config["max_time_steps"]
        flame.set_refine_criteria(**config["refine"])
        receipt["solver"] = {"class": "CounterflowDiffusionFlame", "auto": True,
                             "initial_guess": "Cantera standard infinitely-fast chemistry; no external state",
                             "temperature_bounds_k": [lower_bound, 2 * gas.max_temp],
                             "steady_and_transient_tolerances": "Cantera 3.2.0 defaults",
                             "pressure_pa": flame.P, "radiation_enabled": flame.radiation_enabled}
        write_json(args.out / "receipt.json", receipt)
        flame.set_initial_guess()
        flame.solve(loglevel=1, auto=True)
        receipt.update(status="solver_converged", solver_converged=True,
                       physical_export_qualified=False, elapsed_s=time.monotonic() - started)
        write_json(args.out / "receipt.json", receipt)
        flame.save(str(args.out / "solution.yaml"), name="fresh-counterflow", overwrite=False,
                   description="Canonical fresh solve. Numerical convergence is not scientific acceptance.")
        receipt["artifacts"] = {"solution.yaml": sha256(args.out / "solution.yaml")}
        write_json(args.out / "receipt.json", receipt)
        metrics = export_flame(flame, gas, streams, config, args.out)
        write_json(args.out / "diagnostics.json", metrics)
        receipt.update(status="converged_flame", elapsed_s=time.monotonic() - started,
                       physical_export_qualified=True,
                       completed_at=datetime.now(timezone.utc).isoformat(),
                       artifacts={name: sha256(args.out / name) for name in ("profile.csv", "solution.yaml", "diagnostics.json")})
        write_json(args.out / "receipt.json", receipt)
        print("FLAME_RESULT " + str(metrics), flush=True)
        return 0
    except Exception as error:
        failure(args, receipt, error, time.monotonic() - started)
        if receipt.get("solver_converged"):
            receipt.update(status="diagnostic_failed", physical_export_qualified=False)
            write_json(args.out / "receipt.json", receipt)
        print(f"FAILED: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 4


if __name__ == "__main__":
    sys.exit(main())
