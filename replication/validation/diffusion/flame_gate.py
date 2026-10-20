"""Replay the existing declared Case 5 paper screen; exit 1 if mismatch remains."""
import importlib.util
import json
from pathlib import Path


def main():
    replication = Path(__file__).resolve().parents[2]
    path = replication / "development/cantera-liang/compare_reference.py"
    spec = importlib.util.spec_from_file_location("paper_comparison", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    baseline = json.loads((replication / "docs/liang-figure8a-current-20261020.json")
                          .read_text(encoding="utf-8-sig"))
    reference = json.loads((replication / "docs/liang-figure8a-digitized-v2.json")
                           .read_text(encoding="utf-8-sig"))
    report = module.compare(baseline["results"], reference["rows"])
    rows = [r for r in report["rows"] if r["stage"] == 5]
    failed = [r for r in rows if not r["within_screen"]]
    if len(rows) < 3:
        raise ValueError("Insufficient Case 5 coverage")
    print(json.dumps(dict(criteria=report["criteria"], points=len(rows),
                          failures=failed, scientific_acceptance=False), indent=2))
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
