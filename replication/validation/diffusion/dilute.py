"""Compare the pinned mechanism's dilute transport with NIST measurements."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mechanism", type=Path)
    parser.add_argument("--output", type=Path, help="New report; omit for read-only plan")
    args = parser.parse_args()
    fixture = Path(__file__).with_name("references.json")
    refs = json.loads(fixture.read_text())["nist"]
    if not args.mechanism.is_file():
        parser.error("Mechanism does not exist")
    if args.output is None:
        print(json.dumps(dict(mechanism=str(args.mechanism.resolve()),
                              reference=refs, calculation="not run"), indent=2))
        return 0
    if args.output.exists():
        parser.error("Output exists; select a new report path")
    import cantera as ct
    if ct.__version__ != "3.2.0":
        raise ValueError("Expected pinned Cantera 3.2.0")
    gas = ct.Solution(str(args.mechanism), transport_model="mixture-averaged")
    stock = ct.Solution("gri30.yaml", transport_model="mixture-averaged")
    methane = gas.species_index("CH4")
    nitrogen = gas.species_index("N2")
    rows = []
    for bath, key, composition in [
        ("N2", "nitrogen_table2", {"CH4": 1e-10, "N2": 1.0}),
        ("air_21_79_assumption", "air_table4",
         {"CH4": 1e-10, "O2": .21, "N2": .79}),
    ]:
        for temperature, reference, uncertainty in refs[key]:
            gas.TPX = temperature, refs["pressure_pa"], composition
            stock.TPX = temperature, refs["pressure_pa"], composition
            value = (gas.binary_diff_coeffs[methane, nitrogen] if bath == "N2"
                     else gas.mix_diff_coeffs[methane]) * 1e4
            stock_value = (stock.binary_diff_coeffs[stock.species_index("CH4"), stock.species_index("N2")]
                           if bath == "N2" else stock.mix_diff_coeffs[stock.species_index("CH4")]) * 1e4
            residual = value - reference
            rows.append(dict(bath=bath, temperature_K=temperature,
                             calculated_cm2_s=float(value), reference_cm2_s=reference,
                             stock_gri30_cm2_s=float(stock_value),
                             uncertainty_cm2_s=uncertainty, residual_percent=100*residual/reference,
                             residual_over_U=float(residual/uncertainty),
                             within_U=bool(abs(residual) <= uncertainty),
                             validation_eligible=bath == "N2"))
    eligible = [r for r in rows if r["validation_eligible"]]
    report = dict(cantera_version=ct.__version__, mechanism=str(args.mechanism.resolve()),
                  input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (args.mechanism, fixture)},
                  reference=refs, rows=rows, nitrogen_within_U=sum(r["within_U"] for r in eligible),
                  nitrogen_total=len(eligible), scientific_acceptance=False)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(nitrogen_within_U=report["nitrogen_within_U"],
                          nitrogen_total=len(eligible), report=str(args.output))))
    return int(not all(r["within_U"] for r in eligible))


if __name__ == "__main__":
    raise SystemExit(main())
