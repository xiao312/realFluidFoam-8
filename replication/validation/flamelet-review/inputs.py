"""Read immutable producer artifacts and keep scientific coordinates explicit."""
from pathlib import Path
import hashlib
import json
import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def checked_files(directory, filenames):
    receipt = read_json(directory / "receipt.json")
    hashes = {"receipt.json": digest(directory / "receipt.json")}
    for name in filenames:
        actual = digest(directory / name)
        expected = receipt["artifacts"][name]
        if actual != expected:
            raise ValueError(f"Producer hash mismatch: {directory / name}")
        hashes[name] = actual
    return receipt, hashes


def load_inputs(run, table):
    receipt, run_hashes = checked_files(run, ["trajectory.npz", "diagnostics.json", "phase-metadata.json"])
    if not receipt.get("fresh_start") or receipt.get("status") != "transient_exported_not_accepted":
        raise ValueError("This review requires a fresh exported transient with its original producer receipt")
    for name, expected in [("fuel", {"CH4": 1.0}), ("oxidizer", {"O2": 1.0})]:
        if receipt["case"][name]["mole_fractions"] != expected:
            raise ValueError("This progress-normalization review currently supports pure CH4/O2 streams only")
    table_receipt, table_hashes = checked_files(table, ["table.json", "coverage.json", "heldout.json"])
    if table_receipt["metadata_sha256"] != run_hashes["phase-metadata.json"]:
        raise ValueError("Table phase metadata differs from trajectory phase metadata")
    with np.load(run / "trajectory.npz", allow_pickle=False) as archive:
        trajectory = {name: archive[name].copy() for name in archive.files}
    time, z, temperature, species = [trajectory[k] for k in ["time_s", "Z", "T_K", "species"]]
    y = trajectory["Y"]
    if temperature.shape != (len(time), len(z)) or y.shape != (len(time), len(z), len(species)):
        raise ValueError("Trajectory axes and field shapes disagree")
    if np.any(np.diff(time) <= 0) or np.any(np.diff(z) <= 0) or time[0] != 0:
        raise ValueError("Expected fresh t=0 trajectory and strictly increasing time/Z axes")
    if not all(np.isfinite(v).all() for v in [time, z, temperature, y]):
        raise ValueError("Non-finite trajectory data")
    if not np.isclose(time[-1], receipt["actual_final_time_s"], rtol=1e-12, atol=1e-15):
        raise ValueError("Trajectory final physical time disagrees with receipt")
    table_data = read_json(table / "table.json")
    values = np.asarray(table_data["values"])
    expected_shape = (len(table_data["z"]), len(table_data["eta"]), len(table_data["columns"]))
    if values.shape != expected_shape or not np.isfinite(values).all():
        raise ValueError("Malformed or non-finite table")
    return {"trajectory": trajectory, "receipt": receipt,
            "diagnostics": read_json(run / "diagnostics.json"),
            "table": table_data, "coverage": read_json(table / "coverage.json"),
            "heldout": read_json(table / "heldout.json"), "table_receipt": table_receipt,
            "input_hashes": {"run": run_hashes, "table": table_hashes}}


def sample_z(z, values, point):
    """Interpolate only along the sampled Z axis, preserving all other ordering."""
    if not z[0] <= point <= z[-1]:
        raise ValueError("Requested mixture fraction is outside sampled coverage")
    i = min(np.searchsorted(z, point, side="right") - 1, len(z) - 2)
    weight = (point - z[i]) / (z[i + 1] - z[i])
    return values[..., i] * (1 - weight) + values[..., i + 1] * weight


def whole_profile_summary(heldout):
    profiles = heldout["whole_profile"]
    fields = ["T_K", "omega_CO2_plus_CO_kg_m3_s", "Qdot_formation_298K_W_m3"]
    summary = {"profiles": len(profiles), "evaluated": sum(p["evaluated"] for p in profiles.values()),
               "out_of_coverage": sum(p["out_of_coverage"] for p in profiles.values()), "fields": {}}
    for field in fields:
        rows = [(p["evaluated"], p["fields"][field]) for p in profiles.values() if field in p["fields"]]
        count = sum(n for n, _ in rows)
        summary["fields"][field] = {
            "pooled_rms_absolute": float(np.sqrt(sum(n * row["rms_absolute_error"] ** 2 for n, row in rows) / count)),
            "max_absolute": max(row["max_absolute_error"] for _, row in rows),
            "sign_disagreements_above_profile_floor": sum(row["sign_disagreements_above_floor"] for _, row in rows),
            "resolved_points": sum(row["resolved_points"] for _, row in rows),
            "relative_error_note": "Per-profile denominator floors differ; no pooled relative metric reported"}
    return summary
