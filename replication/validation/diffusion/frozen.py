"""Locate pressure/range-policy contributions at fixed saved flame states."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from prepare import correction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = [args.inputs/"ideal.yaml", args.inputs/"species.txt", args.profile,
             Path(__file__).with_name("references.json")]
    if not all(p.is_file() for p in paths):
        parser.error("Missing input")
    if args.output is None:
        print("Plan: eight frozen faces, all ordered binary pairs; no flame solve")
        return
    if args.output.exists():
        parser.error("Select a new output directory")
    import cantera as ct
    import numpy as np
    if ct.__version__ != "3.2.0":
        raise ValueError("Expected Cantera 3.2.0")
    gas = ct.Solution(str(paths[0]), transport_model="mixture-averaged")
    parameters = [line.split() for line in paths[1].read_text().splitlines()]
    names = [r[0] for r in parameters]
    if names != gas.species_names or len(names) != 53:
        raise ValueError("Species order mismatch")
    with args.profile.open() as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames[7:] != ["Y_"+name for name in names]:
            raise ValueError("Unexpected profile species columns")
        data = list(reader)
    temperatures = np.array([float(r["T_K"]) for r in data])
    critical_t = np.array([float(r[1]) for r in parameters])
    critical_p = np.array([float(r[2]) for r in parameters])
    table = json.loads(paths[3].read_text())["takahashi"]["table2"]
    pairs, species_rows, states = [], [], []
    pressure = 100*101325.
    for target in [300, 400, 600, 900, 1200, 1500, 1800, 2100]:
        left = int(np.argmin(abs((temperatures[:-1]+temperatures[1:])/2-target)))
        a, b = data[left:left+2]
        y = np.array([(float(a["Y_"+s])+float(b["Y_"+s]))/2 for s in names])
        # Match transport's nonnegative composition projection, not Newton residuals.
        y = np.maximum(y, 0); y /= y.sum()
        temperature = (temperatures[left]+temperatures[left+1])/2
        gas.TPY = temperature, pressure, y
        x = np.maximum(gas.X, 1e-20)
        dilute = gas.binary_diff_coeffs
        states.append(dict(target_K=target, actual_K=float(temperature), face_index=left))
        for i, name in enumerate(names):
            items = []
            for j, partner in enumerate(names):
                if i == j:
                    continue
                wi = x[i]/(x[i]+x[j]); wj = x[j]/(x[i]+x[j])
                pr = pressure/(wi*critical_p[i]+wj*critical_p[j])
                tr = temperature/(wi*critical_t[i]+wj*critical_t[j])
                factor = correction(pr, tr, table)
                extrapolated = correction(pr, tr, table, upper_clamp=False)
                dense = dilute[i, j]*factor
                items.append(dict(target_K=target, actual_K=float(temperature),
                                  species=name, partner=partner, Pr=float(pr), Tr=float(tr),
                                  Xi=float(x[i]), Xj=float(x[j]), factor=factor,
                                  dilute_m2_s=float(dilute[i, j]), corrected_m2_s=float(dense),
                                  denominator_term=float(x[j]/dense),
                                  upper_unclamped_denominator_term=float(x[j]/(dilute[i, j]*extrapolated)),
                                  low_Pr=bool(pr < .1), Tr_clamped=bool(tr < 1 or tr > 5)))
            denominator = sum(r["denominator_term"] for r in items)
            extrapolated_denominator = sum(r["upper_unclamped_denominator_term"] for r in items)
            for item in items:
                item["denominator_fraction"] = item["denominator_term"]/denominator
            low = sum(r["denominator_fraction"] for r in items if r["low_Pr"])
            clamped = sum(r["denominator_fraction"] for r in items if r["Tr_clamped"])
            upper = sum(r["denominator_fraction"] for r in items if r["Tr"] > 5)
            lower = sum(r["denominator_fraction"] for r in items if r["Tr"] < 1)
            species_rows.append(dict(target_K=target, species=name, mass_fraction=float(y[i]),
                                     low_Pr_denominator_fraction=low,
                                     Tr_clamped_denominator_fraction=clamped,
                                     Tr_upper_clamped_fraction=upper,
                                     Tr_lower_clamped_fraction=lower,
                                     upper_unclamped_mix_change_percent=100*(denominator/extrapolated_denominator-1),
                                     mix_corrected_m2_s=float((1-y[i])/denominator)))
            pairs.extend(items)
    args.output.mkdir(parents=True)
    with (args.output/"pairs.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(pairs[0]))
        writer.writeheader(); writer.writerows(pairs)
    major = {"H", "H2", "O", "OH", "CH4", "O2", "N2", "H2O", "CO", "CO2"}
    major_rows = [r for r in species_rows if r["species"] in major]
    report = dict(cantera_version=ct.__version__, pressure_pa=pressure, states=states,
                  ordered_pair_samples=len(pairs),
                  input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  maximum_low_Pr_fraction_all=max(r["low_Pr_denominator_fraction"] for r in species_rows),
                  maximum_low_Pr_fraction_major=max(r["low_Pr_denominator_fraction"] for r in major_rows),
                  major_species=major_rows, scientific_acceptance=False,
                  limits=["Independent correlation replay, not actual C++ adapter output",
                          "Eight representative faces, not the entire flame",
                          "Denominator fractions are not additive flame-speed sensitivities",
                          "Upper-unclamped values extrapolate Takahashi beyond its main fitted temperature range",
                          "Negative saved mass fractions projected to zero for transport"])
    with (args.output/"summary.json").open("x") as stream:
        json.dump(report, stream, indent=2); stream.write("\n")
    print(json.dumps({key: report[key] for key in [
        "ordered_pair_samples", "maximum_low_Pr_fraction_all", "maximum_low_Pr_fraction_major"]}))


if __name__ == "__main__":
    main()
