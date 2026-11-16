"""Recompute chemistry at frozen physical-table nodes; no integration or fitting."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import cantera as ct
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_table(path):
    headers, blocks, current = {}, {}, None
    for line in path.read_text().splitlines():
        tokens = line.split('#', 1)[0].split()
        if not tokens:
            continue
        if tokens[0] == 'block':
            if current is not None:
                raise ValueError('Nested block')
            current = ' '.join(tokens[1:])
            if current in blocks:
                raise ValueError('Duplicate block')
            blocks[current] = []
        elif tokens[0] == 'end':
            if current is None:
                raise ValueError('Unmatched block end')
            current = None
        elif current is not None:
            blocks[current].append([float(x) for x in tokens])
        else:
            headers[tokens[0]] = tokens[1:]
    if current is not None or headers['schema'] != ['forge-fgm-table-v2']:
        raise ValueError('Complete v2 raw-progress table required')
    z, eta = np.array(headers['z'], float), np.array(headers['c'], float)
    if not (np.diff(z) > 0).all() or not (np.diff(eta) > 0).all():
        raise ValueError('Strict coordinate axes required')
    blocks = {k: np.array(v, float) for k, v in blocks.items()}
    if any(a.shape != (len(z), len(eta)) or not np.isfinite(a).all() for a in blocks.values()):
        raise ValueError('Nonfinite or incorrectly shaped block')
    return headers, blocks, z, eta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['table', 'metadata', 'mechanism', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--pressure', type=float, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text())
    if metadata['mechanismSha256'] != digest(args.mechanism) or metadata['thermoModel'] != 'ideal-gas':
        raise ValueError('Exact original ideal-concentration mechanism required')
    if metadata['canteraVersion'] != ct.__version__:
        raise ValueError('Producer and replay Cantera versions differ')
    h, blocks, z, eta = read_table(args.table)
    names = h['species']
    if names != metadata['speciesOrder'] or h['progress-species'] != ['CO2', 'CO']:
        raise ValueError('Species order or progress definition differs')
    gas = ct.Solution(str(args.mechanism))
    indices = [gas.species_index(name) for name in names]
    if len(indices) != gas.n_species:
        raise ValueError('Complete mechanism composition required')
    pressure = args.pressure
    if not np.isfinite(pressure) or pressure <= 0:
        raise ValueError('Explicit positive reference pressure required')
    y = np.stack([blocks['Y ' + name] for name in names], axis=-1)
    if y.min() < 0 or np.max(np.abs(y.sum(axis=-1)-1)) > 1e-10:
        raise ValueError('Nonnegative complete table composition required')
    report = dict(schema='g2-table-node-chemistry-audit/v1', readOnly=not args.apply,
        nodes=int(len(z)*len(eta)), pressure_Pa=pressure, canteraVersion=ct.__version__,
        inputHashes={str(p): digest(p) for p in [args.table, args.metadata, args.mechanism]},
        integration=False, fitting=False, CFDStateChanged=False, scientificAcceptance=False,
        interpretation='Pointwise ideal-concentration kinetics at frozen table Y and reference pressure. No SRK chemistry validation.')
    if not args.apply:
        print(json.dumps(report, indent=2))
        return
    args.out.mkdir(parents=True, exist_ok=False)
    offsets = [0., -100., -50., -20., 20., 50., 100.]
    rates = np.full((*blocks['Sc'].shape, len(offsets)), np.nan)
    normalization = 0.
    for i in range(len(z)):
        for j in range(len(eta)):
            composition = np.zeros(gas.n_species)
            composition[indices] = y[i, j]
            for k, offset in enumerate(offsets):
                temperature = blocks['Tdiag'][i, j] + offset
                if temperature <= 0:
                    continue
                gas.TPY = temperature, pressure, composition
                normalization = max(normalization, float(np.max(np.abs(gas.Y[indices]-y[i, j]))))
                mass = gas.net_production_rates * gas.molecular_weights
                rates[i, j, k] = mass[gas.species_index('CO2')] + mass[gas.species_index('CO')]
    baseline, stored = rates[:, :, 0], blocks['Sc']
    scale = max(float(np.max(np.abs(baseline))), float(np.max(np.abs(stored))))
    report.update(maxCanteraCompositionNormalization=normalization,
        storedAbsoluteNodeSum=float(np.sum(np.abs(stored))),
        baselineAbsoluteNodeSum=float(np.sum(np.abs(baseline))),
        nodeL1ErrorOverStoredL1=float(np.sum(np.abs(baseline-stored))/max(1e-300, np.sum(np.abs(stored)))),
        maximumAbsoluteSourceDifference_kg_m3_s=float(np.max(np.abs(baseline-stored))),
        resolvedSignThreshold_kg_m3_s=scale*1e-8,
        resolvedSignDisagreements=int(np.sum((baseline*stored < 0) & (np.minimum(np.abs(baseline), np.abs(stored)) > scale*1e-8))),
        temperatureSensitivity=[])
    for k, offset in enumerate(offsets[1:], 1):
        valid = np.isfinite(rates[:, :, k])
        report['temperatureSensitivity'].append(dict(offset_K=offset, availableNodes=int(valid.sum()),
            sourceL1ChangeOverBaselineL1=float(np.sum(np.abs(rates[:, :, k][valid]-baseline[valid]))/max(1e-300,np.sum(np.abs(baseline[valid]))))))
    file = args.out/'nodes.csv'
    with file.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['Z', 'eta', 'Ttable_K', 'stored_Sc_kg_m3_s', *['replayed_Sc_offset_'+str(t)+'K' for t in offsets]])
        for i in range(len(z)):
            for j in range(len(eta)):
                writer.writerow([z[i], eta[j], blocks['Tdiag'][i,j], stored[i,j], *rates[i,j]])
    report['nodesSha256'] = digest(file)
    (args.out/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
