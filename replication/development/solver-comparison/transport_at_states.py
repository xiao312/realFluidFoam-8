"""Compare saved native transport at identical frozen TPY states with Cantera.

Input is a job-keyed JSON snapshot with time_s and states. Each state supplies
T_K, p_Pa, rho_kg_m3, kappa_W_mK, all 53 mass fractions in Y, and Dimix_m2s.
This read-only comparison does not integrate a flame or fit model coefficients.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import cantera as ct


def compare(snapshot, mechanism, job):
    data = json.loads(snapshot.read_text(encoding='utf-8-sig'))[job]
    gas = ct.Solution(str(mechanism))
    states = []
    for row in data['states']:
        if len(row['Y']) != 53 or set(row['Y']) != set(gas.species_names):
            raise ValueError('Expected the same 53 named species')
        error = abs(sum(row['Y'].values())-1)
        if error > 1e-8 or min(row['Y'].values()) < 0:
            raise ValueError('Invalid frozen mass fractions')
        gas.TPY = row['T_K'], row['p_Pa'], row['Y']
        current = dict(T_K=row['T_K'], cell=row['cell'], species_sum_error=error,
            kappa_native=row['kappa_W_mK'], kappa_cantera=gas.thermal_conductivity,
            kappa_relative=row['kappa_W_mK']/gas.thermal_conductivity-1,
            density_relative=row['rho_kg_m3']/gas.density-1, Dimix={})
        for name, value in row['Dimix_m2s'].items():
            expected = float(gas.mix_diff_coeffs[gas.species_index(name)])
            if not math.isfinite(value) or value <= 0 or not expected > 0:
                raise ValueError('Invalid diffusivity')
            current['Dimix'][name] = dict(native=value, cantera=expected, relative=value/expected-1)
        if not all(math.isfinite(current[k]) for k in ['kappa_relative', 'density_relative']):
            raise ValueError('Invalid frozen property comparison')
        states.append(current)
    return dict(job=job, time_s=data['time_s'],
        snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        mechanism_sha256=hashlib.sha256(mechanism.read_bytes()).hexdigest(),
        cantera_version=ct.__version__, states=states, scientific_acceptance=False,
        comparison='Same frozen CFD T,p,Y; Cantera normalizes roundoff-level species sum error; no flame integration')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('mechanism', type=Path)
    parser.add_argument('job')
    args = parser.parse_args()
    print(json.dumps(compare(args.snapshot, args.mechanism, args.job), indent=2))
