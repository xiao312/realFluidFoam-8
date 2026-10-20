"""Record completed H2 snapshot identities without copying raw simulation data."""
import argparse
import csv
import hashlib
import json
import re
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


def identity(directory, row, revision):
    """Prefer observed immutable job records; allow only named historical pins."""
    if row.get("source", revision) != revision:
        raise ValueError(f"Source declaration differs from observed job {row['job']}")
    parent = directory.parent
    build_path, binary_path = parent/"build-path.txt", parent/"executable.sha256"
    if build_path.exists() or binary_path.exists():
        if not (build_path.is_file() and binary_path.is_file()):
            raise ValueError(f"Incomplete observed build identity for job {row['job']}")
        build = build_path.read_text().strip().rsplit("/", 1)[-1]
        fields = binary_path.read_text().split()
        if len(fields) != 2:
            raise ValueError(f"Malformed executable hash record for job {row['job']}")
        binary = fields[0]
        if not build.isdigit() or not re.fullmatch(r"[0-9a-f]{64}", binary):
            raise ValueError(f"Malformed build identity for job {row['job']}")
        if int(row.get("build", build)) != int(build):
            raise ValueError(f"Build declaration differs from observed job {row['job']}")
        return {"basis": "observed-job-records", "job": int(build),
                "binary_sha256": binary,
                "record_sha256": {name: digest(parent/name) for name in (
                    "build-path.txt", "executable.sha256", "source-revision.txt",
                    "input-sha256.txt", "guess-sha256.txt", "command.txt")
                    if (parent/name).is_file()}}
    if revision not in BUILDS:
        raise ValueError(f"No observed identity or registered historical source: {revision}")
    if int(row.get("build", BUILDS[revision]["job"])) != BUILDS[revision]["job"]:
        raise ValueError(f"Build declaration differs from historical registry for job {row['job']}")
    return {"basis": "historical-source-registry", **BUILDS[revision]}


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
        record = {k: row[k] for k in ("job", "case", "phi", "transport")}
        configuration = (directory/"configuration.txt").read_text()
        config = {}
        for line in configuration.splitlines():
            if not line.strip():
                continue
            key, value = line.split(maxsplit=1)
            if key in config:
                raise ValueError(f"Duplicate configuration field in job {row['job']}: {key}")
            config[key] = value
        for key in ("width_m", "Tu_K", "grid_factor"):
            if key in row and abs(float(config[key])-float(row[key])) > 1e-12:
                raise ValueError(f"Declared {key} differs from job {row['job']}")
        observed_variant = next((line.split(maxsplit=1)[1] for line in
                                 configuration.splitlines() if line.startswith("model_variant ")),
                                "baseline")
        if row.get("variant", observed_variant) != observed_variant:
            raise ValueError(f"Variant declaration differs from job {row['job']}")
        record.update(
            variant=observed_variant,
            configuration=config,
            source_revision=revision,
            build_identity=identity(directory, row, revision),
            snapshot_result=relative,
            final={k: float(v) for k, v in levels[-1].items() if k != "case"},
            last_speed_relative_change=abs(
                float(levels[-1]["speed_cm_s"])/float(levels[-2]["speed_cm_s"])-1),
            sha256={name: digest(directory/name) for name in (
                "configuration.txt", "refinement.csv", "profile.csv",
                "property-checks.csv", "transport.csv", "callbacks.txt")},
        )
        if (directory/"soret-flux.csv").is_file():
            if config.get("Soret", "off") == "off":
                raise ValueError(f"Unexpected Soret flux output in disabled job {row['job']}")
            record["sha256"]["soret-flux.csv"] = digest(directory/"soret-flux.csv")
        elif config.get("Soret", "off") != "off":
            raise ValueError(f"Missing native Soret flux output for job {row['job']}")
        if str(levels[-1]["case"]) != str(row["case"]):
            raise ValueError(f"Case mismatch in job {row['job']}.")
        if abs(record["final"]["phi"]-float(row["phi"])) > 1e-10:
            raise ValueError(f"Equivalence-ratio mismatch in job {row['job']}.")
        result.append(record)
    document = {
        "schema": "liang-hydrogen-completed-ledger-v3",
        "manifest_sha256": digest(args.manifest),
        "script_sha256": digest(Path(__file__)),
        "build_identity_basis": (
            "Each run declares observed job records or a named historical "
            "source-to-build registry association. No identity is inferred from current HEAD."
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
