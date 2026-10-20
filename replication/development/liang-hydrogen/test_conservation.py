"""Check captured native balances and detect corrupted face fluxes."""
import argparse
import csv
import json
import shutil
from pathlib import Path

from conservation import evaluate


def perturb(path, column, change):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    index = len(rows) // 2
    rows[index][column] = format(float(rows[index][column]) + change, ".17g")
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "mechanism", "fixtures"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    if args.fixtures.exists():
        raise ValueError("Choose a new fixture directory; captured runs remain untouched")
    row = json.loads(args.manifest.read_text(encoding="utf-8-sig"))[0]
    original = evaluate(row, args.mechanism)
    if max(original["identity_errors"].values()) >= 1e-10:
        raise ValueError("Captured residual identities must pass before perturbation")
    source = Path(row["result"]).parent
    reports = []
    controls = (
        ("species", "G_H2", .0001,
         ("species_flux_definition", "species_residual_identity")),
        ("energy", "H_total_W_m2", 100.,
         ("energy_decomposition", "energy_residual_identity")),
    )
    for label, column, change, expected in controls:
        target = args.fixtures / label
        shutil.copytree(source, target)
        altered = dict(row, result=str(target / "result"))
        perturb(target / "result/balance-faces.csv", column, change)
        report = evaluate(altered, args.mechanism)
        if not all(name in report["failed_checks"] for name in expected):
            raise AssertionError(f"{label} corruption was not detected")
        reports.append(dict(control=label, injected_change=change,
                            detected=list(expected)))
    # Re-evaluate the original to prove fixtures did not alter captured evidence.
    assert original == evaluate(row, args.mechanism)
    print(json.dumps(dict(result="PASS", original_job=row["job"],
                          original_failed_screens=original["failed_checks"],
                          corruption_controls=reports), indent=2))


if __name__ == "__main__":
    main()
