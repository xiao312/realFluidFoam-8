"""Read-only energy effect of legacy native versus Cantera molecular weights."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs', type=Path)
    p.add_argument('reference', type=Path)
    a = p.parse_args()
    import cantera as ct
    import numpy as np
    if ct.__version__ != '3.2.0':
        raise ValueError('Expected Cantera 3.2.0')
    ref = json.loads(a.reference.read_text())
    gas = ct.Solution(str(a.inputs/'ideal.yaml'))
    table = {s[0]: float(s[4]) for line in (a.inputs/'species.txt').read_text().splitlines()
             if (s := line.split())}
    weights = np.array([table[name] for name in gas.species_names])
    if gas.species_names != ref['species']:
        raise ValueError('Reference species ordering mismatch')
    result = []
    for row in ref['cases']:
        gas.TP = row['T0'], row['p']
        gas.set_unnormalized_mass_fractions(row['Y0'])
        h0 = float(np.dot(row['Y0'], gas.partial_molar_enthalpies/weights))
        gas.TP = row['T'], row['p']
        gas.set_unnormalized_mass_fractions(row['Y'])
        h = float(np.dot(row['Y'], gas.partial_molar_enthalpies/weights))
        cp = float(np.dot(row['Y'], gas.partial_molar_cp/weights))
        result.append(dict(initial_T=row['T0'], duration_s=row['duration'],
                           native_enthalpy_difference_J_kg=h-h0,
                           equivalent_temperature_difference_K=(h-h0)/cp))
    print(json.dumps(dict(cases=result, maximum_weight_relative_difference=float(
        np.max(np.abs(gas.molecular_weights/weights-1))),
        reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest()), indent=2))


if __name__ == '__main__':
    main()
