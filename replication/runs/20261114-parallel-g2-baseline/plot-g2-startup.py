"""Show actual G2 startup fields and paper means without inventing normalization."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'validation/g2-review'))
from inputs import load_case


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('case', 'run-record', 'reference', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--time', type=float, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    run = json.loads(args.run_record.read_text())
    data = load_case(args.case, [args.time])
    matches = [r for r in data['records'] if r['name'] == 'nearAxis' and r['kind'] == 'instantaneous']
    if len(matches) != 1 or run.get('CFDStartTime_s') != 0 or not run.get('jobId'):
        raise ValueError('Require one actual near-axis snapshot and identified clean-start run')
    fields = matches[0]['fields']
    if not {'x', 'U_0', 'O2'} <= fields.keys():
        raise ValueError('Snapshot must contain actual x, axial U_0 and O2')
    ref = json.loads((args.reference / 'receipt.json').read_text())
    if ref.get('schema') != 'schmitt-fig21-reference/v1':
        raise ValueError('Require qualified Schmitt Fig.21 extraction')
    hashes = {**data['input_hashes'], str(args.run_record): sha(args.run_record),
              str(args.reference / 'receipt.json'): sha(args.reference / 'receipt.json'),
              str(Path(__file__)): sha(__file__)}
    for name in ('velocity_mean.csv', 'oxygen_mean.csv'):
        file = args.reference / name
        if sha(file) != ref['outputHashes'][name]:
            raise ValueError('Reference changed: ' + name)
        hashes[str(file)] = sha(file)
    receipt = {'schema': 'g2-startup-comparison/v1', 'inputHashes': hashes,
               'jobId': run['jobId'], 'time_s': args.time,
               'CFDStartTime_s': 0, 'paperVelocityNormalizationAssumed': False,
               'paperDiameterAssumed': False, 'scientificAcceptance': False}
    if not args.apply:
        print(json.dumps({'readOnly': True, **receipt}, indent=2))
        return
    args.out.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'legend.fontsize': 9})
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))
    fig.subplots_adjust(left=.08, right=.98, top=.88, bottom=.18, hspace=.48, wspace=.30)
    for row, (quantity, label, reference) in enumerate([
        ('U_0', 'Axial velocity (m/s)', 'velocity_mean.csv'),
        ('O2', 'Oxygen mass fraction', 'oxygen_mean.csv')
    ]):
        axes[row, 0].plot(fields['x'], fields[quantity], ls='none', marker='o', ms=3,
                          color='#66459b', label=f'Our instant: {args.time*1e6:g} us')
        paper = np.genfromtxt(args.reference/reference, delimiter=',', names=True)
        axes[row, 1].plot(paper['x_over_d'], paper['value'], color='#2866a4',
                          lw=1.6, label='Paper G2: time mean')
        axes[row, 0].set(xlabel='Axial position (m)', ylabel=label)
        axes[row, 1].set(xlabel='Paper x/d', ylabel='Paper axial velocity / U0' if row == 0 else label)
        for ax in axes[row]:
            ax.grid(alpha=.15)
            ax.legend(loc='best')
    axes[0, 0].set_title('Computed dimensional startup')
    axes[0, 1].set_title('Schmitt Fig.21: retained paper means')
    fig.suptitle('G2 near-axis startup diagnostics', fontsize=14)
    fig.text(.08, .085, 'Separate units: the supplied paper does not unambiguously specify numerical U0 here.', fontsize=10)
    fig.text(.08, .045, 'No inferred normalization, developed mean, oxygen RMS or scientific acceptance.', fontsize=10)
    for ext in ('png', 'svg'):
        fig.savefig(args.out/('schmitt-g2-startup.'+ext), dpi=180)
    plt.close(fig)
    receipt['outputHashes'] = {f.name: sha(f) for f in args.out.iterdir()}
    (args.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({'out': str(args.out), 'time_s': args.time, 'scientificAcceptance': False}))


if __name__ == '__main__':
    main()
