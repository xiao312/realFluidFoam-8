"""Inspect all named mixture diffusivity ratios at identical saved flame states."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("inputs", "profile", "transport", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]/"validation/diffusion"
    paths = [args.inputs/"ideal.yaml", args.inputs/"species.txt", args.inputs/"pairs.txt",
             args.profile, args.transport, root/"references.json"]
    if not all(p.is_file() for p in paths) or args.output.exists():
        parser.error("Existing inputs and a new output directory are required")
    if paths[2].read_text().strip():
        parser.error("This independent replay supports LJ control inputs only")
    print(json.dumps(dict(output=str(args.output.resolve()), flame_solve=False)))
    if args.action == "plan":
        return
    import cantera as ct
    import numpy as np
    if ct.__version__ != "3.2.0":
        raise ValueError("Expected Cantera 3.2.0")
    spec = importlib.util.spec_from_file_location("takahashi_reference", root/"prepare.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    table = json.loads(paths[-1].read_text())["takahashi"]["table2"]
    parameters = [line.split() for line in paths[1].read_text().splitlines()]
    names = [r[0] for r in parameters]
    tc = np.array([float(r[1]) for r in parameters])
    pc = np.array([float(r[2]) for r in parameters])
    gas = ct.Solution(str(paths[0]), transport_model="mixture-averaged")
    if gas.species_names != names:
        raise ValueError("Species order mismatch")
    profile = list(csv.DictReader(args.profile.open()))
    transport = list(csv.DictReader(args.transport.open()))
    if len(profile) != len(transport):
        raise ValueError("Profile and transport rows differ")
    temperatures = np.array([float(r["T_K"]) for r in profile])
    indices = sorted(set(np.argmin(abs(temperatures-t)) for t in
                         [298, 300, 400, 500, 600, 800, 1000, 1200, 1500, 1800, 2000, 2400]))
    results, errors = [], []
    for index in indices:
        row, actual = profile[index], transport[index]
        t, p = float(row["T_K"]), 100*ct.one_atm
        gas.TPY = t, p, [float(row["Y_"+s]) for s in names]
        x = np.maximum(gas.X, 1e-20)
        dilute = gas.binary_diff_coeffs
        for i, name in enumerate(names):
            denominator, corrected = 0., 0.
            for j in range(len(names)):
                if i == j:
                    continue
                xi, xj = x[i]/(x[i]+x[j]), x[j]/(x[i]+x[j])
                factor = module.correction(p/(xi*pc[i]+xj*pc[j]), t/(xi*tc[i]+xj*tc[j]), table)
                denominator += x[j]/dilute[i, j]
                corrected += x[j]/(dilute[i, j]*factor)
            ratio = denominator/corrected
            results.append(dict(row=int(index), T_K=t, species=name,
                                Y=float(gas.Y[i]), ratio=float(ratio)))
            if name in ("H2", "O2", "N2"):
                errors.append(abs(ratio/float(actual[f"Dmix_{name}_real_over_ideal"])-1))
    maximum = max(errors)
    if maximum > 1e-7:
        raise ValueError(f"Independent replay disagrees with C++: {maximum}")
    args.output.mkdir(parents=True)
    with (args.output/"ratios.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    evidence = dict(input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                    maximum_cpp_parity_error=maximum, cpp_checks=len(errors), rows=len(results),
                    scientific_acceptance=False,
                    limitation="Paper Figure 6 does not specify a species or pair; no identity inferred")
    (args.output/"summary.json").write_text(json.dumps(evidence, indent=2)+"\n",
                                          encoding="utf-8", newline="\n")
    print(json.dumps(dict(maximum_cpp_parity_error=maximum, cpp_checks=len(errors))))


if __name__ == "__main__":
    main()
