"""Verify the audit detects corrupted native fluxes in explicit local fixtures."""
import argparse
import csv
import json
from pathlib import Path
import shutil

from conservation import digest, evaluate, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("observation", "balances", "mechanism", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "Choose a new fixture directory")
    observation = json.loads(args.observation.read_text())
    row = observation["jobs"][0]
    baseline = evaluate(row, Path(observation["snapshot"]), args.balances, args.mechanism)
    require(all(value < 1e-10 for value in baseline["identity_errors"].values()),
            "Source fixture does not pass native identities")
    args.output.mkdir(parents=True)
    results = {}
    for label, field, failed in (
        ("species", "J_H2", "species_flux_definition"),
        ("energy", "H_total_W_m2", "energy_decomposition")):
        root = args.output/label
        destination = root/"jobs"/str(row["job"])/"result"
        destination.mkdir(parents=True)
        original = args.balances/"jobs"/str(row["job"])/"result"
        for name in ("profile.csv", "balance-nodes.csv", "balance-faces.csv"):
            shutil.copyfile(original/name, destination/name)
        path = destination/"balance-faces.csv"
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        middle = len(rows)//2
        scale = max(abs(float(r[field])) for r in rows)
        require(scale > 0, "Perturbation has no scale")
        rows[middle][field] = str(float(rows[middle][field])+1e-4*scale)
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        result = evaluate(row, Path(observation["snapshot"]), root, args.mechanism)
        require(failed in result["failed_checks"], "Corrupted flux was not detected")
        results[label] = dict(
            field=field, perturbation=1e-4*scale,
            failed_checks=result["failed_checks"], identity_errors=result["identity_errors"])
    report = dict(
        result="PASS", job=row["job"], source_identity_errors=baseline["identity_errors"],
        original_failed_checks=baseline["failed_checks"], controls=results,
        script_sha256=digest(Path(__file__)), audit_sha256=digest(Path(__file__).with_name("conservation.py")),
        scientific_acceptance=False)
    (args.output/"test.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
