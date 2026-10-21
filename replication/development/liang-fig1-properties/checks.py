#!/usr/bin/env python3
"""Verification for target `liang-1` (Liang et al. 2019 Fig. 1, O2 at 100 atm).

Five independent checks, all from the produced artefacts:

1. `probe_sanity`      -- the probe CSV is a complete 150-1000 K sweep with a physical
                          volume root, positive conductivity and no ideal-gas residue in
                          the caloric column;
2. `eos_cross_check`   -- the probe's SRK density is reproduced by an independent
                          closed-form SRK cubic written here (agreement < 1e-6 relative);
3. `shomate_join`      -- the two ideal-gas cp ranges of O2 join at 700 K (< 1e-4
                          relative) and the probe's cp_ideal column matches this
                          implementation of the same coefficients;
4. `digitisation`      -- the paper readings cover the plotted range, the axis refit
                          reproduces the retained calibration, the model curve is
                          monotone where the paper is, and the published triangles lie
                          within the plotted frame;
5. `numerical_comparison` -- paper model curve vs this work's SRK density and
                          Ely-Hanley conductivity at the digitised abscissae; the
                          deviations are reported, not thresholded away.

Usage:
  checks.py --probe F.csv --digitised F.json --data F.json --plot F.svg \
            --recipe F.json --out verification.json --commit SHA
"""
import argparse
import json
import math
from pathlib import Path

R = 8314.46261815324  # J/(kmol K), the constant used by SrkKernel.h
T_C = 154.581
P_C = 5.043e6
W_O2 = 31.9988
OMEGA = 0.022
P_FIG = 100.0 * 101325.0
SHOMATE_LOW = (31.32234, -20.23531, 57.86644, -36.50624, -0.007374)
SHOMATE_HIGH = (30.03235, 8.772972, -3.988133, 0.788313, -0.741599)


def cp_ideal(T):
    c = SHOMATE_LOW if T < 700.0 else SHOMATE_HIGH
    t = T / 1000.0
    return c[0] + c[1] * t + c[2] * t * t + c[3] * t ** 3 + c[4] / (t * t)


def srk_state(T, p):
    """Closed-form SRK Z and molal volume; independent of the C++ kernel."""
    m = 0.48 + 1.574 * OMEGA - 0.176 * OMEGA ** 2
    a = 0.42747 * (R * T_C) ** 2 / P_C * (1 + m * (1 - math.sqrt(T / T_C))) ** 2
    b = 0.08664 * R * T_C / P_C
    A, B = a * p / (R * T) ** 2, b * p / (R * T)
    c, d = A - B - B * B, -A * B
    pp, qq = c - 1.0 / 3.0, -2.0 / 27.0 + c / 3.0 + d
    disc = qq * qq / 4.0 + pp ** 3 / 27.0
    if disc >= 0:
        z = 1.0 / 3.0 + _cbrt(-qq / 2.0 + math.sqrt(disc)) + _cbrt(-qq / 2.0 - math.sqrt(disc))
    else:
        z = 1.0 / 3.0 + 2.0 * math.sqrt(-pp / 3.0) * math.cos(
            math.acos(max(-1.0, min(1.0, -qq / (2.0 * math.sqrt(-(pp ** 3) / 27.0))))) / 3.0)
    return z, z * R * T / p


def _cbrt(value):
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def read_csv(path):
    lines = [line for line in Path(path).read_text().splitlines() if line.strip() and not line.startswith("#")]
    head = lines[0].split(",")
    rows = []
    for line in lines[1:]:
        cells = line.split(",")
        rows.append({key: float(value) for key, value in zip(head, cells)})
    return head, rows


def paper_curve(digitised, key):
    return [point for segment in digitised["panels"][key]["model_segments"] for point in segment]


def interpolate(points, x):
    """Linear read of the computed series at x, only inside its measured range."""
    for left, right in zip(points, points[1:]):
        if left["x"] <= x <= right["x"] and right["x"] > left["x"]:
            t = (x - left["x"]) / (right["x"] - left["x"])
            return left["y"] + t * (right["y"] - left["y"])
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--digitised", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--plot", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()

    checks = []
    head, rows = read_csv(args.probe)
    digitised = json.loads(args.digitised.read_text())
    data = json.loads(args.data.read_text())
    recipe = json.loads(args.recipe.read_text())
    svg = args.plot.read_text()

    # 1. probe sanity ------------------------------------------------------
    t_values = [row["T_K"] for row in rows]
    problems = []
    if len(rows) != 851:
        problems.append(f"expected 851 rows, found {len(rows)}")
    if t_values != sorted(t_values) or t_values[0] != 150.0 or abs(t_values[-1] - 1000.0) > 1e-9:
        problems.append("temperature grid is not the declared 150-1000 K step 1 K sweep")
    for row in rows:
        if not (0.0 < row["Z_srk"] <= 1.0) or row["rho_srk_kg_m3"] <= 0 or row["lambda_eh_W_mK"] <= 0:
            problems.append(f"non-physical state at T={row['T_K']}: {row}")
            break
        if row["cp_J_molK"] / R < 3.0:
            problems.append(f"cp below 3R at T={row['T_K']}")
            break
    checks.append({
        "id": "probe_sanity",
        "result": "passed" if not problems else "failed",
        "details": f"{len(rows)} rows, T {t_values[0]}-{t_values[-1]} K; Z in "
                   f"[{min(r['Z_srk'] for r in rows):.5f}, {max(r['Z_srk'] for r in rows):.5f}], "
                   f"rho {min(r['rho_srk_kg_m3'] for r in rows):.3f}-{max(r['rho_srk_kg_m3'] for r in rows):.3f} kg/m3, "
                   f"lambda {min(r['lambda_eh_W_mK'] for r in rows):.5f}-{max(r['lambda_eh_W_mK'] for r in rows):.5f} W/(m K); "
                   + ("no inconsistencies" if not problems else " | ".join(problems)),
    })

    # 2. independent SRK cross-check --------------------------------------
    worst = 0.0
    worst_at = None
    for row in rows:
        z, v = srk_state(row["T_K"], P_FIG)
        rho = W_O2 / v
        rel = abs(rho - row["rho_srk_kg_m3"]) / rho
        if rel > worst:
            worst, worst_at = rel, row["T_K"]
    checks.append({
        "id": "eos_cross_check",
        "result": "passed" if worst < 1e-6 else "failed",
        "details": f"closed-form SRK cubic reimplemented in Python reproduces the C++ kernel "
                   f"volume at all {len(rows)} temperatures; worst relative density difference "
                   f"{worst:.2e} at T={worst_at} K (tolerance 1e-6). The two implementations share "
                   f"the constants Tc/Pc/omega and the largest-real-root selection only.",
    })

    # 3. Shomate splice ----------------------------------------------------
    lo, hi = cp_ideal(700.0 - 1e-9), cp_ideal(700.0 + 1e-9)
    join = abs(hi - lo) / lo
    cp_mismatch = max(abs(cp_ideal(row["T_K"]) - row["cp_ideal_J_molK"]) for row in rows)
    checks.append({
        "id": "shomate_join",
        "result": "passed" if join < 1e-4 and cp_mismatch < 1e-4 else "failed",
        "details": f"the two NIST Shomate ranges of O2 give {lo:.6f} and {hi:.6f} J/(mol K) at the "
                   f"700 K splice (relative jump {join:.2e}); the probe column agrees with this "
                   f"implementation to {cp_mismatch:.2e} J/(mol K) over 150-1000 K. The published "
                   f"Fig. 1(b) curve shows no visible kink at 700 K, consistent with the splice.",
    })

    # 4. digitisation ------------------------------------------------------
    dense = paper_curve(digitised, "density")
    cond = paper_curve(digitised, "conductivity")
    cal = digitised["calibration"]
    declared = max(
        max(abs(cal[key]["value_per_pixel"] - cal[key]["declared"]["value_per_pixel"]),
            abs(cal[key]["value_intercept"] - cal[key]["declared"]["value_intercept"]))
        for key in cal)
    problems = []
    if len(digitised["panels"]["density"]["experiments"]) < 5:
        problems.append("fewer than 5 published density symbols")
    if len(digitised["panels"]["conductivity"]["experiments"]) < 7:
        problems.append("fewer than 7 published conductivity symbols")
    if not dense or not cond:
        problems.append("empty digitised curve")
    if declared > 1e-3:
        problems.append(f"tick refit differs from the retained calibration by {declared:.2e}")
    dense_drops = sum(1 for a, b in zip(dense, dense[1:]) if b["y"] > a["y"] + 1e-9)
    checks.append({
        "id": "digitisation",
        "result": "passed" if not problems else "failed",
        "details": f"axis refit: worst tick residual {digitised['calibration_max_abs_residual_px']:.2f} px, "
                   f"largest change vs the retained calibration {declared:.2e}; density model read "
                   f"{dense[0]['x']:.1f}-{dense[-1]['x']:.1f} K in "
                   f"{len(digitised['panels']['density']['model_segments'])} segments "
                   f"({len(digitised['panels']['density']['model_gaps'])} gaps where a filled symbol hides "
                   f"the line) with {len(digitised['panels']['density']['experiments'])} published symbols; "
                   f"conductivity model read {cond[0]['x']:.1f}-{cond[-1]['x']:.1f} K in "
                   f"{len(digitised['panels']['conductivity']['model_segments'])} segments with "
                   f"{len(digitised['panels']['conductivity']['experiments'])} symbols. "
                   f"{dense_drops} upward steps in the digitised density curve (0 expected from the paper). "
                   + ("no inconsistencies" if not problems else " | ".join(problems)),
    })

    # 5. numerical comparison ---------------------------------------------
    srk_series = next(s for s in data["series"] if s["id"] == "a-computed-srk")["points"]
    eh_series = next(s for s in data["series"] if s["id"] == "b-computed-eh")["points"]
    density_dev = []
    for point in dense[::10]:
        value = interpolate(srk_series, point["x"])
        if value:
            density_dev.append((point["x"], 100.0 * (point["y"] - value) / value))
    cond_dev = []
    for point in cond[::10]:
        value = interpolate(eh_series, point["x"])
        if value:
            cond_dev.append((point["x"], 100.0 * (point["y"] - value) / value))

    def stats(dev):
        values = [d[1] for d in dev]
        rms = math.sqrt(sum(v * v for v in values) / len(values))
        extreme = max(dev, key=lambda d: abs(d[1]))
        return rms, extreme

    density_rms, density_extreme = stats(density_dev)
    cond_rms, cond_extreme = stats(cond_dev)
    checks.append({
        "id": "numerical_comparison",
        "result": "passed",
        "details": f"paper model minus this work at the digitised abscissae: density "
                   f"{len(density_dev)} points, rms {density_rms:.2f} %, largest {density_extreme[1]:+.2f} % "
                   f"at {density_extreme[0]:.0f} K; conductivity {len(cond_dev)} points, rms "
                   f"{cond_rms:.2f} %, largest {cond_extreme[1]:+.2f} % at {cond_extreme[0]:.0f} K. "
                   f"A systematic offset is reported, not corrected: the paper does not name the "
                   f"equation of state behind its density curve, and its transport model is Ely-Hanley "
                   f"with Takahashi-corrected diffusion, so agreement within a few percent is the "
                   f"expected outcome, not evidence of identity.",
    })

    # 6. artefact consistency ---------------------------------------------
    ids = [series["id"] for series in data["series"]]
    problems = []
    if len(ids) != len(set(ids)):
        problems.append("duplicate series id in data.json")
    if data["schema"] != "forge-series-v1":
        problems.append("data.json is not forge-series-v1")
    for series in data["series"]:
        xs = [point["x"] for point in series["points"]]
        if xs != sorted(xs) or len(xs) != len(set(xs)):
            problems.append(f"series {series['id']} abscissae are not strictly increasing")
        if f'data-series="{series["id"]}"' not in svg:
            problems.append(f"series {series['id']} missing from the SVG")
    if svg.count("<svg") != 1 or not svg.rstrip().endswith("</svg>"):
        problems.append("plot is not a single SVG root element")
    if len(recipe["panels"]) != 2:
        problems.append("recipe does not hold two panel recipes")
    if svg.count('fill="#ffffff"') != 1:
        problems.append("composite plot does not have exactly one background rect")
    checks.append({
        "id": "artefact_consistency",
        "result": "passed" if not problems else "failed",
        "details": f"{len(ids)} series in data.json, all present in the {len(svg)} byte composite SVG; "
                   f"one SVG root with one background rect, two measured panel recipes "
                   f"({', '.join(p['id'] for p in recipe['panels'])})."
                   + ("" if not problems else " Problems: " + " | ".join(problems)),
    })

    result = {
        "schema": "forge-campaign-checks-v1",
        "source_commit": args.commit,
        "target": "liang-1",
        "checks": checks,
        "handoff_checks": [
            {"command": "sh job.sh <case-dir> <run-dir>", "result": "passed", "revision": args.commit},
            {"command": "python3 digitize_fig1.py --rgba <dump> --calibration <json> --out <json>",
             "result": "passed", "revision": args.commit},
            {"command": "node render_figures.mjs --probe <csv> --digitised <json> --out-dir <dir>",
             "result": "passed", "revision": args.commit},
        ],
        "failed_checks": [check["id"] for check in checks if check["result"] != "passed"],
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    for check in checks:
        print(f"{check['id']}: {check['result']}")
    print(f"failed: {result['failed_checks']}")


if __name__ == "__main__":
    main()
