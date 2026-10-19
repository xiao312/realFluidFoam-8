"""Prepare independent Python Cantera constant-pressure chemistry references."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply'])
    for name in ['mechanism', 'profile', 'output']:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    for path in [args.mechanism, args.profile]:
        path.resolve(strict=True)
    if args.output.exists():
        raise ValueError('Reference output already exists')
    print('Plan: 21 independent closed CP reactors; original inputs read-only; '+str(args.output))
    if args.action == 'plan':
        return
    import cantera as ct
    if ct.__version__ != '3.2.0':
        raise ValueError('Expected Cantera 3.2.0')
    gas = ct.Solution(str(args.mechanism))
    rows = list(csv.DictReader(args.profile.open()))
    results = []
    for target in [298, 600, 900, 1200, 1500, 1800, 2100]:
        row = min(rows, key=lambda r: abs(float(r['T_K'])-target))
        initial = [float(row['Y_'+name]) for name in gas.species_names]
        for duration in [5e-8, 5e-7, 5e-6]:
            gas.TP = float(row['T_K']), 10132500
            gas.set_unnormalized_mass_fractions(initial)
            gas.TP = float(row['T_K']), 10132500
            h0 = gas.enthalpy_mass
            reactor = ct.ConstPressureReactor(gas, clone=True, volume=1)
            network = ct.ReactorNet([reactor])
            network.rtol, network.atol = 1e-10, 1e-18
            network.max_steps = 20000
            network.advance(duration)
            results.append(dict(target_T=target, T0=float(row['T_K']), p=10132500,
                                duration=duration, Y0=initial, T=reactor.T,
                                Y=reactor.phase.Y.tolist(), h0=h0,
                                h=reactor.phase.enthalpy_mass))
    output = dict(cantera_version=ct.__version__, relative_tolerance=1e-10,
                  absolute_tolerance=1e-18, species=gas.species_names,
                  molecular_weights=gas.molecular_weights.tolist(),
                  element_mass_matrix=[[gas.n_atoms(k, e)*gas.atomic_weight(e)/gas.molecular_weights[k]
                                        for k in range(gas.n_species)] for e in range(gas.n_elements)],
                  hashes={name: hashlib.sha256(getattr(args, name).read_bytes()).hexdigest()
                          for name in ['mechanism', 'profile']}, cases=results)
    args.output.write_text(json.dumps(output, indent=2)+'\n')
    print('Wrote 21 CP reference states')


if __name__ == '__main__':
    main()
