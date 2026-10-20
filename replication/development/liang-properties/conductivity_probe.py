"""Compare declared conductivity mappings at frozen states without solving flames."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from conductivity_math import REFERENCES, R, conductivity, mapping, shape, srk_volumes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    paths = [args.inputs/"ideal.yaml", args.inputs/"species.txt"]
    if args.profile:
        paths.append(args.profile)
    if not all(p.is_file() for p in paths) or args.output.exists():
        parser.error("Require existing inputs and a new output directory")
    print(json.dumps(dict(inputs=[str(p.resolve()) for p in paths],
                          output=str(args.output.resolve()), flame_solve=False)))
    if args.action == "plan":
        return
    import cantera as ct
    import numpy as np
    if ct.__version__ != "3.2.0":
        raise ValueError("Expected Cantera 3.2.0")
    records = [line.split() for line in paths[1].read_text().splitlines()]
    names = [r[0] for r in records]
    parameters = np.array([[float(v) for v in r[1:]] for r in records])
    gas = ct.Solution(str(paths[0]), transport_model="mixture-averaged")
    if gas.species_names != names:
        raise ValueError("Species order mismatch")
    rows, pure_checks, parity = [], [], []

    def evaluate(label, t, p, y):
        gas.TPY = t, p, y
        x = gas.X.copy()
        cp = gas.standard_cp_R.copy()
        v, _ = srk_volumes(t, p, x, parameters)
        ideal = gas.thermal_conductivity
        for mode, reference, corr in [
            ("partial", "current", False), ("partial", "current", True),
            ("coupled", "current", False), ("coupled", "current", True),
            ("coupled", "tn1039", True),
        ]:
            value = conductivity(t, v, x, parameters, cp, mode, reference, corr)
            dilute = conductivity(t, R*t, x, parameters, cp, mode, reference, corr)
            fine = conductivity(t, v, x, parameters, cp, mode, reference, corr, step=1e-6)
            dense_increment = ideal+value["lambda_W_mK"]-dilute["lambda_W_mK"]
            rows.append(dict(state=label, T_K=t, p_Pa=p, mapping=mode,
                             reference=reference, correction=corr, **value,
                             dilute_EH_W_mK=dilute["lambda_W_mK"],
                             Cantera_W_mK=ideal, dense_increment_W_mK=dense_increment,
                             ideal_over_dense_increment=ideal/dense_increment,
                             derivative_step_relative_change=abs(
                                 fine["lambda_W_mK"]/value["lambda_W_mK"]-1)))

    for t in (298., 300., 500., 800., 1200., 2000.):
        for phi in (1., 1.4, 2.1):
            for p in (ct.one_atm, 100*ct.one_atm):
                gas.set_equivalence_ratio(phi, "H2", "O2:0.21,N2:0.79")
                evaluate(f"fresh-phi{phi}", t, p, gas.Y.copy())

    # In a pure mixture the coupled reduced states reduce exactly to T/Tc,v/Vc.
    for name in ("H2", "O2", "N2", "H2O"):
        k = names.index(name)
        for t in (300., 800.):
            gas.TPX = t, 100*ct.one_atm, {name: 1.}
            x = gas.X.copy()
            v, _ = srk_volumes(t, gas.P, x, parameters)
            for ref in REFERENCES:
                fi, hi, *_ = mapping(t, v, x, parameters, REFERENCES[ref], "coupled")
                expected_f, expected_h = shape(t/parameters[:, 0], v/parameters[:, 2],
                                               parameters, REFERENCES[ref], 1e-12)
                error = max(abs(fi[k]/expected_f[k]-1), abs(hi[k]/expected_h[k]-1))
                pure_checks.append(dict(species=name, T_K=t, reference=ref, error=error))
                if error > 2e-10:
                    raise ValueError("Pure coupled map failed recovery")
            evaluate("pure-"+name, t, 100*ct.one_atm, gas.Y.copy())

    if args.profile:
        profile = list(csv.DictReader(args.profile.open()))
        for j in np.linspace(0, len(profile)-1, 35).astype(int):
            row = profile[j]
            y = np.maximum([float(row["Y_"+s]) for s in names], 0.)
            y /= sum(y)
            t, p = float(row["T_K"]), 100*ct.one_atm
            evaluate(f"flame-row{j}", t, p, y)
            reconstructed = rows[-5]["dense_increment_W_mK"]
            error = abs(reconstructed/float(row["lambda_W_mK"])-1)
            parity.append(dict(row=int(j), relative_error=error))
        if max(r["relative_error"] for r in parity) > 1e-7:
            raise ValueError("Python baseline differs from supplied C++ dense-increment profile")
    maximum_step = max(row["derivative_step_relative_change"] for row in rows)
    if maximum_step > 1e-5:
        raise ValueError("Fixed-volume derivative lacks step convergence")
    args.output.mkdir(parents=True)
    with (args.output/"states.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(
        cantera_version=ct.__version__, rows=len(rows), pure_recovery=pure_checks,
        profile_parity=parity, maximum_derivative_step_change=maximum_step,
        input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        scientific_acceptance=False,
        limits=["SRK prescribed-volume hybrid; not full methane-reference-EOS TRAPP",
                "No Liang rich-H2 modification identified or fitted",
                "Dense increment retains Cantera dilute transport by explicit subtraction",
                "No critical enhancement or empirical binary interaction fitted"])
    (args.output/"summary.json").write_text(json.dumps(summary, indent=2)+"\n",
                                          encoding="utf-8", newline="\n")
    print(json.dumps(dict(rows=len(rows), pure_checks=len(pure_checks),
                          profile_parity=max((r["relative_error"] for r in parity), default=0),
                          maximum_derivative_step_change=maximum_step)))


if __name__ == "__main__":
    main()
