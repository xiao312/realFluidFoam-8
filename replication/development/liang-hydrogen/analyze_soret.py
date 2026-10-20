"""Audit matched hydrogen thermal-diffusion controls without fitting paper data."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

from compare import profile_diagnostics
from digitize import PAPER_SHA, sample
from ledger import identity


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shared_audit():
    path = Path(__file__).parent.parent/"cantera-liang/analyze_soret.py"
    spec = importlib.util.spec_from_file_location("native_soret_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def evaluate(row, reference, native):
    result = Path(row["result"])
    require((result/"completed.txt").is_file(), f"Incomplete job {row['job']}")
    config = {}
    for line in (result/"configuration.txt").read_text().splitlines():
        if not line.strip():
            continue
        key, value = line.split(maxsplit=1)
        require(key not in config, "Duplicate configuration field")
        config[key] = value
    require(config["model_variant"] == row["variant"], "Variant mismatch")
    require(config["case"] == str(row["case"]), "Case mismatch")
    require(abs(float(config["phi"])-row["phi"]) < 1e-10, "Phi mismatch")
    with (result/"refinement.csv").open() as stream:
        levels = list(csv.DictReader(stream))
    require(len(levels) >= 2, "Two converged grids required")
    require(all(np.isfinite(float(value)) for level in levels
                for name, value in level.items() if name != "case"),
            "Nonfinite refinement value")
    final = levels[-1]
    speed = float(final["speed_cm_s"])
    grid_change = abs(speed/float(levels[-2]["speed_cm_s"])-1)
    require(grid_change < .005, "Final refinement change exceeds existing screen")
    diagnostics = profile_diagnostics(result)
    require(diagnostics["max_relative_massflux_change"] < .001, "Mass-flow screen failed")
    require(diagnostics["max_species_sum_error"] < 1e-7, "Species sum screen failed")
    require(diagnostics["minimum_mass_fraction"] >= -1e-9, "Negative species screen failed")
    checks = np.genfromtxt(result/"property-checks.csv", delimiter=",", names=True)
    require(all(np.isfinite(checks[name]).all() for name in checks.dtype.names),
            "Nonfinite thermodynamic identity")
    require(np.max(np.abs(checks["relative_cp_fd_error"])) < 1e-5, "Cp identity failed")
    require(np.max(np.abs(checks["relative_enthalpy_euler_error"])) < 1e-9,
            "Partial-enthalpy Euler identity failed")
    profile, species = native.read_profile(result/"profile.csv")
    require(abs(profile["T_K"][0]-float(config["Tu_K"])) < 1e-8, "Inlet mismatch")
    require(abs(100*profile["U_m_s"][0]-speed) < 1e-10, "Speed/profile mismatch")
    require(abs(profile["x_m"][-1]-profile["x_m"][0]-float(config["width_m"])) < 1e-12,
            "Domain/profile mismatch")
    source = (result.parent/"source-revision.txt").read_text().strip()
    build = identity(result, row, source)
    record = {key: row[key] for key in ("job", "case", "phi", "transport", "variant")}
    record.update(source=source, build_identity=build, configuration=config,
                  speed_cm_s=speed, Tb_K=float(final["Tb_K"]),
                  grid_change=grid_change, diagnostics=diagnostics,
                  sha256={name: digest(result/name) for name in (
                      "profile.csv", "refinement.csv", "property-checks.csv",
                      "configuration.txt", "callbacks.txt")})
    enabled = row["variant"] != "baseline"
    require((config["Soret"] != "off") == enabled, "Soret configuration mismatch")
    if enabled:
        path = result/"soret-flux.csv"
        errors, faces, species_rows = native.inspect_native_fluxes(path, profile, species)
        record["sha256"]["soret-flux.csv"] = digest(path)
        record["native_flux_checks"] = errors
        limits = dict(decomposition=1e-12, thermal_definition=1e-10,
                      total_mass_closure=1e-7, thermal_mass_closure=1e-10,
                      coefficient_projection=1e-10)
        record["strict_native_limits"] = limits
        record["strict_native_failures"] = [key for key, limit in limits.items()
                                            if errors[key] >= limit]
        record["maximum_absolute_thermal_enthalpy_flux_W_m2"] = max(
            abs(item["thermal_h_W_m2"]) for item in faces)
        record["species_thermal_flux"] = species_rows
    else:
        require(not (result/"soret-flux.csv").exists(), "Unexpected disabled thermal output")
    series = [s for s in reference["figures"]["3"]["series"] if s["case"] == row["case"]]
    require(len(series) == 1, "Unknown Figure 3 case")
    point = sample(series[0], row["phi"])
    record["paper_comparison"] = None
    if point is not None:
        limit = max(.05, .01*abs(point["value"]))+point["uncertainty"]
        record["paper_comparison"] = dict(
            **point, error_cm_s=speed-point["value"],
            relative_error_percent=100*(speed/point["value"]-1),
            screening_allowance_cm_s=limit,
            screen_passed=abs(speed-point["value"]) <= limit)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("manifest", "reference", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "Choose a new output directory")
    rows = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    reference = json.loads(args.reference.read_text(encoding="utf-8-sig"))
    require(reference["paper_sha256"] == PAPER_SHA, "Paper reference identity mismatch")
    require(len({r["job"] for r in rows}) == len(rows), "Duplicate job ID")
    native, native_path = shared_audit()
    runs = [evaluate(row, reference, native) for row in rows]
    groups = {}
    for run in runs:
        key = (run["case"], run["phi"], run["transport"])
        group = groups.setdefault(key, {})
        require(run["variant"] not in group, "Duplicate variant in matched group")
        group[run["variant"]] = run
    changes = []
    for key, group in sorted(groups.items()):
        require(set(group) == {"baseline", "soret-baseline", "manual-soret-baseline"},
                "Each case/phi needs off, native and manual controls")
        values = list(group.values())
        require(len({r["source"] for r in values}) == 1, "Unmatched source")
        require(len({r["build_identity"]["binary_sha256"] for r in values}) == 1,
                "Unmatched executable")
        require(len({r["build_identity"]["record_sha256"]["input-sha256.txt"]
                     for r in values}) == 1, "Unmatched physical inputs")
        for field in ("pressure_Pa", "Tu_K", "width_m", "grid_factor", "energy",
                      "alpha", "transport", "flux_correction", "collider_concentration"):
            require(len({r["configuration"][field] for r in values}) == 1,
                    "Unmatched configuration: "+field)
        off = group["baseline"]["speed_cm_s"]
        for variant, run in group.items():
            point = run["paper_comparison"]
            changes.append(dict(
                case=key[0], phi=key[1], transport=key[2], variant=variant,
                job=run["job"], speed_cm_s=run["speed_cm_s"],
                change_from_off_percent=100*(run["speed_cm_s"]/off-1),
                paper_cm_s=None if point is None else point["value"],
                paper_error_percent=None if point is None else point["relative_error_percent"],
                paper_speed_screen=None if point is None else point["screen_passed"]))
    report = dict(
        manifest_sha256=digest(args.manifest), reference_sha256=digest(args.reference),
        script_sha256=digest(Path(__file__)), native_audit_sha256=digest(native_path),
        runs=runs, comparisons=changes, numerical_checks_passed=True,
        strict_native_checks_passed=not any(r.get("strict_native_failures") for r in runs),
        scientific_acceptance=False,
        limits=["Neither Soret closure is identified as Liang's setting",
                "No paper extrapolation; phi=1 lies outside Figure 3's extracted interval",
                "Author collision-fit temperature bounds are unavailable",
                "Strict native-flux failures remain explicit and are not waived",
                "Case 4/5 conductivity remains a provisional dense-increment model"])
    print(json.dumps({"runs": len(runs), "comparisons": changes}, indent=2))
    if args.action == "apply":
        args.output.mkdir(parents=True)
        (args.output/"summary.json").write_text(json.dumps(report, indent=2)+"\n",
                                               encoding="utf-8", newline="\n")
        with (args.output/"comparisons.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(changes[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(changes)


if __name__ == "__main__":
    main()
