#!/usr/bin/env python3
"""Peng-Robinson density of pure O2 at 100 atm for the Fig. 1 cross-check.

The PR implementation is the validated `../oxygen-properties/oxygen_properties.py`
module; this script only sweeps it at the pressure of Liang et al. (2019) Fig. 1 and
writes a two-column CSV (`T_K,rho_PR_kg_m3`) so the figure renderer can draw the second
equation-of-state variant.  Standard library only, no fitting.

Usage: pr_density.py --out F.csv [--pressure 10132500]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "oxygen-properties"))
from oxygen_properties import state  # noqa: E402  (module path is the checkout layout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pressure", type=float, default=100.0 * 101325.0)
    args = parser.parse_args()

    lines = ["T_K,rho_PR_kg_m3,p_Pa"]
    worst = 0.0
    for step in range(150, 1001):
        value = state(float(step), args.pressure)
        lines.append(f"{step},{value['rho_PR']:.6f},{args.pressure:.1f}")
        worst = max(worst, abs(value["rho_PR"]))
    args.out.write_text("\n".join(lines) + "\n")
    print(json.dumps({"rows": len(lines) - 1, "p_Pa": args.pressure, "max_rho": round(worst, 3)}))


if __name__ == "__main__":
    main()
