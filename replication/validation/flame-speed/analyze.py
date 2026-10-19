"""Evaluate paper Eq.40 on a fixed fresh-side OH crossing in each CSV."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics
import sys


def measure(rows, level, cold_cells=100, report_density_mismatch=False):
    if not rows or any(not math.isfinite(v) for row in rows for v in row.values()):
        raise ValueError("Empty or nonfinite diagnostic fields")
    rows = sorted(rows, key=lambda row: row["x"])
    if len(rows) < max(3, cold_cells):
        raise ValueError("Too few cells")
    spacing = rows[1]["x"] - rows[0]["x"]
    if spacing <= 0 or any(abs((b["x"] - a["x"]) / spacing - 1) > 1e-6
                          for a, b in zip(rows, rows[1:])):
        raise ValueError("Expected a uniform single x-row")
    for key in ("y", "z"):
        if max(row[key] for row in rows) - min(row[key] for row in rows) > spacing * 1e-6:
            raise ValueError("Expected one-dimensional mesh")
    peak = max(range(len(rows)), key=lambda i: rows[i]["YOH"])
    crossings = [i for i in range(peak)
                 if rows[i]["YOH"] <= level < rows[i + 1]["YOH"]]
    if len(crossings) != 1:
        raise ValueError("Expected one rising OH crossing before the peak")
    a, b = rows[crossings[0]], rows[crossings[0] + 1]
    fraction = (level - a["YOH"]) / (b["YOH"] - a["YOH"])
    terms = {key: a[key] + fraction * (b[key] - a[key]) for key in a}
    rho_u = statistics.mean(row["rho"] for row in rows[:cold_cells])
    gradient = terms["magGradOH"]
    if rho_u <= 0 or gradient <= 1e-12 or terms["gradOHx"] <= 0:
        raise ValueError("Invalid density/gradient or wrong flame flank")
    relative_rho_error = max(abs(row["rho"] / row["rhoSaved"] - 1) for row in rows
                             if row["rhoSaved"] > 0)
    if any(row["rhoSaved"] <= 0 for row in rows):
        raise ValueError("Nonpositive saved density")
    density_passed = relative_rho_error <= 1e-7
    if not density_passed and not report_density_mismatch:
        raise ValueError("Saved and reconstructed density disagree")
    chemistry_speed = terms["omegaOH"] / (rho_u * gradient)
    diffusion_speed = terms["minusDivJOH"] / (rho_u * gradient)
    return {"OH_level": level, "rho_unburned_kg_m3": rho_u, "crossing": terms,
            "chemistry_contribution_m_s": chemistry_speed,
            "diffusion_contribution_m_s": diffusion_speed,
            "direct_eq40_m_s": chemistry_speed + diffusion_speed,
            "density_check_passed": density_passed,
            "density_relative_tolerance": 1e-7,
            "max_relative_density_reconstruction_error": relative_rho_error}


def analyze(case, report_density_mismatch=False):
    output = {"method": "instantaneous chemistry plus corrected diffusion, Eq40",
              "primary_OH_level": 2e-5, "times": []}
    for path in sorted(case.glob("eq40-*.csv")):
        with path.open(newline="") as stream:
            rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
        item = {"time_s": float(path.stem[5:]), "source": path.name, "levels": []}
        for level in (1e-5, 2e-5, 3e-5):
            item["levels"].append(measure(rows, level,
                report_density_mismatch=report_density_mismatch))
        output["times"].append(item)
    if not output["times"]:
        raise ValueError("No diagnostic CSV files")
    output["times"].sort(key=lambda item: item["time_s"])
    output["qualified"] = all(level["density_check_passed"]
        for item in output["times"] for level in item["levels"])
    output["status"] = "checks_passed" if output["qualified"] else "density_check_failed"
    print(json.dumps(output, indent=2, allow_nan=False))
    return 0 if output["qualified"] else 3


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--report-density-mismatch", action="store_true",
        help="Emit provisional numbers with failure flags; still exit 3 on density failure")
    args = parser.parse_args()
    sys.exit(analyze(args.case, args.report_density_mismatch))
