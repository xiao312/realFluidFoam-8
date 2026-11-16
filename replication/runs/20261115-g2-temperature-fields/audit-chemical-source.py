"""Replay pointwise table-compatible chemistry; never advances or changes CFD."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

import cantera as ct
import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['cells', 'thermal-audit', 'species-collection', 'metadata', 'mechanism', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    here = Path(__file__).parent
    reader = load_module('chemical_field_reader', here / 'render-case.py')
    species_reader = load_module('chemical_species_reader', here / 'audit-species.py')
    receipt = json.loads(args.species_collection.read_text())
    audit = json.loads(args.thermal_audit.read_text())
    metadata = json.loads(args.metadata.read_text())
    if receipt['CFDStartTime_s'] != 0 or receipt['isTimeMean'] is not False:
        raise ValueError('Original-zero instantaneous fields required')
    if audit['collectionSha256'] != digest(args.species_collection) or audit['cellsCsvSha256'] != digest(args.cells):
        raise ValueError('Cell audit and original species collection differ')
    if metadata['mechanismSha256'] != digest(args.mechanism) or metadata['thermoModel'] != 'ideal-gas':
        raise ValueError('Exact table mechanism and ideal-gas concentration phase required')
    if ct.__version__ != metadata['canteraVersion']:
        raise ValueError('Cantera version differs from table producer')
    archive_path = Path(receipt['archivePath'])
    if digest(archive_path) != receipt['archiveSha256']:
        raise ValueError('Case-sensitive archive changed')
    cells = np.genfromtxt(args.cells, delimiter=',', names=True)
    count = len(cells)
    if not np.array_equal(cells['cell'], np.arange(count)) or not (cells['volume_m3'] > 0).all():
        raise ValueError('One-to-one positive-volume internal cells required')
    names = metadata['speciesOrder']
    fields = {name: np.full(count, np.nan) for name in [*names, 'T', 'p', 'fgmTdiag', 'fgmScSource']}
    root = Path(receipt['localRoot'])
    prefix = 'cases/' + receipt['case']
    with tarfile.open(archive_path) as archive:
        if len(archive.getnames()) != len(set(archive.getnames())):
            raise ValueError('Duplicate archive member')

        def member(name):
            raw = archive.extractfile(name).read()
            if hashlib.sha256(raw).hexdigest() != receipt['rawMemberHashes'][name]:
                raise ValueError('Changed or unbound archive member: ' + name)
            return raw

        manifest = json.loads(member(prefix + '/direct-g2-input.json'))
        if manifest['inputHashes']['metadata'] != digest(args.metadata):
            raise ValueError('Metadata differs from actual executing case')
        seen = np.zeros(count, dtype=int)
        for rank in range(receipt['ranks']):
            part = prefix + f'/processor{rank}'
            address = root / part / 'constant/polyMesh/cellProcAddressing'
            key = str(address.relative_to(root)).replace('\\', '/')
            if digest(address) != receipt['inputHashes'][key]:
                raise ValueError('Partition map changed')
            ids = reader.labels(address)
            if not ((ids >= 0) & (ids < count)).all():
                raise ValueError('Partition address outside global cells')
            seen[ids] += 1
            for name in fields:
                fields[name][ids] = species_reader.scalar(member(part + '/' + receipt['timeDirectory'] + '/' + name), name, len(ids))
    if not (seen == 1).all() or any(not np.isfinite(v).all() for v in fields.values()):
        raise ValueError('Missing or duplicate mapped cells')
    for name in ['T', 'p', 'fgmTdiag', 'fgmScSource']:
        if not np.array_equal(fields[name], cells[name]):
            raise ValueError('Thermal CSV differs from executing field: ' + name)
    gas = ct.Solution(str(args.mechanism), metadata['phase'])
    if gas.species_names != names:
        raise ValueError('Mechanism species order changed')
    indices = [gas.species_index(name) for name in ['CO', 'CO2']]
    rates = np.zeros((count, 3))
    normalization_error = 0.0
    for i in range(count):
        y = np.array([fields[name][i] for name in names])
        gas.set_unnormalized_mass_fractions(y)
        normalization_error = max(normalization_error, float(abs(gas.Y - y).max()))
        for j, (temperature, pressure) in enumerate([
            (fields['fgmTdiag'][i], manifest['pressure']),
            (fields['T'][i], manifest['pressure']),
            (fields['T'][i], fields['p'][i])]):
            gas.TP = temperature, pressure
            rates[i, j] = np.dot(gas.net_production_rates[indices], gas.molecular_weights[indices])
    if normalization_error != 0 or not np.isfinite(rates).all():
        raise ValueError('Composition was normalized or chemistry was nonfinite')
    volume = cells['volume_m3']
    stored = fields['fgmScSource']
    stored_l1 = float(np.sum(volume * abs(stored)))
    comparisons = []
    for j, label in enumerate(['table_T_reference_p', 'actual_T_reference_p', 'actual_T_actual_p']):
        difference = rates[:, j] - stored
        comparisons.append(dict(evaluation=label, signedIntegral_kg_s=float(np.sum(volume * rates[:, j])),
            absoluteIntegral_kg_s=float(np.sum(volume * abs(rates[:, j]))),
            absoluteDifferenceIntegral_kg_s=float(np.sum(volume * abs(difference))),
            relativeL1DifferenceOverStoredSource=float(np.sum(volume * abs(difference)) / stored_l1) if stored_l1 else None))
    report = dict(schema='g2-captured-pressure-based-chemistry-audit/v1',sourceJob=receipt['sourceJob'],
        time_s=receipt['time_s'],cells=count,pressureReference_Pa=manifest['pressure'],
        storedSourceAbsoluteIntegral_kg_s=stored_l1,comparisons=comparisons,
        compositionNormalized=False,maximumSetterCompositionChange=normalization_error,
        rateUnits='kg/m3/s for omega_CO + omega_CO2; integrals kg/s',
        model='Ideal-gas concentration chemistry from the original table mechanism; no EOS-density rescaling',
        limitations=['Stored source is a captured diagnostic, not necessarily a final-state source re-evaluation.',
                     'Table source interpolation and thermal/composition departure are distinct errors.',
                     'No chemistry integration, source correction, real-fluid kinetic validation or acceptance.'],
        inputHashes={str(p):digest(p) for p in [args.cells,args.thermal_audit,args.species_collection,args.metadata,args.mechanism]},
        archiveSha256=receipt['archiveSha256'],canteraVersion=ct.__version__,
        canteraBinarySha256=digest(ct._cantera.__file__),codeSha256=digest(__file__),
        scientificAcceptance=False,readOnly=not args.apply)
    if args.apply:
        args.out.mkdir(parents=True,exist_ok=False)
        output = args.out / 'cells.csv'
        with output.open('w',newline='') as handle:
            writer=csv.writer(handle)
            writer.writerow(['cell','x_mm','r_mm','volume_m3','stored_kg_m3_s','table_T_reference_p','actual_T_reference_p','actual_T_actual_p'])
            writer.writerows(zip(cells['cell'].astype(int),cells['x_mm'],cells['r_mm'],volume,stored,*rates.T))
        report['cellsCsvSha256']=digest(output)
        (args.out/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
