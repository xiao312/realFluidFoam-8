"""Independent stock Cantera ideal-LJ solve; no custom C++ adapters."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("mechanism", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--phi", type=float, default=1.4)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Output exists")
    record = {"phi": args.phi, "pressure_Pa": 10132500, "Tu_K": 298,
              "width_m": .01, "mechanism_sha256": hashlib.sha256(args.mechanism.read_bytes()).hexdigest(),
              "transport": "stock mixture-averaged LJ", "Soret": False}
    print(json.dumps(record), flush=True)
    if args.action == "plan":
        return
    import cantera as ct
    if ct.__version__ != "3.2.0":
        raise ValueError("Expected Cantera 3.2.0")
    args.output.mkdir(parents=True)
    gas = ct.Solution(args.mechanism)
    gas.set_equivalence_ratio(args.phi, "H2", "O2:0.21,N2:0.79")
    gas.TP = 298, 10132500
    flame = ct.FreeFlame(gas, width=.01)
    flame.transport_model = "mixture-averaged"
    flame.soret_enabled = False
    flame.flame.set_steady_tolerances(default=(1e-5, 1e-11))
    flame.set_max_grid_points(flame.flame, 6000)
    with (args.output/"refinement.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["slope", "curve", "points", "speed_cm_s", "Tb_K"])
        for slope, curve in [(.08, .1), (.03, .05), (.015, .025), (.0075, .0125), (.00375, .00625)]:
            flame.set_refine_criteria(ratio=3, slope=slope, curve=curve, prune=0)
            flame.solve(loglevel=1, auto=slope == .08)
            writer.writerow([slope, curve, len(flame.grid), 100*flame.velocity[0], flame.T[-1]])
            stream.flush()
    flame.save(args.output/"flame.yaml")
    (args.output/"manifest.json").write_text(json.dumps(record, indent=2)+"\n", newline="\n")


if __name__ == "__main__":
    main()
