"""Record completed H2 snapshot identities without copying raw simulation data."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

BUILDS = {
    "ff39189850d8ec83277e3abe093cfc037f8da900": {
        "job": 125068607,
        "binary_sha256": "10390da5398f0ebd42b413da4a031e0e0d9bb38362ea5a2c9a4caa5be978ee91",
    },
    "cd62786661d050bcc9ea29023c8a1e3cd41ad41c": {
        "job": 125071462,
        "binary_sha256": "e80861cb22e62da7d1303bb96bce8dcb8230e349b5f8f962049fd60941301792",
    },
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("manifest", "project_root", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    rows = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    project = args.project_root.resolve()
    if args.output.exists():
        parser.error("Use a new ledger path.")
    if len({int(row["job"]) for row in rows}) != len(rows):
        parser.error("Duplicate job IDs in manifest.")
    result = []
    for row in rows:
        directory = Path(row["result"]).resolve()
        relative = directory.relative_to(project).as_posix()
        if not (directory/"completed.txt").is_file():
            raise ValueError(f"Job {row['job']} is incomplete; collect it separately.")
        with (directory/"refinement.csv").open() as stream:
            levels = list(csv.DictReader(stream))
        if len(levels) < 2:
            raise ValueError(f"Job {row['job']} lacks a refinement comparison.")
        source_path = directory.parent/"source-revision.txt"
        revision = source_path.read_text().strip()
        if revision not in BUILDS:
            raise ValueError(f"Unregistered historical build source: {revision}")
        record = {k: row[k] for k in ("job", "case", "phi", "transport")}
        record.update(
            source_revision=revision,
            build_registry_association=BUILDS[revision],
            snapshot_result=relative,
            final={k: float(v) for k, v in levels[-1].items() if k != "case"},
            last_speed_relative_change=abs(
                float(levels[-1]["speed_cm_s"])/float(levels[-2]["speed_cm_s"])-1),
            sha256={name: digest(directory/name) for name in (
                "configuration.txt", "refinement.csv", "profile.csv",
                "property-checks.csv", "transport.csv", "callbacks.txt")},
        )
        if str(levels[-1]["case"]) != str(row["case"]):
            raise ValueError(f"Case mismatch in job {row['job']}.")
        if abs(record["final"]["phi"]-float(row["phi"])) > 1e-10:
            raise ValueError(f"Equivalence-ratio mismatch in job {row['job']}.")
        result.append(record)
    document = {
        "schema": "liang-hydrogen-completed-ledger-v1",
        "manifest_sha256": digest(args.manifest),
        "build_identity_basis": (
            "Historical source-to-build registry association; original jobs lack "
            "direct build-path records. Result files and source-revision were observed."
        ),
        "scientific_acceptance": False,
        "completed": len(result),
        "runs": sorted(result, key=lambda r: int(r["job"])),
    }
    print(json.dumps({"jobs": len(result), "output": str(args.output),
                      "remote_writes": False, "scientific_acceptance": False}))
    if args.action == "apply":
        args.output.write_text(json.dumps(document, indent=2)+"\n",
                               encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
