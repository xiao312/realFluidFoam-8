"""Compare local ODE-averaged sources with instantaneous sources at frozen states.

This read-only analysis separates a source-averaging change from an integrator
parity error. It does not predict the error of a coupled CFD flame.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def analyze(path, closure):
    groups = {}
    with path.open(encoding='utf8', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['reactor'] != closure:
                continue
            interval = float(row['interval_s'])
            rate = float(row['RR_kg_m3_s'])
            temperature = float(row['T_initial_K'])
            if not all(math.isfinite(v) for v in [interval, rate, temperature]) or interval < 0:
                raise ValueError('Invalid interval, rate or temperature')
            group = groups.setdefault((int(row['state']), interval), {})
            if row['species'] in group:
                raise ValueError('Duplicate species observation')
            group[row['species']] = (rate, temperature)
    if not groups:
        raise ValueError('No observations for the requested closure')
    results = []
    for (state, interval), current in sorted(groups.items()):
        if not interval:
            continue
        initial = groups.get((state, 0))
        if initial is None or set(initial) != set(current) or len(initial) != 53:
            raise ValueError('Each interval needs the same 53 instantaneous species')
        if any(initial[k][1] != current[k][1] for k in initial):
            raise ValueError('Compared sources do not share initial temperature')
        scale = sum(abs(v[0]) for v in initial.values())
        if not scale:
            raise ValueError('Instantaneous source vector is zero')
        species = {}
        for name in ['CH4', 'OH', 'H', 'O', 'H2', 'HO2']:
            before, after = initial[name][0], current[name][0]
            species[name] = dict(instantaneous_kg_m3_s=before,
                averaged_kg_m3_s=after, difference_kg_m3_s=after-before,
                relative_change=None if before == 0 else (after-before)/abs(before))
        results.append(dict(state=state, temperature_K=initial['CH4'][1], interval_s=interval,
            source_vector_L1_relative=sum(abs(current[k][0]-initial[k][0]) for k in initial)/scale,
            species=species))
    return dict(input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        closure=closure, results=results, scientific_acceptance=False,
        limit='Frozen local ODE comparison; transport is absent. Not a CFD speed-error estimate.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--closure', default='openfoam-concentration-cp', choices=[
        'openfoam-concentration-cp', 'constant-pressure-adiabatic', 'constant-volume-isothermal'])
    args = parser.parse_args()
    print(json.dumps(analyze(args.csv, args.closure), indent=2))
