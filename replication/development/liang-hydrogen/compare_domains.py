"""Screen completed domain controls and report sensitivity without fitting paper data."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from compare import profile_diagnostics
from ledger import identity


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(row):
    result = Path(row["result"])
    if not (result/"completed.txt").is_file():
        raise ValueError(f"Incomplete control: {row['job']}")
    config = dict(line.split(maxsplit=1) for line in
                  (result/"configuration.txt").read_text().splitlines() if line.strip())
    with (result/"refinement.csv").open() as stream:
        levels = list(csv.DictReader(stream))
    if len(levels)<2:
        raise ValueError("Need two converged grids")
    last = levels[-1]
    if not all(np.isfinite(float(value)) for level in levels
               for name, value in level.items() if name != "case"):
        raise ValueError("Nonfinite refinement record")
    if str(last["case"])!=str(row["case"]) or abs(float(last["phi"])-row["phi"])>1e-10:
        raise ValueError("Run identity differs from manifest")
    variant = config.get("model_variant", "baseline")
    if row.get("variant", variant)!=variant:
        raise ValueError("Run variant differs from manifest")
    profile = np.genfromtxt(result/"profile.csv", delimiter=",", names=True)
    width = float(profile["x_m"][-1]-profile["x_m"][0])
    if not np.all(np.diff(profile["x_m"])>0):
        raise ValueError("Nonmonotone profile")
    if abs(width-float(config["width_m"]))>1e-12 or abs(width-row["width_m"])>1e-12:
        raise ValueError("Actual domain differs from configured or requested width")
    if abs(profile["T_K"][0]-float(config["Tu_K"]))>1e-8:
        raise ValueError("Inlet temperature differs from configuration")
    diagnostics = profile_diagnostics(result)
    grid_change = abs(float(last["speed_cm_s"])/float(levels[-2]["speed_cm_s"])-1)
    if (grid_change>=.005 or diagnostics["max_relative_massflux_change"]>=.001
            or diagnostics["max_species_sum_error"]>=1e-7
            or diagnostics["minimum_mass_fraction"]<-1e-9):
        raise ValueError(f"Numerical screen failed for job {row['job']}")
    checks = np.genfromtxt(result/"property-checks.csv", delimiter=",", names=True)
    if not all(np.isfinite(checks[name]).all() for name in checks.dtype.names):
        raise ValueError("Nonfinite thermodynamic check")
    if (np.max(np.abs(checks["relative_cp_fd_error"]))>1e-5
            or np.max(np.abs(checks["relative_enthalpy_euler_error"]))>1e-9):
        raise ValueError(f"Thermodynamic identity failed for job {row['job']}")
    source = (result.parent/"source-revision.txt").read_text().strip()
    build = identity(result, row, source)
    return {
        "job": row["job"], "case": str(row["case"]), "phi": row["phi"],
        "transport": row["transport"], "variant": variant,
        "width_m": width, "Tu_K": float(config["Tu_K"]),
        "pressure_Pa": float(config["pressure_Pa"]), "source": source,
        "build_identity": build, "speed_cm_s": float(last["speed_cm_s"]),
        "Tb_K": float(last["Tb_K"]), "grid_change": grid_change,
        "first_interval_temperature_change_K": float(profile["T_K"][1]-profile["T_K"][0]),
        "last_interval_temperature_change_K": float(profile["T_K"][-1]-profile["T_K"][-2]),
        "diagnostics": diagnostics,
        "sha256": {name:digest(result/name) for name in
                   ("profile.csv", "refinement.csv", "configuration.txt", "property-checks.csv")},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output directory")
    rows = json.loads(args.manifest.read_text(encoding="utf-8"))
    if len({r["job"] for r in rows})!=len(rows):
        raise ValueError("Duplicate job identity")
    runs = [evaluate(row) for row in rows]
    grouped = {}
    for run in runs:
        key = (run["case"], run["phi"], run["transport"], run["variant"])
        grouped.setdefault(key, []).append(run)
    groups = []
    for key, group in sorted(grouped.items()):
        group.sort(key=lambda row:row["width_m"])
        if len(group)<3 or len({r["width_m"] for r in group})!=len(group):
            raise ValueError("Each group needs at least three distinct domain lengths")
        for field in ("source", "Tu_K", "pressure_Pa"):
            if len({r[field] for r in group})!=1:
                raise ValueError("Unmatched domain-control "+field)
        if len({r["build_identity"]["binary_sha256"] for r in group})!=1:
            raise ValueError("Unmatched executable")
        if len({r["build_identity"]["record_sha256"]["input-sha256.txt"] for r in group})!=1:
            raise ValueError("Unmatched physical inputs")
        speeds = [r["speed_cm_s"] for r in group]
        temperatures = [r["Tb_K"] for r in group]
        groups.append(dict(
            case=key[0], phi=key[1], transport=key[2], variant=key[3],
            jobs=[r["job"] for r in group], widths_m=[r["width_m"] for r in group],
            speed_span_cm_s=max(speeds)-min(speeds),
            speed_span_percent=100*(max(speeds)-min(speeds))/group[-1]["speed_cm_s"],
            endpoint_temperature_span_K=max(temperatures)-min(temperatures),
            maximum_grid_change=max(r["grid_change"] for r in group),
        ))
    report = dict(
        manifest_sha256=digest(args.manifest), script_sha256=digest(Path(__file__)),
        groups=groups, runs=runs, scientific_acceptance=False,
        limits=["Observed domain sensitivity, not an asymptotic error estimate",
                "Existing numerical screens do not establish paper agreement",
                "Failed startup attempts are retained in the separate campaign record"],
    )
    print(json.dumps({"runs":len(runs), "groups":groups, "remote_writes":False}, indent=2))
    if args.action=="apply":
        args.output.mkdir(parents=True)
        (args.output/"summary.json").write_text(json.dumps(report,indent=2)+"\n",
                                               encoding="utf-8",newline="\n")
        with (args.output/"groups.csv").open("w",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(groups[0]),lineterminator="\n")
            writer.writeheader();writer.writerows(groups)


if __name__=="__main__":
    main()
