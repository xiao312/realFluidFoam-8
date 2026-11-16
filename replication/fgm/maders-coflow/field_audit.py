"""Read-only mapped-table/enthalpy audit of retained Maders radial profiles."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interpolate(table, mixture, progress):
    """Use the reader's shared eta at both Z rows, not raw-C interpolation."""
    z, eta = table['Z'], table['eta']
    if not np.isfinite([mixture, progress]).all() or not z[0] <= mixture <= z[-1]:
        return None
    lo = np.interp(mixture, z, table['c_min'])
    hi = np.interp(mixture, z, table['c_max'])
    e = (progress-lo)/(hi-lo) if hi > lo else 0.
    if (hi <= lo and progress != lo) or not eta[0] <= e <= eta[-1]:
        return None
    i = min(len(z)-2, max(0, int(np.searchsorted(z, mixture, side='right')-1)))
    j = min(len(eta)-2, max(0, int(np.searchsorted(eta, e, side='right')-1)))
    wz, we = (mixture-z[i])/(z[i+1]-z[i]), (e-eta[j])/(eta[j+1]-eta[j])
    v = table['values']
    return ((1-wz)*((1-we)*v[i, j]+we*v[i, j+1])
            + wz*((1-we)*v[i+1, j]+we*v[i+1, j+1]))


def stats(values):
    v = np.asarray(values)
    return None if not len(v) else dict(count=len(v), minimum=float(v.min()),
        maximum=float(v.max()), rms=float(np.sqrt(np.mean(v*v))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['table', 'initialization', 'samples']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--table-sha256', required=True)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--pressure-pa', type=float)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    if (args.metadata is None) != (args.pressure_pa is None):
        raise ValueError('Density audit requires both --metadata and --pressure-pa')
    if args.pressure_pa is not None and (not np.isfinite(args.pressure_pa) or args.pressure_pa <= 0):
        raise ValueError('Density reference pressure must be positive and finite')
    if digest(args.table) != args.table_sha256:
        raise ValueError('Executed NPZ table SHA256 mismatch')
    files = sorted(args.samples.glob('h*_T_*.csv'))
    if not files:
        raise ValueError('No radial physical profiles')
    report = dict(schema='maders-field-table-audit/v1', table_sha256=digest(args.table),
        initialization_sha256=digest(args.initialization), driver_sha256=digest(Path(__file__)),
        samples={p.name: digest(p) for p in files}, scientific_acceptance=False,
        limits='Pointwise reconstruction from interpolated samples, not exact cell closure; '
        'nonzero Ha mixing residual also contains physical diffusion/work effects.')
    if args.plan:
        print(json.dumps(dict(plan=True, **report), indent=2)); return
    with np.load(args.table, allow_pickle=False) as archive:
        table = {key: archive[key] for key in ['Z', 'eta', 'c_min', 'c_max', 'values']}
        species = archive['species'].tolist()
    for axis in ['Z', 'eta']:
        if len(table[axis]) < 2 or not np.all(np.diff(table[axis]) > 0):
            raise ValueError('Table axes are not strictly increasing')
    if not np.isfinite(table['values']).all():
        raise ValueError('Nonfinite table values')
    init = json.loads(args.initialization.read_text())
    density_table = None
    if args.metadata:
        metadata = json.loads(args.metadata.read_text())
        if species != [s['name'] for s in metadata['species']]:
            raise ValueError('Density metadata species order differs from executed table')
        gas_constants = np.array([metadata['gasConstant_J_kmol_K']/s['molecularWeight_kg_kmol']
                                  for s in metadata['species']])
        # Only the atmospheric ideal-gas Maders comparison: this is deliberately
        # not a reconstruction of SRK density for the G2 cases.
        rho_nodes = args.pressure_pa/(table['values'][:, :, 0]
                                     * (table['values'][:, :, 3:] @ gas_constants))
        if not np.isfinite(rho_nodes).all() or np.any(rho_nodes <= 0):
            raise ValueError('Invalid reconstructed ideal-gas nodal density')
        density_table = {**table, 'values': rho_nodes[:, :, None]}
        report['density_reference'] = dict(pressure_Pa=args.pressure_pa,
            metadata_sha256=digest(args.metadata),
            method='Ideal-gas density at exported nodes, then mapped interpolation; '
            'not an actual author density table or exact cell-state reconstruction.')
    report['profiles'] = []
    for path in files:
        a = np.genfromtxt(path, delimiter=',', names=True)
        required = ['T', 'Z', 'c', 'Ha', 'fgmTdiag', 'fgmScSource']
        if any(k not in a.dtype.names for k in required):
            raise ValueError(f'Missing sampled field in {path}')
        if any(not np.isfinite(a[k]).all() for k in required):
            raise ValueError(f'Nonfinite sampled field in {path}')
        t_error, diagnostic_error, source_error = [], [], []
        density_error, hot_density_relative = [], []
        uncovered = 0
        for row in a:
            value = interpolate(table, float(row['Z']), float(row['c']))
            if value is None:
                uncovered += 1; continue
            diagnostic_error.append(float(row['fgmTdiag'])-value[0])
            source_error.append(float(row['fgmScSource'])-value[1])
            if row['T'] > 500:
                t_error.append(float(row['T'])-value[0])
            if density_table is not None:
                if 'rho' not in a.dtype.names or not np.isfinite(row['rho']) or row['rho'] <= 0:
                    raise ValueError('Density audit requires finite positive sampled rho')
                expected = interpolate(density_table, float(row['Z']), float(row['c']))[0]
                density_error.append(float(row['rho'])-expected)
                if row['T'] > 500:
                    hot_density_relative.append((float(row['rho'])-expected)/float(row['rho']))
        mixed = a['Z']*init['cold_fuel_Ha_J_kg']+(1-a['Z'])*init['cold_air_Ha_J_kg']
        report['profiles'].append(dict(file=path.name, rows=len(a), uncovered=uncovered,
            hot_T_minus_reconstructed_table_K=stats(t_error),
            sampled_Tdiag_minus_table_K=stats(diagnostic_error),
            sampled_source_minus_table_kg_m3_s=stats(source_error),
            Ha_minus_linear_streams_J_kg=stats(a['Ha']-mixed),
            rho_minus_interpolated_node_density_kg_m3=stats(density_error),
            hot_rho_relative_to_interpolated_node_density=stats(hot_density_relative),
            note='Diagnostic-field disagreement is not evidence of caloric failure.'))
    text = json.dumps(report, indent=2, allow_nan=False)+'\n'
    if args.out:
        with args.out.open('x', encoding='utf-8') as output:
            output.write(text)
    print(text)


if __name__ == '__main__':
    main()
