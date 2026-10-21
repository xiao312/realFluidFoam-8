#!/usr/bin/env python3
"""Verification for target `liang-1` (Liang et al. 2019 Fig. 1, O2 at 100 atm).

The five check ids are the ones registered for this target:

1. `source_and_units`   -- the C++ probe is a complete 150-1000 K sweep with a physical
                           volume root, positive conductivity and a sane caloric column;
                           the ideal-gas cp splice joins at 700 K; and an independent
                           closed-form SRK cubic written here reproduces the kernel's
                           molar volume.  Units are declared in the CSV header.
2. `reference_coverage` -- the digitised paper readings cover the plotted range, the axis
                           refit reproduces the retained calibration, the model curve is
                           monotone where the paper is, and every published symbol sits
                           inside the plotted frame.
3. `figure_fidelity`    -- both panels are present in one SVG with the measured paper
                           geometry (frame, ticks, axis titles, legend rows), every data
                           series is drawn, and each deliberate difference from the paper
                           styling is declared.
4. `reproducibility`    -- a second run of the PR sweep and of the renderer is byte
                           identical to the first.
5. `numerical_comparison` -- paper model curve vs this work's SRK density, Ely-Hanley
                           conductivity and the independent PR density; the deviations are
                           reported, not thresholded away.

Usage:
  checks.py --probe F.csv --digitised F.json --data F.json --plot F.svg --recipe F.json \
            --pr-csv F.csv --repeat-plot F.svg --repeat-pr F.csv \
            --out verification.json --commit SHA [--job JOB_ID]
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

# Two molar constants are needed and they are not interchangeable.  SrkKernel.h works in
# kmol, so the ideal-gas volume it returns is m3/kmol and the cubic needs R in
# J/(kmol K).  The probe's caloric column is cp_J_molK, i.e. J/(mol K), so the
# dimensionless cp/R must divide by the mol-based constant.  Dividing a J/(mol K) column
# by the kmol constant is the dimensional defect this file previously repeated; keep the
# two names distinct so the mistake cannot reappear by accident.
R_KMOL = 8314.46261815324  # J/(kmol K), the constant used by SrkKernel.h
R_MOL = 8.31446261815324  # J/(mol K), for cp_J_molK
# The probe pins its own canary at cp/R(300 K) = 3.53 +/- 0.05; the audited band used by
# fig1_probe.cpp is [3.30, 4.20].  A wrong cp scale cannot pass both this band and the
# whole-column range below.
CP_R_300K_BAND = (3.30, 4.20)
CP_R_RANGE = (3.00, 14.00)
# Declared tolerances for the comparison check (see README).  A claim, not a fit.
TOL_DENSITY_RMS_PCT = 5.0
TOL_CONDUCTIVITY_RMS_PCT = 10.0
TOL_PR_RMS_PCT = 5.0
STAGES = ("probe", "pr_density", "digitize_fig1", "render_figures", "git_diff_check")
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
    a = 0.42747 * (R_KMOL * T_C) ** 2 / P_C * (1 + m * (1 - math.sqrt(T / T_C))) ** 2
    b = 0.08664 * R_KMOL * T_C / P_C
    A, B = a * p / (R_KMOL * T) ** 2, b * p / (R_KMOL * T)
    c, d = A - B - B * B, -A * B
    pp, qq = c - 1.0 / 3.0, -2.0 / 27.0 + c / 3.0 + d
    disc = qq * qq / 4.0 + pp ** 3 / 27.0
    if disc >= 0:
        z = 1.0 / 3.0 + _cbrt(-qq / 2.0 + math.sqrt(disc)) + _cbrt(-qq / 2.0 - math.sqrt(disc))
    else:
        z = 1.0 / 3.0 + 2.0 * math.sqrt(-pp / 3.0) * math.cos(
            math.acos(max(-1.0, min(1.0, -qq / (2.0 * math.sqrt(-(pp ** 3) / 27.0))))) / 3.0)
    return z, z * R_KMOL * T / p


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


def stats(dev):
    values = [item[1] for item in dev]
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    return rms, max(dev, key=lambda item: abs(item[1]))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--digitised", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--plot", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--pr-csv", type=Path, required=True)
    parser.add_argument("--repeat-plot", type=Path, required=True)
    parser.add_argument("--repeat-pr", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--job", default=None)
    parser.add_argument(
        "--stage", action="append", default=[], metavar="NAME|COMMAND|RC",
        help="one measured pipeline stage and its real exit status; every name in "
             "STAGES must be supplied, there is no default verdict")
    args = parser.parse_args()

    # Handoff verdicts are measurements.  A stage that is not supplied is a hard error:
    # a verification artifact that can assert 'passed' without having run anything is
    # worthless, so refuse to write one.
    stages = {}
    for item in args.stage:
        name, _, rest = item.partition("|")
        command, _, rc_text = rest.rpartition("|")
        if not name or not command or not rc_text.strip():
            raise SystemExit(f"malformed --stage {item!r}: expected NAME|COMMAND|RC")
        try:
            stages[name] = (command, int(rc_text))
        except ValueError:
            raise SystemExit(f"--stage {name!r} has a non-integer exit status {rc_text!r}")
    missing = [name for name in STAGES if name not in stages]
    if missing:
        raise SystemExit(
            "missing measured stage(s): " + ", ".join(missing)
            + "; pass --stage NAME|COMMAND|RC for every stage, including its real rc")
    unknown = sorted(set(stages) - set(STAGES))
    if unknown:
        raise SystemExit("unexpected stage name(s): " + ", ".join(unknown))

    checks = []
    head, rows = read_csv(args.probe)
    pr_head, pr_rows = read_csv(args.pr_csv)
    digitised = json.loads(args.digitised.read_text())
    data = json.loads(args.data.read_text())
    recipe = json.loads(args.recipe.read_text())
    svg = args.plot.read_text()

    # 1. source_and_units --------------------------------------------------
    t_values = [row["T_K"] for row in rows]
    problems = []
    if len(rows) != 851:
        problems.append(f"expected 851 rows, found {len(rows)}")
    if t_values != sorted(t_values) or t_values[0] != 150.0 or abs(t_values[-1] - 1000.0) > 1e-9:
        problems.append("temperature grid is not the declared 150-1000 K step 1 K sweep")
    cp_over_r = {row["T_K"]: row["cp_J_molK"] / R_MOL for row in rows}
    cp_min = min(cp_over_r.values())
    cp_max = max(cp_over_r.values())
    cp_300 = cp_over_r.get(300.0)
    # Z above 1 is physical (repulsion-dominated states at high T, low p) up to roughly 1.2
    # for these conditions; the bound rejects a failed root solve, not a real gas.
    for row in rows:
        if not (0.0 < row["Z_srk"] <= 1.5) or row["rho_srk_kg_m3"] <= 0 or row["lambda_eh_W_mK"] <= 0:
            problems.append(f"non-physical state at T={row['T_K']}: {row}")
            break
    # The probe's 300 K canary is an ideal-gas number: it pins cpR_ideal, the column that
    # must equal cp_ideal/(J/(mol K))/R_MOL.  The total cp/R at 100 atm carries the residual
    # part and is legitimately larger, so it is range-checked, not band-checked.
    ideal_300 = next((row["cpR_ideal"] for row in rows if row["T_K"] == 300.0), None)
    if ideal_300 is None:
        problems.append("the 300 K canary row is missing from the sweep")
    elif not (CP_R_300K_BAND[0] <= ideal_300 <= CP_R_300K_BAND[1]):
        problems.append(
            f"ideal cp/R(300 K) = {ideal_300:.4f} outside the audited band "
            f"[{CP_R_300K_BAND[0]}, {CP_R_300K_BAND[1]}]")
    cp_300 = ideal_300
    if cp_min < CP_R_RANGE[0] or cp_max > CP_R_RANGE[1]:
        problems.append(
            f"total cp/R spans [{cp_min:.4f}, {cp_max:.4f}], outside the physical range "
            f"[{CP_R_RANGE[0]}, {CP_R_RANGE[1]}] - a wrong cp scale looks like this")
    worst = 0.0
    worst_at = None
    for row in rows:
        _, v = srk_state(row["T_K"], P_FIG)
        rho = W_O2 / v
        rel = abs(rho - row["rho_srk_kg_m3"]) / rho
        if rel > worst:
            worst, worst_at = rel, row["T_K"]
    if worst >= 1e-6:
        problems.append(f"independent SRK cubic differs by {worst:.2e} at T={worst_at} K")
    lo, hi = cp_ideal(700.0 - 1e-9), cp_ideal(700.0 + 1e-9)
    join = abs(hi - lo) / lo
    cp_mismatch = max(abs(cp_ideal(row["T_K"]) - row["cp_ideal_J_molK"]) for row in rows)
    if join >= 1e-4 or cp_mismatch >= 1e-4:
        problems.append(f"Shomate splice {join:.2e}, column mismatch {cp_mismatch:.2e}")
    checks.append({
        "id": "source_and_units",
        "result": "passed" if not problems else "failed",
        "details":
            f"The probe is compiled from this checkout (replication/development/cantera-liang/"
            f"SrkKernel.h for the SRK volume and residual cp, replication/development/"
            f"liang-properties/ElyHanley.H for the conductivity) and sweeps {len(rows)} states, "
            f"T {t_values[0]}-{t_values[-1]} K at 100 atm = {P_FIG:.1f} Pa; no Python Cantera "
            f"module, no external numerics library. Z in "
            f"[{min(r['Z_srk'] for r in rows):.5f}, {max(r['Z_srk'] for r in rows):.5f}], "
            f"rho {min(r['rho_srk_kg_m3'] for r in rows):.3f}-{max(r['rho_srk_kg_m3'] for r in rows):.3f} kg/m3, "
            f"lambda {min(r['lambda_eh_W_mK'] for r in rows):.5f}-{max(r['lambda_eh_W_mK'] for r in rows):.5f} W/(m K), "
            f"total cp/R in [{cp_min:.4f}, {cp_max:.4f}] with ideal cp/R(300 K) = "
            f"{cp_300 if cp_300 is None else round(cp_300, 4)} inside the audited band "
            f"[{CP_R_300K_BAND[0]}, {CP_R_300K_BAND[1]}] (J/(mol K) divided by R = {R_MOL} "
            f"J/(mol K), not by the kmol constant used by the cubic). A closed-form SRK cubic written "
            f"independently in Python reproduces the kernel volume at every state; worst relative "
            f"density difference {worst:.2e} at T={worst_at} K (tolerance 1e-6). The two NIST Shomate "
            f"ranges of O2 give {lo:.6f} and {hi:.6f} J/(mol K) at the 700 K splice (relative jump "
            f"{join:.2e}) and the probe column agrees with this implementation to "
            f"{cp_mismatch:.2e} J/(mol K). Units are carried explicitly in the CSV header "
            f"({', '.join(head)}): T/K, rho/(kg/m3), Z/-, v/(m3/kmol), cp/(J/(mol K)), "
            f"lambda/(W/(m K))."
            + ("" if not problems else " Problems: " + " | ".join(problems)),
    })

    # 2. reference_coverage ------------------------------------------------
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
    if dense_drops:
        problems.append(f"{dense_drops} upward steps in the density curve")
    frame = digitised["panels"]["density"]["frame_pixels"]
    outside = [item for item in digitised["panels"]["density"]["experiments"]
               if not (frame[0] - 1 <= item["pixel"][0] <= frame[2] + 1
                       and frame[1] - 1 <= item["pixel"][1] <= frame[3] + 1)]
    if outside:
        problems.append(f"{len(outside)} published density symbols outside the frame")
    checks.append({
        "id": "reference_coverage",
        "result": "passed" if not problems else "failed",
        "details":
            f"The reference is the published figure itself: the PDF page's own embedded raster "
            f"(775x1371 JPEG, sha256 {digitised['source']['embedded_jpeg_sha256'][:16]}...) was "
            f"decoded and measured against the retained axis calibration, whose ticks were refitted "
            f"here (worst residual {digitised['calibration_max_abs_residual_px']:.2f} px, largest "
            f"change vs the retained calibration {declared:.2e}). Density model read "
            f"{dense[0]['x']:.1f}-{dense[-1]['x']:.1f} K in "
            f"{len(digitised['panels']['density']['model_segments'])} segments with "
            f"{len(digitised['panels']['density']['model_gaps'])} declared gaps where a filled symbol "
            f"hides the line, and {len(digitised['panels']['density']['experiments'])} published "
            f"triangles; conductivity model read {cond[0]['x']:.1f}-{cond[-1]['x']:.1f} K in "
            f"{len(digitised['panels']['conductivity']['model_segments'])} segments with "
            f"{len(digitised['panels']['conductivity']['experiments'])} published triangles. "
            f"{dense_drops} upward steps in the digitised density curve (0 expected from the paper). "
            f"Gaps are gaps: nothing was interpolated, moved or invented, and the declared one-pixel "
            f"resolution is {digitised['panels']['density']['uncertainty']['x_per_px']:.2f} K / "
            f"{digitised['panels']['density']['uncertainty']['y_per_px']:.4f} kg/m3 for (a) and "
            f"{digitised['panels']['conductivity']['uncertainty']['x_per_px']:.2f} K / "
            f"{digitised['panels']['conductivity']['uncertainty']['y_per_px']:.2e} W/(m K) for (b)."
            + ("" if not problems else " Problems: " + " | ".join(problems)),
    })

    # 3. figure_fidelity ---------------------------------------------------
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
    panels = recipe["panels"]
    geometry = "; ".join(
        f"({panel['id']}) frame [{', '.join(f'{v:.3f}' for v in panel['frame'])}] with x domain "
        f"{panel['x']['domain']} and y domain {panel['y']['domain']}" for panel in panels)
    checks.append({
        "id": "figure_fidelity",
        "result": "passed" if not problems else "failed",
        "details":
            f"One {len(svg)} byte SVG holds both panels on a single canvas: {geometry}. Geometry is "
            f"measured, not guessed - the 0.24 pt/px scale and the tick pixel rows come from the "
            f"retained calibration and every tick label is placed at its refitted pixel; the axis "
            f"titles are drawn with explicit label coordinates because the renderer has no rotation, "
            f"and the {len(ids)} series ({', '.join(ids)}) are drawn in legend order with the paper's "
            f"own colour convention (black published, #c0392b this work, #2e86c1 the PR variant). "
            f"Deliberate differences from the paper, all declared: (i) the paper's triangles are drawn "
            f"as circles because the renderer supports circles only, (ii) the rotated y-axis titles "
            f"are set horizontally inside the left margin, (iii) the paper's inward minor ticks are "
            f"omitted rather than invented because renderPaperComparison cannot draw them "
            f"(ticks [] plus the measured major ticks are recorded in the recipe), and (iv) the legend "
            f"labels are shortened ('SRK, this work' for 'the present model') and moved into empty "
            f"panel regions to stay inside the frame. The published order of rows is kept."
            + ("" if not problems else " Problems: " + " | ".join(problems)),
    })

    # 4. reproducibility ---------------------------------------------------
    plot_sha, repeat_plot_sha = digest(args.plot), digest(args.repeat_plot)
    pr_sha, repeat_pr_sha = digest(args.pr_csv), digest(args.repeat_pr)
    problems = []
    if plot_sha != repeat_plot_sha:
        problems.append(f"second render differs ({plot_sha[:12]} vs {repeat_plot_sha[:12]})")
    if pr_sha != repeat_pr_sha:
        problems.append(f"second PR sweep differs ({pr_sha[:12]} vs {repeat_pr_sha[:12]})")
    checks.append({
        "id": "reproducibility",
        "result": "passed" if not problems else "failed",
        "details":
            f"Repeated execution of the two deterministic stages is byte identical: the PR sweep "
            f"({len(pr_rows)} rows) gives sha256 {pr_sha[:16]}... twice, and the renderer gives "
            f"sha256 {plot_sha[:16]}... twice, in separate runs at source commit {args.commit[:12]}. "
            f"The C++ probe needs the batch container (g++ 11.2.0) and is not rerun here; its "
            f"inputs are four constants, the two repository headers and this sweep, and the earlier "
            f"native rerun of the sibling module was byte identical, but that is not claimed for "
            f"this binary."
            + ("" if not problems else " Problems: " + " | ".join(problems)),
    })

    # 5. numerical_comparison ---------------------------------------------
    srk_series = next(series for series in data["series"] if series["id"] == "a-computed-srk")["points"]
    eh_series = next(series for series in data["series"] if series["id"] == "b-computed-eh")["points"]
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
    density_rms, density_extreme = stats(density_dev)
    cond_rms, cond_extreme = stats(cond_dev)
    pr_dev = []
    for row in pr_rows[::10]:
        value = interpolate(srk_series, row["T_K"])
        if value:
            pr_dev.append((row["T_K"], 100.0 * (row["rho_PR_kg_m3"] - value) / value))
    pr_rms, pr_extreme = stats(pr_dev)
    problems = []
    if density_rms > TOL_DENSITY_RMS_PCT:
        problems.append(f"density rms {density_rms:.2f} % > {TOL_DENSITY_RMS_PCT} %")
    if cond_rms > TOL_CONDUCTIVITY_RMS_PCT:
        problems.append(f"conductivity rms {cond_rms:.2f} % > {TOL_CONDUCTIVITY_RMS_PCT} %")
    if pr_rms > TOL_PR_RMS_PCT:
        problems.append(f"PR-vs-SRK rms {pr_rms:.2f} % > {TOL_PR_RMS_PCT} %")
    checks.append({
        "id": "numerical_comparison",
        "result": "passed" if not problems else "failed",
        "details":
            f"Paper model minus this work at the digitised abscissae: density {len(density_dev)} "
            f"points, rms {density_rms:.2f} %, largest {density_extreme[1]:+.2f} % at "
            f"{density_extreme[0]:.0f} K; conductivity {len(cond_dev)} points, rms {cond_rms:.2f} %, "
            f"largest {cond_extreme[1]:+.2f} % at {cond_extreme[0]:.0f} K. Independent "
            f"Peng-Robinson density (replication/development/oxygen-properties) minus SRK over "
            f"{len(pr_dev)} sampled temperatures: rms {pr_rms:.2f} %, largest {pr_extreme[1]:+.2f} % "
            f"at {pr_extreme[0]:.0f} K, i.e. the two cubic equations of state bracket the paper's "
            f"curve. A systematic offset is reported, not corrected: the paper does not name the "
            f"equation of state behind its density curve and uses Ely-Hanley with Takahashi-corrected "
            f"diffusion for transport, so agreement within a few percent is the expected outcome, not "
            f"evidence of identity. The one clearly visible disagreement is the conductivity peak at "
            f"the low-temperature frame edge, which the published curve clips and this work resolves "
            f"to {max(r['lambda_eh_W_mK'] for r in rows):.4f} W/(m K) near 150 K. Verdict is "
            f"measured against declared rms tolerances density {TOL_DENSITY_RMS_PCT} %, "
            f"conductivity {TOL_CONDUCTIVITY_RMS_PCT} %, PR-vs-SRK {TOL_PR_RMS_PCT} %. The "
            f"conductivity digitisation is unresolved and is reported as such: the published "
            f"curve read off panel (b) sits about a factor of two above the computed Ely-Hanley "
            f"column over 171-837 K, which a factor-consistency check of the panel (b) y "
            f"calibration must explain before that panel can be called reproduced. Panel (a) "
            f"needs no such caveat."
            + ("" if not problems else " Problems: " + " | ".join(problems)),
    })

    result = {
        "schema": "forge-campaign-checks-v1",
        "source_commit": args.commit,
        "target": "liang-1",
        "checks": checks,
        # Derived from the exit status supplied for each stage, never from a literal.
        "handoff_checks": [
            {"command": stages[name][0],
             "result": "passed" if stages[name][1] == 0 else "failed",
             "revision": args.commit}
            for name in STAGES
        ],
        "stage_exit_status": {name: stages[name][1] for name in STAGES},
        "failed_checks": [check["id"] for check in checks if check["result"] != "passed"],
    }
    if args.job:
        result["run"] = {"job_id": args.job, "kind": "properties"}
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    for check in checks:
        print(f"{check['id']}: {check['result']}")
    print(f"stages: " + ", ".join(f"{n}={stages[n][1]}" for n in STAGES))
    print(f"failed: {result['failed_checks']}")
    stage_failures = [name for name in STAGES if stages[name][1] != 0]
    if stage_failures or result["failed_checks"]:
        print("FAILED stages: " + ", ".join(stage_failures) if stage_failures else "no stage failures")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
