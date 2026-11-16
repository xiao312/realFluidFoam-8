"""Qualify a numerical Z-grid control from retained physical exports."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(directory):
    receipt = json.loads((directory / 'receipt.json').read_text())
    for name, key in [('physical.tbl', 'table_sha256'), ('phase-metadata.json', 'metadata_sha256')]:
        if sha(directory / name) != receipt[key]:
            raise ValueError('Changed export: ' + str(directory / name))
    metadata = json.loads((directory / 'phase-metadata.json').read_text())
    initial = json.loads((directory / 'initialization.json').read_text())
    with np.load(directory / 'table.npz') as stored:
        arrays = {key: stored[key].copy() for key in stored.files}
    return receipt, metadata, initial, arrays


def evaluate(baseline, reproduced, candidate):
    directories = [baseline, reproduced, candidate]
    exports = [load(path) for path in directories]
    reference, original_metadata, original_initial, original = exports[0]
    physics = ['schema', 'canteraVersion', 'mechanismSha256', 'thermoModel', 'phase',
               'gasConstant_J_kmol_K', 'speciesOrder', 'species', 'transportModelQualified']
    streams = ['cold_air_Y', 'cold_fuel_Y', 'cold_air_Ha_J_kg', 'cold_fuel_Ha_J_kg']
    for receipt, metadata, initial, arrays in exports[1:]:
        for key in ['mechanism_sha256', 'environment_sha256', 'nZ', 'nC']:
            if receipt[key] != reference[key]:
                raise ValueError('Changed physical export binding: ' + key)
        for key in physics:
            if metadata[key] != original_metadata[key]:
                raise ValueError('Changed thermodynamic property: ' + key)
        for key in streams:
            if initial[key] != original_initial[key]:
                raise ValueError('Changed cold stream: ' + key)
        if not np.array_equal(arrays['species'], original['species']):
            raise ValueError('Changed species order')
        if not np.array_equal(arrays['progress_weights'], original['progress_weights']):
            raise ValueError('Changed progress definition')
    for key in original:
        if not np.array_equal(original[key], exports[1][3][key]):
            raise ValueError('Default re-export changes numeric array: ' + key)
    def numeric_lines(directory):
        return [line for line in (directory / 'physical.tbl').read_text().splitlines()
                if not line.startswith('source ')]
    if numeric_lines(baseline) != numeric_lines(reproduced):
        raise ValueError('Default numeric table differs beyond its source revision')
    receipt, metadata, _, data = exports[2]
    if receipt.get('mixture_fraction_grid') != 'uniform':
        raise ValueError('Candidate must explicitly declare the uniform grid')
    expected = np.linspace(original['Z'][0], original['Z'][-1], len(original['Z']))
    if not np.array_equal(data['Z'], expected) or not (np.diff(data['Z']) > 0).all():
        raise ValueError('Candidate Z grid is not exactly uniform')
    if np.array_equal(original['Z'], data['Z']):
        raise ValueError('Original grid is already uniform; this is not a distinct control')
    if not np.array_equal(original['eta'], data['eta']):
        raise ValueError('Progress grid changed with Z grid')
    values = data['values']
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite candidate values')
    y = values[:, :, 3:]
    progress = data['c_min'][:, None] + data['eta'][None, :] * (data['c_max'] - data['c_min'])[:, None]
    mass_error = float(np.max(abs(y.sum(axis=2) - 1)))
    progress_error = float(np.max(abs(y @ data['progress_weights'] - progress)))
    # Bilger numerator divided by molecular weight; atomic weights cancel.
    beta = np.array([(2*s['composition'].get('C', 0) + .5*s['composition'].get('H', 0)
                      - s['composition'].get('O', 0)) / s['molecularWeight_kg_kmol']
                     for s in metadata['species']])
    beta_air = np.array(original_initial['cold_air_Y']) @ beta
    beta_fuel = np.array(original_initial['cold_fuel_Y']) @ beta
    z_species = (y @ beta - beta_air) / (beta_fuel - beta_air)
    z_error = float(np.max(abs(z_species - data['Z'][:, None])))
    if y.min() < -1e-12 or max(mass_error, progress_error, z_error) > 1e-8:
        raise ValueError('Candidate violates conserved mass/progress/mixture fraction')
    return {
        'schema': 'maders-uniform-z-grid-qualification/v1',
        'defaultNumericTableParity': True, 'unchangedThermodynamicProperties': True,
        'unchangedColdStreams': True, 'uniformZ': True,
        'maximumMassSumError': mass_error, 'maximumWeightedProgressError': progress_error,
        'maximumSpeciesMixtureFractionError': z_error,
        'maximumGridDisplacement': float(max(abs(original['Z'] - data['Z']))),
        'inputs': {str(path / name): sha(path / name) for path in directories
                   for name in ['receipt.json', 'physical.tbl', 'table.npz', 'phase-metadata.json', 'initialization.json']},
        'scientificAcceptance': False,
        'remainingChecks': ['Independent executing C++ reader', 'Unchanged held-out physical data', 'Fresh original-zero CFD'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline', 'reproduced', 'candidate', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Refusing existing output')
    result = evaluate(args.baseline, args.reproduced, args.candidate)
    if not args.apply:
        print(json.dumps({'readOnly': True, 'out': str(args.out), 'qualification': result}, indent=2))
        return
    args.out.mkdir(parents=True)
    (args.out / 'qualification.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
