"""Exercise saved-grid cancellation and detect a deliberately corrupted thermal flux."""
import argparse
import csv
import json
import shutil
from pathlib import Path

from soret_roundtrip import inspect, shared_audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new local fixture directory")
    rows = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    row = next(r for r in rows if r["case"] == "3" and r["phi"] == 1.4
               and r["variant"] == "manual-soret-baseline")
    native, _ = shared_audit()
    original = inspect(row, native)
    assert original["entries_outside_decimal_bound"] == 0
    error = original["strict_native_residuals"]["thermal_definition"]
    if original["decimal_significant_digits"] == 16:
        # The historical thin-grid fixture exceeds the strict relative limit.
        assert error > 1e-10
    else:
        assert error < 1e-10
    result = args.output/"corrupted"
    result.mkdir(parents=True)
    for name in ("profile.csv", "soret-flux.csv", "completed.txt"):
        shutil.copyfile(Path(row["result"])/name, result/name)
    config = Path(row["result"])/"configuration.txt"
    if config.exists():
        shutil.copyfile(config, result/config.name)
    path = result/"soret-flux.csv"
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        names, fluxes = reader.fieldnames, list(reader)
    index = max(range(len(fluxes)), key=lambda i: abs(float(fluxes[i]["soret_kg_m2_s"])))
    fluxes[index]["soret_kg_m2_s"] = str(float(fluxes[index]["soret_kg_m2_s"])*1.0001)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(fluxes)
    corrupted = inspect(dict(row, result=str(result)), native)
    assert corrupted["entries_outside_decimal_bound"] > 0
    report = dict(unmodified=original, corrupted=corrupted,
                  result="PASS: export rounding bounded; 100 ppm thermal-flux corruption detected")
    (args.output/"test.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(report["result"])


if __name__ == "__main__":
    main()
