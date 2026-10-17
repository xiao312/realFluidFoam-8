"""Compare runtime-library methane properties with pinned NIST tables."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

PROPERTIES = {
    "rho_kg_m3": ("Density (kg/m3)", 1),
    "Cp_J_kg_K": ("Cp (J/g*K)", 1000),
    "mu_Pa_s": ("Viscosity (Pa*s)", 1),
    "kappa_W_m_K": ("Therm. Cond. (W/m*K)", 1),
}
EXPECTED = {(p, t) for p in (1, 50, 100, 200, 300) for t in range(180, 621, 10)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srk", type=Path)
    parser.add_argument("pr", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name("nist-provenance.json").read_text())
    reference = {}
    for entry in manifest["files"]:
        path = args.reference / entry["file"]
        if digest(path) != entry["sha256"]:
            raise ValueError("Reference hash mismatch: " + str(path))
        with path.open(newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                key = (float(row["Pressure (atm)"]), float(row["Temperature (K)"]))
                if key in reference:
                    raise ValueError("Duplicate reference state: " + str(key))
                reference[key] = {name: float(row[column])*factor
                                  for name, (column, factor) in PROPERTIES.items()}
    if set(reference) != EXPECTED:
        raise ValueError("Reference coverage differs from the declared sweep")
    errors, summaries, inputs = [], [], {}
    for eos, path in (("SRK", args.srk), ("PR", args.pr)):
        inputs[eos] = {"path": str(path), "sha256": digest(path)}
        seen = set()
        with path.open(newline="") as stream:
            for row in csv.DictReader(stream):
                key = (float(row["p_atm"]), float(row["T_requested_K"]))
                if key in seen or key not in EXPECTED:
                    raise ValueError("Unexpected/duplicate solver state: " + str(key))
                seen.add(key)
                inversion = float(row["inversion_relative_error"])
                if not math.isfinite(inversion) or abs(inversion) > 1e-6:
                    raise ValueError("Invalid enthalpy inversion: " + str(key))
                for name in PROPERTIES:
                    value, target = float(row[name]), reference[key][name]
                    if not all(math.isfinite(v) and v > 0 for v in (value, target)):
                        raise ValueError("Invalid property: " + str(key))
                    errors.append(dict(eos=eos, p_atm=key[0], T_K=key[1],
                                       property=name, computed=value, reference=target,
                                       relative_error=(value-target)/target))
        if seen != EXPECTED:
            raise ValueError("Incomplete solver sweep: " + eos)
        for pressure in (1, 50, 100, 200, 300):
            for name in PROPERTIES:
                group = [r for r in errors if r["eos"] == eos
                         and r["p_atm"] == pressure and r["property"] == name]
                worst = max(group, key=lambda r: abs(r["relative_error"]))
                summaries.append(dict(eos=eos, p_atm=pressure, property=name, count=len(group),
                    rms_relative_error=math.sqrt(sum(r["relative_error"]**2 for r in group)/len(group)),
                    max_absolute_relative_error=abs(worst["relative_error"]),
                    max_error_T_K=worst["T_K"]))
    args.output.mkdir(parents=True, exist_ok=False)
    for name, rows in (("errors.csv", errors), ("summary.csv", summaries)):
        with (args.output/name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    receipt = {"inputs": inputs, "reference": manifest,
               "qualification": "Comparison only; no universal agreement threshold imposed"}
    (args.output/"provenance.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    print("Compared 450 solver states; wrote 40 property/pressure summaries")


if __name__ == "__main__":
    main()
