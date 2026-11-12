"""Trusted physical-data lookup diagnostic. No candidate code is imported."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from scipy.interpolate import PchipInterpolator
from lookup_baseline import build, query


def source(model, z, c, scheme):
    grid, rows = model
    i = min(len(grid)-2, max(0, int(np.searchsorted(grid, z, side='right')-1)))
    w = (z-grid[i])/(grid[i+1]-grid[i])
    lo = (1-w)*rows[i][0][0]+w*rows[i+1][0][0]
    hi = (1-w)*rows[i][0][-1]+w*rows[i+1][0][-1]
    if hi-lo <= 1e-14:
        return (1-w)*rows[i][1][0, 1]+w*rows[i+1][1][0, 1]
    eta = (c-lo)/(hi-lo)
    values = []
    for axis, fields in rows[i:i+2]:
        location = axis[0]+eta*(axis[-1]-axis[0])
        if scheme == 'linear' or len(axis) < 3:
            values.append(float(np.interp(location, axis, fields[:, 1])))
        else:
            values.append(float(PchipInterpolator(axis, fields[:, 1], extrapolate=False)(location)))
    return (1-w)*values[0]+w*values[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--scheme', choices=['linear', 'pchip'], required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((args.assets/'training/manifest.json').read_text())
    paths = [args.assets/'training'/p for p in manifest['profiles']]
    model = build(paths)
    with np.load(args.assets/'evaluation/queries.npz') as coordinates:
        values, covered = [], []
        for z, c in zip(coordinates['Z'], coordinates['C']):
            try:
                value = query(model, float(z), float(c))
                value[1] = source(model, float(z), float(c), args.scheme)
                covered.append(True)
            except ValueError:
                value = np.full(2+manifest['species_count'], np.nan)
                covered.append(False)
            values.append(value)
    values = np.asarray(values)
    prediction = args.out/'predictions.npz'
    np.savez_compressed(prediction, T=values[:, 0], Sc_kg_m3_s=values[:, 1],
                        Y=values[:, 2:], covered=covered)
    subprocess.run([sys.executable, str(Path(__file__).with_name('evaluate_lookup.py')),
                    '--reference', str(args.assets/'evaluation/reference.npz'),
                    '--predictions', str(prediction), '--out', str(args.out/'metrics.json')], check=True)
    metrics = json.loads((args.out/'metrics.json').read_text())
    score = metrics['coverage']/(1 + metrics['errors']['Sc_kg_m3_s']['RMSE']/metrics['source_global_peak_kg_m3_s']
                                 + metrics['nontrivial_source_sign_errors']/metrics['queries'])
    result = {'validity': 1.0, 'combined_score': score, 'cost_time': 0, 'error_info': '',
              'metric': {'scheme': args.scheme, 'physical_lookup': metrics,
                         'assets_sha256': {str(p.relative_to(args.assets)): hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in paths + [args.assets/'evaluation/reference.npz', args.assets/'evaluation/queries.npz']},
                         'limitations': 'Retained family includes failed high-chi solve. Not new flamelet convergence, CFD, paper acceptance or merge approval.'}}
    (args.out/'result.json').write_text(json.dumps(result, allow_nan=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
