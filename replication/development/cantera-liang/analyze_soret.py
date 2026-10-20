"""Audit paired methane Soret controls using native face fluxes, without remote access."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_profile(path):
    values = np.genfromtxt(path, delimiter=",", names=True)
    require(len(values) > 10, "Incomplete profile")
    require(all(np.all(np.isfinite(values[name])) for name in values.dtype.names),
            "Nonfinite profile")
    # NumPy sanitizes parentheses in CH2(S); retain the original species names.
    with path.open(newline="", encoding="utf-8") as stream:
        header = next(csv.reader(stream))
    names = [name[2:] for name in header if name.startswith("Y_")]
    return values, names


def native_fluxes(path, profile, species):
    """Preserve the writer's face-major, species-minor ordering."""
    header = ["x_left_m", "x_right_m", "T_mid_K", "species", "DT_kg_m_s",
              "ordinary_kg_m2_s", "soret_kg_m2_s", "total_kg_m2_s", "partial_h_J_kg"]
    numeric = [name for name in header if name != "species"]
    array = np.empty((len(profile)-1, len(species), len(numeric)))
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == header, "Unexpected native Soret schema")
        count = 0
        for count, row in enumerate(reader, 1):
            face, k = divmod(count-1, len(species))
            require(face < len(profile)-1, "Excess flux rows")
            require(row["species"] == species[k], "Flux species order mismatch")
            array[face, k] = [float(row[name]) for name in numeric]
    require(count == (len(profile)-1)*len(species), "Incomplete flux rows")
    require(np.all(np.isfinite(array)), "Nonfinite native face flux")
    data = {name: array[:, :, n] for n, name in enumerate(numeric)}
    require(np.max(np.abs(data["x_left_m"]-profile["x_m"][:-1, None])) < 1e-13,
            "Left-face coordinates differ from profile")
    require(np.max(np.abs(data["x_right_m"]-profile["x_m"][1:, None])) < 1e-13,
            "Right-face coordinates differ from profile")
    expected_temperature = .5*(profile["T_K"][:-1]+profile["T_K"][1:])
    require(np.max(np.abs(data["T_mid_K"]-expected_temperature[:, None])) < 1e-9,
            "Face temperatures differ from profile")
    dx = np.diff(profile["x_m"])
    require(np.all(dx > 0), "Nonmonotone profile")
    gradient = np.diff(profile["T_K"])/dx/expected_temperature
    ordinary, thermal, total = [data[name] for name in
        ["ordinary_kg_m2_s", "soret_kg_m2_s", "total_kg_m2_s"]]
    flux_scale = max(1e-100, np.max(np.abs(total)), np.max(np.abs(thermal)))
    coefficient = data["DT_kg_m_s"]
    errors = {
        "decomposition": float(np.max(np.abs(ordinary+thermal-total))/flux_scale),
        "thermal_definition": float(np.max(np.abs(thermal+coefficient*gradient[:, None]))/flux_scale),
        "total_mass_closure": float(np.max(np.abs(total.sum(axis=1)))/flux_scale),
        "thermal_mass_closure": float(np.max(np.abs(thermal.sum(axis=1)))/flux_scale),
        "coefficient_projection": float(np.max(np.abs(coefficient.sum(axis=1))) /
                                        max(1e-100, np.max(np.abs(coefficient)))),
    }
    require(errors["decomposition"] < 1e-12, "Flux decomposition failed")
    require(errors["thermal_definition"] < 1e-10, "Thermal flux definition failed")
    require(errors["total_mass_closure"] < 1e-7, "Total mass-flux closure failed")
    require(errors["thermal_mass_closure"] < 1e-10, "Thermal mass-flux closure failed")
    require(errors["coefficient_projection"] < 1e-10, "Coefficient projection failed")
    faces = []
    ordinary_h = np.sum(ordinary*data["partial_h_J_kg"], axis=1)
    thermal_h = np.sum(thermal*data["partial_h_J_kg"], axis=1)
    for j in range(len(dx)):
        faces.append({
            "x_mid_m": float(.5*(profile["x_m"][j]+profile["x_m"][j+1])),
            "T_mid_K": float(expected_temperature[j]),
            "ordinary_h_W_m2": float(ordinary_h[j]),
            "thermal_h_W_m2": float(thermal_h[j]),
            "total_species_h_W_m2": float(ordinary_h[j]+thermal_h[j]),
            "mass_diffusion_sum_kg_m2s": float(total[j].sum()),
        })
    species_rows = []
    for k, name in enumerate(species):
        peak = int(np.argmax(np.abs(thermal[:, k])))
        species_rows.append({
            "species": name,
            "max_abs_ordinary_kg_m2s": float(np.max(np.abs(ordinary[:, k]))),
            "max_abs_thermal_kg_m2s": float(np.max(np.abs(thermal[:, k]))),
            "max_abs_total_kg_m2s": float(np.max(np.abs(total[:, k]))),
            "signed_peak_thermal_kg_m2s": float(thermal[peak, k]),
            "T_at_peak_thermal_K": float(expected_temperature[peak]),
        })
    return errors, faces, species_rows


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("observation", type=Path)
    parser.add_argument("flux_directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "Choose a new output directory")
    observation = json.loads(args.observation.read_text(encoding="utf-8"))
    runs = observation["jobs"]
    require(len(runs) == 6 and {(r["stage"], r["soret"]) for r in runs} ==
            {(s, v) for s in [1, 4, 5] for v in [False, True]},
            "Expected matched Cases 1/4/5, Soret off/on")
    snapshot = Path(observation["snapshot"])
    sources = {r["source"] for r in runs}
    binaries = {r["executable_sha256"] for r in runs}
    inputs = {r["record_sha256"]["input-sha256.txt"] for r in runs}
    require(len(sources) == len(binaries) == len(inputs) == 1, "Unmatched build or inputs")
    require(len({r["phi"] for r in runs}) == 1, "Unmatched equivalence ratio")
    require(all(r["pressure_atm"] == 100 for r in runs), "Expected 100 atm")
    diagnostics, tables, pairs = [], {}, []
    by_stage = {}
    for row in runs:
        require(row["scheduler"][0] == "COMPLETED" and row["screen_passed"],
                "Unscreened or unfinished solve")
        profile_path = snapshot/"jobs"/str(row["job"])/"result/profile.csv"
        require(digest(profile_path) == row["output_sha256"]["profile.csv"],
                "Profile hash mismatch")
        profile, species = read_profile(profile_path)
        require(abs(profile["T_K"][0]-298.) < 1e-8, "Unexpected inlet temperature")
        result = dict(stage=row["stage"], soret=row["soret"], job=row["job"],
                      speed_cm_s=row["screen"]["speed_cm_s"],
                      final_temperature_K=float(profile["T_K"][-1]))
        require(abs(result["speed_cm_s"]-100*profile["U_m_s"][0]) < 1e-10,
                "Profile and screened speed differ")
        if row["soret"]:
            require(row["saved_soret_enabled"], "Saved flow does not enable Soret")
            path = args.flux_directory/"jobs"/str(row["job"])/"result/soret-flux.csv"
            require(digest(path) == row["soret_flux_sha256"], "Native flux hash mismatch")
            errors, faces, species_rows = native_fluxes(path, profile, species)
            result["native_flux_sha256"] = digest(path)
            result["native_flux_checks"] = errors
            result["maximum_absolute_thermal_enthalpy_flux_W_m2"] = max(
                abs(r["thermal_h_W_m2"]) for r in faces)
            tables[f"case-{row['stage']}-faces.csv"] = faces
            tables[f"case-{row['stage']}-species.csv"] = species_rows
        diagnostics.append(result)
        by_stage.setdefault(row["stage"], {})[row["soret"]] = result
    for stage, pair in sorted(by_stage.items()):
        off, on = pair[False]["speed_cm_s"], pair[True]["speed_cm_s"]
        pairs.append(dict(stage=stage, off_cm_s=off, on_cm_s=on,
                          change_cm_s=on-off, change_pct=100*(on/off-1)))
    delta_off = by_stage[4][False]["speed_cm_s"]-by_stage[5][False]["speed_cm_s"]
    delta_on = by_stage[4][True]["speed_cm_s"]-by_stage[5][True]["speed_cm_s"]
    summary = {
        "observation_sha256": digest(args.observation), "script_sha256": digest(Path(__file__)),
        "source_revision": next(iter(sources)), "executable_sha256": next(iter(binaries)),
        "input_record_sha256": next(iter(inputs)), "phi": runs[0]["phi"],
        "pressure_atm": 100, "Tu_K": 298, "pairs": pairs, "runs": diagnostics,
        "case4_minus_case5_without_soret_cm_s": delta_off,
        "case4_minus_case5_with_soret_cm_s": delta_on,
        "change_in_case4_minus_case5_cm_s": delta_on-delta_off,
        "scientific_acceptance": False,
        "limits": ["Cantera 3.2 mixture Soret sensitivity, not recovered Liang settings",
                   "Case 5 uses corrected mixture diffusion with dilute binary collision terms",
                   "Native thermal enthalpy contribution is evaluated on each solved profile"],
    }
    print(json.dumps(summary, indent=2))
    if args.action == "apply":
        args.output.mkdir(parents=True)
        (args.output/"summary.json").write_text(json.dumps(summary, indent=2)+"\n",
                                               encoding="utf-8", newline="\n")
        write_csv(args.output/"paired-speeds.csv", pairs)
        for name, rows in tables.items():
            write_csv(args.output/name, rows)


if __name__ == "__main__":
    main()
