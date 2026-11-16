"""Map actual cold-flow cells meeting the executing ignition coordinates."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['collection', 'audit', 'cells', 'out']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    receipt = json.loads(args.collection.read_text())
    audit = json.loads(args.audit.read_text())
    if receipt.get('CFDStartTime_s') != 0 or receipt.get('isTimeMean') is not False:
        raise ValueError('Original-zero instantaneous cell collection required')
    if receipt.get('stateQualification') != 'retained-timestep':
        raise ValueError('Retained pre-ignition timestep required')
    if audit['collectionSha256'] != sha(args.collection) or audit['cellsCsvSha256'] != sha(args.cells):
        raise ValueError('Internal audit and cells belong to another collection')
    base = Path(receipt['localRoot']).resolve()
    bound = set()
    for relative, expected in receipt['inputHashes'].items():
        file = (base/relative).resolve()
        if not file.is_relative_to(base) or sha(file) != expected:
            raise ValueError('Changed or escaping retained input: '+relative)
        bound.add(file)
    protocol_file = base/'cases'/receipt['case']/'ignition-protocol.json'
    if protocol_file.resolve() not in bound:
        raise ValueError('Executing ignition protocol is not hash-bound')
    protocol = json.loads(protocol_file.read_text())
    origin = protocol['rawAxialOrigin_m']
    length = protocol['length_m']
    lower, upper = protocol['Zrange']
    if protocol['CFDStart'] != 0 or protocol['evolvedStart'] or not protocol['localZPreserved']:
        raise ValueError('Fresh local-Z ignition protocol required')
    if origin != receipt['axialOrigin_m'] or not length > 0 or not 0 <= lower < upper <= 1:
        raise ValueError('Invalid or inconsistent ignition coordinates')
    if not 0 <= receipt['time_s'] < protocol['sourcePausedUntil']:
        raise ValueError('Cold-region diagnostic requires a pre-ignition snapshot')
    case = protocol_file.parent
    required = [case/'constant/polyMesh'/name for name in ['points', 'faces', 'owner', 'neighbour']]
    for rank in range(receipt['ranks']):
        part = case/f'processor{rank}'
        required.extend([part/'constant/polyMesh/cellProcAddressing', part/receipt['timeDirectory']/'T'])
    if any(file.resolve() not in bound for file in required):
        raise ValueError('Consumed mesh, temperature or partition is not hash-bound')
    spec = importlib.util.spec_from_file_location('ignition_cell_reader', Path(__file__).with_name('render-case.py'))
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    polygons, centres, temperature = reader.load_cells(receipt, base)
    data = np.genfromtxt(args.cells, delimiter=',', names=True)
    if not np.array_equal(data['cell'], np.arange(len(temperature))) or not np.array_equal(data['T'], temperature):
        raise ValueError('CSV cells differ from original partition/temperature mapping')
    if not np.allclose(centres, np.column_stack([data['x_mm'], data['r_mm']]), rtol=0, atol=1e-10):
        raise ValueError('Original cell centres differ')
    if not all(np.isfinite(data[key]).all() for key in ['Z', 'rho', 'volume_m3']):
        raise ValueError('Nonfinite ignition audit values')
    if not (data['rho'] > 0).all() or not (data['volume_m3'] > 0).all():
        raise ValueError('Nonpositive density or cell volume')
    mask = ((data['x_mm'] >= origin*1000) & (data['x_mm'] <= (origin+length)*1000)
            & (data['Z'] >= lower) & (data['Z'] <= upper))
    report = {'readOnly': not args.apply, 'job': receipt['sourceJob'], 'time_s': receipt['time_s'],
              'collectionSha256': sha(args.collection), 'auditSha256': sha(args.audit),
              'cellsSha256': sha(args.cells), 'protocolSha256': sha(protocol_file),
              'codeSha256': sha(Path(__file__)), 'ignitionTime_s': protocol['sourcePausedUntil'],
              'eligibleCells': int(mask.sum()), 'eligibleVolume_m3': float(data['volume_m3'][mask].sum()),
              'eligibleMass_kg': float(np.dot(data['rho'][mask], data['volume_m3'][mask])),
              'rawAxialRange_mm': [float(data['x_mm'][mask].min()), float(data['x_mm'][mask].max())] if mask.any() else None,
              'scientificAcceptance': False,
              'interpretation': 'Coordinate eligibility only; positive-source selection and flame viability remain separate'}
    if not args.apply:
        print(json.dumps(report))
        return
    args.out.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig, axis = plt.subplots(figsize=(10, 3.7), layout='constrained')
    shifted = [p-np.array([origin*1000, 0]) for p in polygons]
    image = PolyCollection(shifted, array=data['Z'], cmap='viridis', clim=(0, 1),
                           edgecolors='none', antialiased=False, rasterized=True)
    axis.add_collection(image)
    axis.scatter(data['x_mm'][mask]-origin*1000, data['r_mm'][mask], s=11,
                 facecolor='none', edgecolor='white', linewidth=.7,
                 label=f"{int(mask.sum())} cells within ignition coordinates")
    axis.axvline(0, color='black', lw=.7)
    axis.axvline(length*1000, color='black', lw=.7, ls='--')
    axis.set(xlim=(-origin*1000, 15), ylim=(0, 8), aspect='equal',
             xlabel='Distance from injector exit (mm)', ylabel='Radius (mm)',
             title=f"Reviewed G2 cold flow at {receipt['time_s']*1000:g} ms")
    axis.legend(loc='upper left', fontsize=9)
    fig.colorbar(image, ax=axis, label='Transported mixture fraction Z')
    report['artifacts'] = {}
    for suffix in ['png', 'svg']:
        file = args.out/f'mixing-region.{suffix}'
        fig.savefig(file, dpi=180)
        report['artifacts'][file.name] = sha(file)
    plt.close(fig)
    (args.out/'evidence.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
