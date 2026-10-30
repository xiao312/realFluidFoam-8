"""Derive lookup-grid sensitivity from the same immutable physical family and holdouts."""
import argparse
import copy
import json
import re
from pathlib import Path
import subprocess
import sys
import time
from common import sha256, write_json

GRIDS = [(201, 41), (201, 161), (401, 161), (401, 401)]


def summarize(path):
    raw = json.loads(path.read_text())
    result = {}
    for scope in ("whole_profile", "within_profile_every_fifth"):
        frames = list(raw[scope].values())
        fields = {}
        for name in ("T_K", "omega_CO2_plus_CO_kg_m3_s", "Qdot_formation_298K_W_m3", "Y_CO2", "Y_CO"):
            rows = [frame["fields"][name] for frame in frames if name in frame["fields"]]
            fields[name] = {key: max(row[key] for row in rows) if rows else None for key in
                ("max_absolute_error", "rms_absolute_error", "max_global_peak_relative_error", "rms_global_peak_relative_error")}
            fields[name]["sign_disagreements_above_floor"] = sum(row["sign_disagreements_above_floor"] for row in rows)
        result[scope] = {"attempted": sum(frame["attempted"] for frame in frames),
                         "evaluated": sum(frame["evaluated"] for frame in frames),
                         "out_of_coverage": sum(frame["out_of_coverage"] for frame in frames),
                         "fields": fields, "RMS_summary": "maximum per-frame RMS, not pooled RMS"}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--branch-policy", choices=["post-peak-extinction/v1"])
    parser.add_argument("--zero-endpoint-policy", choices=["zero-progress-numerical-tail/v1"])
    parser.add_argument("--mechanism", type=Path)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.source_commit):
        parser.error("--source-commit requires the full source commit")
    original = json.loads(args.manifest.read_text())
    if original.get("schema") != "direct-flamelet-family/v1" or sha256(args.metadata) != original["metadata_sha256"]:
        raise ValueError("Manifest or metadata identity mismatch")
    receipt = {"schema": "physical-table-sensitivity/v1", "source_commit": args.source_commit,
               "input_manifest_sha256": sha256(args.manifest), "metadata_sha256": sha256(args.metadata),
               "holdout_ids": [row["id"] for row in original["members"] if row["role"] == "held-out"],
               "grids": GRIDS, "raw_physics_modified": False, "scientific_acceptance": False,
               "branch_policy": args.branch_policy,
               "zeroEndpointPolicy": args.zero_endpoint_policy,
               "limitation": "Lookup density cannot resolve missing physical sampling or multi-valued states", "results": []}
    if args.plan:
        print(json.dumps(receipt, indent=2))
        return 0
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new directory")
    args.out.mkdir(parents=True)
    write_json(args.out / "receipt.json", receipt)
    for nz, nc in GRIDS:
        manifest = copy.deepcopy(original)
        manifest.update(z_points=nz, eta_points=nc)
        if args.branch_policy is not None:
            manifest["branch_policy"] = args.branch_policy
        if args.zero_endpoint_policy is not None:
            manifest["zeroEndpointPolicy"] = args.zero_endpoint_policy
        for member in manifest["members"]:
            path = Path(member["directory"])
            member["directory"] = str((path if path.is_absolute() else args.manifest.parent / path).resolve())
        name = f"z{nz}-eta{nc}"
        manifest_path = args.out / (name + "-manifest.json")
        write_json(manifest_path, manifest)
        started = time.monotonic()
        command = [sys.executable, str(Path(__file__).with_name("table.py")),
                "--manifest", str(manifest_path), "--metadata", str(args.metadata.resolve()),
                "--source-commit", args.source_commit, "--out", str(args.out / name)]
        if args.mechanism is not None:
            command += ["--mechanism", str(args.mechanism.resolve())]
        with (args.out / (name + ".log")).open("w") as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        result = {"grid": [nz, nc], "exit": completed.returncode, "elapsed_s": time.monotonic() - started,
                  "manifest_sha256": sha256(manifest_path), "log_sha256": sha256(args.out / (name + ".log"))}
        if completed.returncode == 0:
            result.update(table_receipt_sha256=sha256(args.out / name / "receipt.json"),
                          heldout=summarize(args.out / name / "heldout.json"))
        receipt["results"].append(result)
        write_json(args.out / "receipt.json", receipt)
        print(json.dumps(result), flush=True)
    return 0 if all(row["exit"] == 0 for row in receipt["results"]) else 5


if __name__ == "__main__":
    raise SystemExit(main())
