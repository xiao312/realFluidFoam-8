"""Compare explicit stoichiometric profiles with Figure 7; never select a model."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from profile_diagnostics import profile_diagnostics
from structure_reference import CALIBRATION, crossing, extract, metrics


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_run(row, weights, window):
    result = Path(row["result"])
    if row["phi"] != 1 or not (result/"completed.txt").is_file():
        raise ValueError("Require explicitly selected completed stoichiometric runs")
    diagnostic = profile_diagnostics(result)
    if (diagnostic["max_species_sum_error"] >= 1e-7 or
            diagnostic["minimum_mass_fraction"] < -1e-9 or
            diagnostic["max_relative_massflux_change"] >= .001):
        raise ValueError(f"Numerical profile screen failed: {row['job']}")
    config = dict(line.split(maxsplit=1) for line in
                  (result/"configuration.txt").read_text().splitlines() if line.strip())
    if (abs(float(config["pressure_Pa"])-10132500) > 1e-6 or
            float(config["Tu_K"]) != 298 or float(config["phi"]) != 1 or
            config["case"] != str(row["case"])):
        raise ValueError("Profile operating conditions differ from Figure 7 comparison")
    with (result/"refinement.csv").open() as stream:
        levels = list(csv.DictReader(stream))
    if len(levels) < 2 or abs(float(levels[-1]["speed_cm_s"]) /
                             float(levels[-2]["speed_cm_s"])-1) >= .005:
        raise ValueError("Missing or inadequate refinement screen")
    profile = np.genfromtxt(result/"profile.csv", delimiter=",", names=True)
    expected = ["Y_"+name for name in weights]
    if [name for name in profile.dtype.names if name.startswith("Y_")] != expected:
        raise ValueError("Profile/species-table order differs")
    x, temperature = profile["x_m"]*1e6, profile["T_K"]
    denominator = sum(profile["Y_"+name]/weight for name, weight in weights.items())
    if not np.all(denominator > 0):
        raise ValueError("Nonpositive molar composition sum")
    data = dict(x_T_um=x, T=temperature)
    for name in ("H2", "O2", "HO2", "H2O2"):
        data[name] = profile["Y_"+name]/weights[name]/denominator
        data[f"x_{name}_um"] = x
    measured = metrics(data)
    point = measured["x1500_absolute_um"]+window
    if not x[0] <= point <= x[-1]:
        raise ValueError("Profile does not cover the finite paper window")
    measured["T_at_paper_right_K"] = float(np.interp(point, x, temperature))
    source = (result.parent/"source-revision.txt").read_text().strip()
    if row.get("source", source) != source:
        raise ValueError("Source revision differs from manifest")
    label = (f"Case {row['case']}; {config.get('model_variant', 'baseline')}; "
             f"grid {config.get('grid_factor', '1')}; job {row['job']}")
    record = dict(job=row["job"], case=row["case"], label=label,
                  variant=config.get("model_variant", "baseline"), source=source,
                  configuration=config, speed_cm_s=float(levels[-1]["speed_cm_s"]),
                  diagnostics=diagnostic, metrics=measured,
                  sha256={name: digest(result/name) for name in
                          ("profile.csv", "refinement.csv", "configuration.txt")})
    return record, data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("paper", "manifest", "species", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    rows = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    if not rows or len({r["job"] for r in rows}) != len(rows) or args.output.exists():
        parser.error("Require unique selected jobs and a new output directory")
    paper, paper_metrics, bounds, raw, calibration = extract(args.paper)
    window = float(paper["x_T_um"][-1]-paper_metrics["x1500_absolute_um"])
    weights = {}
    for line in args.species.read_text().splitlines():
        fields = line.split()
        if fields:
            weights[fields[0]] = float(fields[4])
    evaluations = [load_run(row, weights, window) for row in rows]
    for record, _ in evaluations:
        record["inside_graphical_metric_bounds"] = {
            name: lower <= record["metrics"][name] <= upper
            for name, (lower, upper) in bounds.items()}
        record["finite_window_temperature_difference_K"] = (
            record["metrics"]["T_at_paper_right_K"]-paper_metrics["T_at_paper_right_K"])
    print(json.dumps(dict(output=str(args.output.resolve()), jobs=len(rows),
                          scientific_acceptance=False, remote_writes=False)))
    if args.action == "plan":
        return
    aligned, fixed_temperature = [], []
    for label, data in [("Paper; case unspecified", paper)] + [
            (record["label"], profile) for record, profile in evaluations]:
        anchor = crossing(data["x_T_um"], data["T"], 1500)
        for species in ("T", "H2", "O2", "HO2", "H2O2"):
            for x, value in zip(data[f"x_{species}_um"], data[species]):
                aligned.append(dict(profile=label, series=species,
                                    x_relative_um=float(x-anchor), value=float(value)))
        for temperature in (500, 1000, 1250, 1500, 1750, 2000, 2300):
            location = crossing(data["x_T_um"], data["T"], temperature)
            for species in ("H2", "O2", "HO2", "H2O2"):
                x = data[f"x_{species}_um"]
                if x[0] <= location <= x[-1]:
                    fixed_temperature.append(dict(
                        profile=label, T_K=temperature, species=species,
                        X=float(np.interp(location, x, data[species]))))
    files = [args.paper, args.manifest, args.species, CALIBRATION, Path(__file__),
             Path(__file__).with_name("structure_reference.py")]
    report = dict(
        inputs_sha256={path.name: digest(path) for path in files},
        paper_metrics=paper_metrics, graphical_bounds=bounds,
        paper_right_relative_um=window, calibration=calibration,
        runs=[record for record, _ in evaluations], scientific_acceptance=False,
        limits=["Original paper does not identify the plotted case or Soret setting",
                "Translation at 1500 K only; no spatial or species rescaling",
                "Graphical bounds are not experimental confidence intervals",
                "Native mass/element/energy and Soret audits remain separate requirements",
                "Fixed-temperature sampling omits unobserved tails; no extrapolation"])
    args.output.mkdir(parents=True)
    write_csv(args.output/"raw-vector-points.csv", raw)
    write_csv(args.output/"aligned-profiles.csv", aligned)
    write_csv(args.output/"species-at-temperature.csv", fixed_temperature)
    write_csv(args.output/"metrics.csv", [
        dict(label="Paper; case unspecified", **paper_metrics)] + [
        dict(label=record["label"], job=record["job"], **record["metrics"])
        for record, _ in evaluations])
    report["outputs_sha256"] = {name: digest(args.output/name) for name in (
        "raw-vector-points.csv", "aligned-profiles.csv", "species-at-temperature.csv", "metrics.csv")}
    (args.output/"summary.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
