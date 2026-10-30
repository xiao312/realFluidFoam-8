"""Load solved physical profiles and interpolate their explicitly covered domain."""
import csv
import json
from pathlib import Path
import numpy as np
from common import sha256


def load_member(member, manifest_dir, species):
    directory = Path(member["directory"])
    if not directory.is_absolute():
        directory = manifest_dir / directory
    receipt_path = directory / "receipt.json"
    if sha256(receipt_path) != member["receipt_sha256"]:
        raise ValueError(f"{member['id']}: receipt hash mismatch")
    receipt = json.loads(receipt_path.read_text())
    if receipt["status"] not in ("converged_flame", "transient_snapshot") or not receipt.get("physical_export_qualified"):
        raise ValueError(f"{member['id']}: not a physically exported finite-rate flame")
    profile = directory / "profile.csv"
    if sha256(profile) != receipt["artifacts"]["profile.csv"]:
        raise ValueError(f"{member['id']}: profile hash mismatch")
    with profile.open(newline="") as handle:
        raw = list(csv.DictReader(handle))
    columns = ["T_K", "rho_kg_m3", "Y_CO2_plus_CO", "omega_CO2_plus_CO_kg_m3_s",
               "Qdot_formation_298K_W_m3", *["Y_" + name for name in species]]
    coordinate = "Z_coordinate" if receipt.get("coordinate") == "mixture_fraction" else "Z_Bilger"
    z = np.array([float(row[coordinate]) for row in raw])
    values = np.array([[float(row[key]) for key in columns] for row in raw])
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(z)):
        raise ValueError(f"{member['id']}: nonfinite profile")
    if not (np.max(np.diff(z)) <= 1e-7 or np.min(np.diff(z)) >= -1e-7):
        raise ValueError(f"{member['id']}: mixture fraction is not monotone")
    order = np.argsort(z)
    z, values = z[order], values[order]
    if abs(z[0]) > 1e-8 or abs(z[-1] - 1) > 1e-8:
        raise ValueError(f"{member['id']}: profile does not reach both pure streams")
    z[0], z[-1] = 0.0, 1.0  # roundoff only, with the original values retained in CSV
    unique, first, counts = np.unique(z, return_index=True, return_counts=True)
    for start, count in zip(first, counts):
        if count > 1:
            group = values[start:start + count]
            scale = np.maximum(np.max(np.abs(values), axis=0), 1e-8)
            if np.max(np.ptp(group, axis=0) / scale) > 1e-7:
                raise ValueError(f"{member['id']}: different physical states share exactly equal Z")
    removed_duplicates = len(z) - len(unique)
    z, values = unique, values[first]
    held_indices = np.arange(5, len(z) - 1, 5) if member["role"] == "training" else np.array([], dtype=int)
    keep = np.ones(len(z), dtype=bool)
    keep[held_indices] = False
    return {"id": member["id"], "role": member["role"], "receipt": receipt, "columns": columns,
            "z": z, "values": values, "train_z": z[keep], "train_values": values[keep],
            "spatial_holdout_z": z[held_indices], "spatial_holdout_values": values[held_indices],
            "profile_sha256": sha256(profile), "roundoff_duplicate_coordinates_removed": removed_duplicates}


def interpolate_profile(member, z_axis):
    return np.column_stack([np.interp(z_axis, member["train_z"], member["train_values"][:, k])
                            for k in range(len(member["columns"]))])


def lookup(model, z, progress):
    axis = model["z"]
    if z < axis[0] or z > axis[-1]:
        raise ValueError("mixture_fraction_out_of_range")
    lower_c = float(np.interp(z, axis, model["c_min"]))
    upper_c = float(np.interp(z, axis, model["c_max"]))
    tolerance = 1e-12
    if progress < lower_c - tolerance or progress > upper_c + tolerance:
        raise ValueError("progress_out_of_covered_range")
    if upper_c - lower_c <= tolerance:
        if abs(progress - lower_c) > tolerance:
            raise ValueError("degenerate_stream_progress_mismatch")
        eta = 0.0
    else:
        eta = (progress - lower_c) / (upper_c - lower_c)
        eta = min(1.0, max(0.0, eta))  # tolerance-limited floating-point endpoint only
    hi = min(len(axis) - 1, max(1, int(np.searchsorted(axis, z))))
    lo = hi - 1
    weight = (z - axis[lo]) / (axis[hi] - axis[lo])
    left = np.array([np.interp(eta, model["eta"], model["values"][lo, :, k])
                     for k in range(len(model["columns"]))])
    right = np.array([np.interp(eta, model["eta"], model["values"][hi, :, k])
                      for k in range(len(model["columns"]))])
    return (1 - weight) * left + weight * right


def heldout_report(model, z, actual):
    expected, predicted, rejected = [], [], []
    for mixture, row in zip(z, actual):
        try:
            predicted.append(lookup(model, float(mixture), float(row[2])))
            expected.append(row)
        except ValueError as error:
            rejected.append({"Z": float(mixture), "C": float(row[2]), "reason": str(error)})
    report = {"attempted": len(z), "evaluated": len(expected), "out_of_coverage": len(rejected),
              "rejected_points": rejected, "fields": {}, "verdict": "measured, not accepted"}
    if not expected:
        return report
    expected, predicted = np.asarray(expected), np.asarray(predicted)
    for k, name in enumerate(model["columns"]):
        difference = predicted[:, k] - expected[:, k]
        floor = 1.0 if name == "T_K" else 1e-6
        if name in ("omega_CO2_plus_CO_kg_m3_s", "Qdot_formation_298K_W_m3"):
            floor = max(1e-8, float(np.max(np.abs(expected[:, k]))) * 1e-4)
        relative = np.abs(difference) / np.maximum(np.abs(expected[:, k]), floor)
        resolved = np.abs(expected[:, k]) >= floor
        report["fields"][name] = {"max_absolute_error": float(np.max(np.abs(difference))),
            "rms_absolute_error": float(np.sqrt(np.mean(difference ** 2))),
            "p95_absolute_error": float(np.quantile(np.abs(difference), .95)),
            "relative_error_floor": floor, "max_floor_relative_error": float(np.max(relative)),
            "rms_floor_relative_error": float(np.sqrt(np.mean(relative ** 2))),
            "resolved_points": int(np.sum(resolved)),
            "sign_disagreements_above_floor": int(np.sum(resolved & (predicted[:, k] * expected[:, k] < 0)))}
    return report
