"""Replay the existing declared Case 5 paper screen; exit 1 if mismatch remains."""
import importlib.util
import argparse
import hashlib
import json
from pathlib import Path


def main():
    replication = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path,
                        default=replication / "docs/liang-figure8a-current-20261020.json")
    parser.add_argument("--reference", type=Path,
                        default=replication / "docs/liang-figure8a-digitized-v2.json")
    args = parser.parse_args()
    path = replication / "development/cantera-liang/compare_reference.py"
    spec = importlib.util.spec_from_file_location("paper_comparison", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    baseline = json.loads(args.results.read_text(encoding="utf-8-sig"))
    reference = json.loads(args.reference.read_text(encoding="utf-8-sig"))
    report = module.compare(baseline["results"], reference["rows"])
    rows = [r for r in report["rows"] if r["stage"] == 5]
    failed = [r for r in rows if not r["within_screen"]]
    if not {1.3, 1.35, 1.4}.issubset({round(r["phi"], 6) for r in rows}):
        raise ValueError("Case 5 must include the three previously failing conditions")
    print(json.dumps(dict(criteria=report["criteria"], points=len(rows),
                          failures=failed,
                          input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in (args.results, args.reference)},
                          scientific_acceptance=False), indent=2))
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
