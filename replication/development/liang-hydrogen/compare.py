"""Compare completed H2 baselines to independent vector references; never fit data."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from digitize import PAPER_SHA, sample
from plot import load_runs


def profile_diagnostics(result):
    data = np.genfromtxt(result/"profile.csv", delimiter=",", names=True)
    species = [name for name in data.dtype.names if name.startswith("Y_")]
    if not species or len(data) < 3:
        raise ValueError(f"Incomplete profile: {result}")
    if not all(np.isfinite(data[name]).all() for name in data.dtype.names):
        raise ValueError(f"Nonfinite profile: {result}")
    mass_flux = data["rho_kg_m3"]*data["U_m_s"]
    return {
        "points": len(data),
        "min_temperature_K": float(min(data["T_K"])),
        "max_temperature_K": float(max(data["T_K"])),
        "max_species_sum_error": float(max(abs(sum(data[s] for s in species)-1))),
        "minimum_mass_fraction": float(min(min(data[s]) for s in species)),
        "max_relative_massflux_change": float(max(abs(mass_flux/mass_flux[0]-1))),
        "inlet_outlet_enthalpy_difference_J_kg": float(data["h_J_kg"][-1]-data["h_J_kg"][0]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("manifest", "reference", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text(encoding="utf-8-sig"))
    inputs = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    if reference["paper_sha256"] != PAPER_SHA or args.output.exists():
        parser.error("Expected calibrated paper reference and new output directory")
    runs = load_runs(args.manifest)
    seen = set()
    for run in runs:
        if run.get("variant", "baseline") != "baseline" or run.get("grid_factor", 1) != 1:
            raise ValueError("Use a separate manifest for nonbaseline controls")
        key = (run["transport"], run["case"], run["phi"])
        if key in seen:
            raise ValueError(f"Duplicate baseline point: {key}")
        seen.add(key)
    print(json.dumps(dict(input_jobs=len(inputs), completed=len(runs),
                          output=str(args.output.resolve()), remote_writes=False)))
    if args.action == "plan":
        return
    records, diagnostics, missing = [], [], []
    completed_ids = {r["job"] for r in runs}
    for row in inputs:
        if row["job"] not in completed_ids:
            missing.append({k: row[k] for k in ("job", "case", "phi", "transport")})
    columns = {"speed_cm_s": ("speed_cm_s", 1.),
               "density_g_cm3": ("rhou_kg_m3", .001),
               "massflux_g_cm2_s": ("massflux_kg_m2s", .1),
               "temperature_K": ("Tb_K", 1.), "Tb_K": ("Tb_K", 1.)}
    for run in runs:
        result = Path(run["result"])
        diag = profile_diagnostics(result)
        diagnostics.append({k: run[k] for k in ("job", "case", "phi", "transport")} |
                           {"grid_change": run["grid_change"],
                            "last_grid_screen": run["grid_change"] < .005, **diag})
        for number, figure in reference["figures"].items():
            for series in figure["series"]:
                if series["case"] != run["case"]:
                    continue
                point = sample(series, run["phi"])
                if point is None:
                    continue
                quantity = series["quantity"]
                if quantity not in columns:
                    raise ValueError(f"Unrecognized reference quantity: {quantity}")
                key, scale = columns[quantity]
                value = run[key]*scale
                error = value-point["value"]
                allowance = (max(.05, .01*abs(point["value"])) + point["uncertainty"]
                             if quantity == "speed_cm_s" else None)
                identity = run["case"] != "3star"
                records.append(dict(
                    figure=int(number), case=run["case"], phi=run["phi"],
                    transport=run["transport"], job=run["job"], quantity=quantity,
                    calculated=value, reference=point["value"],
                    reading_allowance=point["uncertainty"], reading_method=point["method"],
                    error=error, relative_error=error/point["value"],
                    screening_allowance=allowance,
                    numeric_speed_screen=None if allowance is None else abs(error) <= allowance,
                    paper_case_identity_eligible=identity,
                    grid_change=run["grid_change"]))
    args.output.mkdir(parents=True)
    with (args.output/"comparison.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    report = dict(
        inputs={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (args.manifest, args.reference, Path(__file__))},
        paper_sha256=PAPER_SHA, completed=len(runs), missing=missing,
        numerical_diagnostics=diagnostics,
        failed_speed_points=[r for r in records if r["numeric_speed_screen"] is False],
        comparisons=records, scientific_acceptance=False,
        limits=[
            "Figure geometry is not author tabular data; reading uncertainty is not a confidence interval.",
            "The speed rule is a screening tolerance, not validation of missing model definitions.",
            "Partial-T is not established as paper Case 3*; Case 4/5 conductivity remains provisional.",
            "No acceptance threshold is introduced here for density, burning flux or temperature.",
            "No extrapolation, marker interpolation, coefficient fit or selection of a preferred transport variant."])
    (args.output/"summary.json").write_text(json.dumps(report, indent=2)+"\n",
                                          encoding="utf-8", newline="\n")
    print(json.dumps(dict(comparisons=len(records), missing=len(missing),
                          failed_speed_points=len(report["failed_speed_points"]))))


if __name__ == "__main__":
    main()
