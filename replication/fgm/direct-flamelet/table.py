"""Build a bounded finite-rate flamelet table and measure physical held-out errors."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from common import sha256, write_json
from table_io import heldout_report, interpolate_profile, load_member


def build(members, z_axis, eta_axis):
    profiles = np.array([interpolate_profile(member, z_axis) for member in members])
    output = np.empty((len(z_axis), len(eta_axis), profiles.shape[2]))
    lower, upper, degeneracies, reversals = [], [], [], []
    for j, mixture in enumerate(z_axis):
        states = profiles[:, j, :]
        progress = states[:, 2]
        low, high = float(np.min(progress)), float(np.max(progress))
        lower.append(low)
        upper.append(high)
        differences = np.diff(progress)
        if np.any(differences > 1e-10) and np.any(differences < -1e-10):
            reversals.append(float(mixture))
        order = np.argsort(progress)
        progress, states = progress[order], states[order]
        unique, first, counts = np.unique(progress, return_index=True, return_counts=True)
        for start, count in zip(first, counts):
            if count > 1 and np.max(np.ptp(states[start:start + count], axis=0) /
                                    np.maximum(np.max(np.abs(states), axis=0), 1e-8)) > 1e-7:
                raise ValueError(f"Ambiguous physical states at Z={mixture} and C={progress[start]}")
        if high - low <= 1e-12:
            scale = np.maximum(np.max(np.abs(states), axis=0), 1e-8)
            if np.max(np.ptp(states, axis=0) / scale) > 1e-7:
                raise ValueError(f"Degenerate progress coordinate has different physical states at Z={mixture}")
            output[j] = states[0]
            degeneracies.append(float(mixture))
        else:
            queries = low + eta_axis * (high - low)
            output[j] = np.column_stack([np.interp(queries, unique, states[first, k])
                                          for k in range(states.shape[1])])
    return {"z": z_axis, "eta": eta_axis, "c_min": np.array(lower), "c_max": np.array(upper),
            "values": output, "columns": members[0]["columns"],
            "degenerate_rows": degeneracies, "family_order_reversal_Z": reversals}


def write_of8(path, model, species, source_commit, combined_hash):
    number = lambda values: " ".join(format(float(value), ".17g") for value in values)
    lines = ["schema forge-fgm-table-v2", "source " + source_commit,
             "profile-sha256 " + combined_hash, "units-progress-source kg/m3/s", "units-heat-release W/m3",
             "density-owner thermophysicalModel", "temperature-owner thermophysicalModel",
             "enthalpy-owner thermophysicalModel", "progress-coordinate mass-fraction-mapped",
             "progress-species CO2 CO", "species " + " ".join(species),
             "nZ " + str(len(model["z"])), "nC " + str(len(model["eta"])),
             "z " + number(model["z"]), "c " + number(model["eta"]),
             "c-min " + number(model["c_min"]), "c-max " + number(model["c_max"])]
    blocks = [("Y " + name, "Y_" + name) for name in species]
    blocks += [("Sc", "omega_CO2_plus_CO_kg_m3_s"), ("Q", "Qdot_formation_298K_W_m3"), ("Tdiag", "T_K")]
    for block, column in blocks:
        lines.append("block " + block)
        index = model["columns"].index(column)
        lines.extend(number(row) for row in model["values"][:, :, index])
        lines.append("end")
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    metadata = json.loads(args.metadata.read_text())
    if manifest["schema"] != "direct-flamelet-family/v1" or not re.fullmatch("[0-9a-f]{40}", args.source_commit):
        parser.error("unsupported manifest or source commit")
    if sha256(args.metadata) != manifest["metadata_sha256"]:
        parser.error("metadata hash mismatch")
    specification = manifest["members"]
    if len({item["id"] for item in specification}) != len(specification):
        parser.error("duplicate member id")
    if any(item["role"] not in ("training", "held-out") for item in specification):
        parser.error("member roles must be training or held-out")
    species = metadata["speciesOrder"]
    members = [load_member(item, args.manifest.parent, species) for item in specification]
    training = [item for item in members if item["role"] == "training"]
    if len(training) < 2 or len({item["profile_sha256"] for item in members}) != len(members):
        parser.error("at least two distinct training profiles required; duplicated physical files refused")
    first = training[0]["receipt"]
    for member in members:
        receipt = member["receipt"]
        if receipt["mechanism_sha256"] != metadata["mechanismSha256"]:
            parser.error(f"{member['id']}: mechanism mismatch")
        if any(receipt["case"][key] != first["case"][key] for key in ("pressure_pa", "fuel", "oxidizer", "width_m")):
            parser.error(f"{member['id']}: pressure, inlets or width differ; not a matched strain family")
        if receipt["models"]["thermo"] != first["models"]["thermo"] or receipt["models"]["transport"] != first["models"]["transport"]:
            parser.error(f"{member['id']}: physical models differ")
    z_count, eta_count = manifest["z_points"], manifest["eta_points"]
    if type(z_count) is not int or z_count < 3 or type(eta_count) is not int or eta_count < 2:
        parser.error("grid point counts invalid")
    kinds = sorted({item["receipt"]["status"] for item in members})
    plan = {"training": [item["id"] for item in training], "held_out": [item["id"] for item in members if item["role"] == "held-out"],
            "grid": [z_count, eta_count], "species": len(species), "physical_profile_kinds": kinds,
            "scope": "finite-rate data on measured C coverage; no claim of a complete manifold"}
    if args.plan:
        print(json.dumps(plan, indent=2))
        return 0
    if args.out is None or args.out.exists():
        parser.error("--out must be a new directory")
    model = build(training, np.linspace(0, 1, z_count), np.linspace(0, 1, eta_count))
    reports = {item["id"]: heldout_report(model, item["z"], item["values"]) for item in members if item["role"] == "held-out"}
    spatial = {item["id"]: heldout_report(model, item["spatial_holdout_z"], item["spatial_holdout_values"]) for item in training}
    source_hashes = {item["id"]: item["profile_sha256"] for item in training}
    combined = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    coverage = {"Z": model["z"].tolist(), "C_min": model["c_min"].tolist(), "C_max": model["c_max"].tolist(),
                "degenerate_Z": model["degenerate_rows"], "family_order_reversal_Z": model["family_order_reversal_Z"],
                "cold_unreacted_interior_covered": bool(np.all(model["c_min"][1:-1] <= 1e-12)),
                "full_unsteady_manifold": False, "presumed_PDF": False, "out_of_range": "refuse",
                "python_holdout_progress_endpoint_tolerance": 1e-12,
                "python_holdout_degenerate_span_threshold": 1e-12,
                "OF8_admissibility": "C++ strict default has no endpoint tolerance and only exactly zero span is degenerate; diagnostic clamp is separate",
                "progress": "transport raw Y_CO2+Y_CO; eta is only a local lookup coordinate, not Sharma normalized progress"}
    args.out.mkdir(parents=True)
    write_of8(args.out / "physical.tbl", model, species, args.source_commit, combined)
    write_json(args.out / "coverage.json", coverage)
    write_json(args.out / "heldout.json", {"whole_profile": reports, "within_profile_every_fifth": spatial, "scientific_acceptance": False})
    write_json(args.out / "table.json", {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in model.items()})
    write_json(args.out / "receipt.json", {"schema": "physical-family-table/v1", "status": "table_built_not_accepted", **plan,
        "source_commit": args.source_commit, "manifest_sha256": sha256(args.manifest), "metadata_sha256": sha256(args.metadata),
        "training_profiles": source_hashes, "combined_training_hash": combined,
        "heldout_profiles": {item["id"]: item["profile_sha256"] for item in members if item["role"] == "held-out"},
        "case": first["case"], "mechanism_sha256": first["mechanism_sha256"], "scientific_acceptance": False,
        "artifacts": {name: sha256(args.out / name) for name in ("physical.tbl", "coverage.json", "heldout.json", "table.json")}})
    print(json.dumps({"status": "table_built_not_accepted", **plan}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
