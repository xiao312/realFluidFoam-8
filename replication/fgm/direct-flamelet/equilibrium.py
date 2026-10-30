"""Independent HP-equilibrium limit, not finite-rate flamelet/source qualification."""
import csv
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
        import numpy as np
        gas, streams = gas_and_streams(ct, args, config, receipt)
        rows = []
        progress_indices = [gas.species_index(name) for name in ("CO2", "CO")]
        enthalpy_error = []
        elemental_error = []
        for fraction in np.linspace(0, 1, config["equilibrium_points"]):
            mixed_y = fraction * streams["fuel"]["Y"] + (1 - fraction) * streams["oxidizer"]["Y"]
            mixed_h = fraction * streams["fuel"]["h"] + (1 - fraction) * streams["oxidizer"]["h"]
            if fraction == 0 or fraction == 1:
                inlet = streams["fuel" if fraction == 1 else "oxidizer"]
                gas.TPY = inlet["temperature"], config["pressure_pa"], inlet["Y"]
                before = [gas.elemental_mass_fraction(element) for element in gas.element_names]
            else:
                gas.HPY = mixed_h, config["pressure_pa"], mixed_y
                before = [gas.elemental_mass_fraction(element) for element in gas.element_names]
                gas.equilibrate("HP", solver="auto", rtol=1e-9, max_steps=1000)
            after = [gas.elemental_mass_fraction(element) for element in gas.element_names]
            elemental_error.append(max(abs(a - b) for a, b in zip(after, before)))
            enthalpy_error.append(abs(gas.enthalpy_mass - mixed_h))
            row = [fraction, gas.T, gas.density, gas.enthalpy_mass,
                   sum(gas.Y[k] for k in progress_indices), *gas.Y]
            if not np.all(np.isfinite(row)) or np.min(gas.Y) < -1e-10 or abs(np.sum(gas.Y) - 1) > 1e-8:
                raise ValueError(f"Invalid equilibrium state at mixture fraction {fraction}")
            rows.append(row)
        with (args.out / "equilibrium.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Z_mass_mixing", "T_K", "rho_ideal_kg_m3", "h_J_kg", "Y_CO2_plus_CO"] +
                            ["Y_" + name for name in gas.species_names])
            writer.writerows(rows)
        diagnostics = {"points": len(rows), "peak_temperature_k": max(row[1] for row in rows),
                       "enthalpy_max_error_J_kg": max(enthalpy_error),
                       "element_mass_fraction_max_error": max(elemental_error),
                       "endpoint_policy": "exact original inlet states, not equilibrated pure streams",
                       "finite_rate_flamelet": False, "fgm_source_qualified": False,
                       "source_terms": "not exported; equilibrium rates are not flamelet progress sources",
                       "comparison_scope": "approximate chi_st approaching zero thermal/species limit only",
                       "transport_effects": "none: equilibrium path independent of transport closure"}
        write_json(args.out / "diagnostics.json", diagnostics)
        receipt.update(status="equilibrium_limit", elapsed_s=time.monotonic() - started,
                       completed_at=datetime.now(timezone.utc).isoformat(),
                       artifacts={name: sha256(args.out / name) for name in ("equilibrium.csv", "diagnostics.json")})
        write_json(args.out / "receipt.json", receipt)
        print("EQUILIBRIUM_RESULT " + str(diagnostics), flush=True)
        return 0
    except Exception as error:
        failure(args, receipt, error, time.monotonic() - started)
        print(f"FAILED: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 4


if __name__ == "__main__":
    sys.exit(main())
