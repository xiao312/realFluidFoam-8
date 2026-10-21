#!/usr/bin/env python3
"""Compare the computed sweep against the digitised Cavalieri et al. (2025) Fig. 1.

Two reference sets are kept strictly separate, because they answer different questions:

  published curve  the model curve drawn in the paper (PDF vector paths).  A deviation here
                   measures how faithfully this implementation reproduces the paper's own
                   model, so it should be small and is dominated by digitisation error.
  published dots   the NIST comparison symbols printed in the same panels.  A deviation here
                   is a real physics difference between the model and the reference data.
                   It is reported as found; nothing is tuned to reduce it.

Both are `origin: paper` in the figure data; only the sweep carries `origin: computed`.

Run: python3 compare_reference.py --vector figure1-vector.json --sweep out/sweep.json \
        [--out out/comparison.json]
"""
import argparse
import json
import math
from pathlib import Path

# sweep.json already stores each property in the panel's own unit, so no rescaling here.
PANELS = {
    "a": {"quantity": "density", "unit": "kg/m3"},
    "b": {"quantity": "isobaric heat capacity", "unit": "kJ/(kg K)"},
    "c": {"quantity": "dynamic viscosity", "unit": "1e-4 Pa s"},
    "d": {"quantity": "thermal conductivity", "unit": "W/(m K)"},
}
FLUID = {"o2": "O2", "ch4": "CH4"}


def interpolate(points, x):
    """Linear interpolation on a strictly increasing curve; None outside its range."""
    if x < points[0][0] or x > points[-1][0]:
        return None
    lo, hi = 0, len(points) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if points[mid][0] <= x:
            lo = mid
        else:
            hi = mid
    x0, y0 = points[lo]
    x1, y1 = points[hi]
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def stats(pairs):
    """pairs: list of (x, computed, reference).  Relative deviations in per cent."""
    rel = [100.0 * (computed - reference) / reference for _, computed, reference in pairs]
    worst = max(range(len(rel)), key=lambda index: abs(rel[index]))
    return {
        "n": len(pairs),
        "max_abs_pct": abs(rel[worst]),
        "signed_at_max_pct": rel[worst],
        "at_x": pairs[worst][0],
        "computed_at_max": pairs[worst][1],
        "reference_at_max": pairs[worst][2],
        "rms_pct": math.sqrt(sum(value * value for value in rel) / len(rel)),
        "mean_pct": sum(rel) / len(rel),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vector", required=True)
    parser.add_argument("--sweep", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    vector = json.loads(Path(args.vector).read_text(encoding="utf-8"))
    sweep = json.loads(Path(args.sweep).read_text(encoding="utf-8"))
    if sweep.get("schema") != "forge-property-sweep-v1":
        raise SystemExit("unexpected sweep schema")

    result = {
        "target": "cavalieri2025-fig-1",
        "sweep": Path(args.sweep).name,
        "reference": {
            "file": Path(args.vector).name,
            "pdf_sha256": vector["source_pdf_sha256"],
            "form": vector["form"],
        },
        "model": sweep["model"],
        "pressure_Pa": sweep["pressure_Pa"],
        "panels": {},
    }

    for key, spec in PANELS.items():
        panel = vector["panels"][key]
        result["panels"][key] = {"quantity": spec["quantity"], "unit": spec["unit"],
                                 "series": {}}
        for fluid, name in FLUID.items():
            computed = [[row[0], row[1]]
                        for row in sweep["properties"][
                            {"a": "rho", "b": "cp", "c": "mu", "d": "kappa"}[key]][fluid]]
            curve_pairs = []
            for x, y in panel["curves"][fluid]:
                value = interpolate(computed, x)
                if value is not None:
                    curve_pairs.append((x, value, y))
            marker_pairs = []
            for entry in panel["markers"][fluid]:
                x, y = entry[0], entry[1]
                value = interpolate(computed, x)
                if value is not None:
                    marker_pairs.append((x, value, y))
            # Independent of this work: how far the symbols as printed sit from the curve as
            # printed.  If that digitisation-consistent difference is the size of the
            # computed-vs-symbols difference, the residual belongs to the published figure,
            # not to this implementation.
            dot_vs_curve = []
            for entry in panel["markers"][fluid]:
                value = interpolate(panel["curves"][fluid], entry[0])
                if value is not None:
                    dot_vs_curve.append((entry[0], value, entry[1]))
            result["panels"][key]["series"][fluid] = {
                "published_curve": stats(curve_pairs) if curve_pairs else None,
                "published_markers": stats(marker_pairs) if marker_pairs else None,
                "published_markers_vs_published_curve":
                    stats(dot_vs_curve) if dot_vs_curve else None,
                "markers_digitised": len(panel["markers"][fluid]),
                "markers_compared": len(marker_pairs),
                "markers_excluded": panel.get("marker_excluded", []),
            }

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    for key, spec in PANELS.items():
        for fluid in ("o2", "ch4"):
            series = result["panels"][key]["series"][fluid]
            line = f"{key} {fluid:3s} {spec['quantity']:24s}"
            for label, block in (("curve", series["published_curve"]),
                                 ("dots ", series["published_markers"])):
                if block is None:
                    line += f" | {label}: n/a"
                    continue
                line += (f" | {label}: max {block['max_abs_pct']:6.3f}% "
                         f"@ {block['at_x']:6.1f} K (n={block['n']}) rms {block['rms_pct']:5.3f}%")
            print(line)


if __name__ == "__main__":
    main()
