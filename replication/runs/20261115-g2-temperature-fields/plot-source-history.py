"""Compare completed-step extrema and source-stage totals from one frozen log."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['history', 'stages', 'out']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    history = json.loads(args.history.read_text())
    stages = json.loads(args.stages.read_text())
    if history.get('schema') != 'g2-completed-step-history/v1' or stages.get('schema') != 'g2-completed-source-stage-history/v1':
        raise ValueError('Completed extrema and source-stage receipts required')
    for key in ['job', 'nativeLogSha256', 'CFDStart']:
        if history[key] != stages[key]:
            raise ValueError('Different log or run identity: '+key)
    if history['CFDStart'] != 0 or not re.fullmatch('[0-9a-f]{64}', history['nativeLogSha256']):
        raise ValueError('Original-zero, immutable native log required')
    a = np.array([[r[k] for k in ['time_s', 'Tmax_K', 'cmax']] for r in history['rows']])
    b = np.array([[r[k] for k in ['time_s', 'firstHalfChangeKg', 'lastSecondHalfChangeKg']] for r in stages['rows']])
    if a.shape != b.shape or len(a) < 2 or not np.array_equal(a[:, 0], b[:, 0]):
        raise ValueError('Completed-step times differ')
    if not np.isfinite(a).all() or not np.isfinite(b).all() or not (np.diff(a[:, 0]) > 0).all():
        raise ValueError('Finite increasing completed steps required')
    active = []
    for row in stages['rows']:
        first, second = row['firstHalfCount'], row['secondHalfCount']
        if first not in [0, 1] or (first == 1 and second < 1) or (first == 0 and second != 0):
            raise ValueError('Invalid stage ownership or missing reactive stage')
        active.append(first == 1)
    active = np.array(active)
    if not active.any():
        raise ValueError('No reactive source stages; inspect producer log ordering')
    report = {'readOnly': not args.apply, 'job': history['job'],
              'historySha256': sha(args.history), 'stagesSha256': sha(args.stages),
              'nativeLogSha256': history['nativeLogSha256'], 'codeSha256': sha(Path(__file__)),
              'completedSteps': len(a), 'reactiveSteps': int(active.sum()),
              'negativeFirstStageTotals': int((b[active, 1] < 0).sum()),
              'negativeFinalSecondStageTotals': int((b[active, 2] < 0).sum()),
              'scientificAcceptance': False,
              'interpretation': 'Global stage increments per evaluation, not rates, local source signs or a closed progress budget'}
    if not args.apply:
        print(json.dumps(report))
        return
    args.out.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.6), sharex=True, layout='constrained')
    axes[0].plot(a[:, 0]*1e6, a[:, 1], 'o', ms=2.5, color='#7451b8', label='Global maximum T')
    axes[1].plot(a[:, 0]*1e6, a[:, 2], 's', ms=2.5, color='#21867a', label='Global maximum C')
    for col, marker, label in [(1, 'o', 'First source half-step'), (2, 's', 'Final second half-step')]:
        axes[2].plot(b[active, 0]*1e6, b[active, col], marker, ms=2.4, label=label)
    axes[0].set(ylabel='Temperature (K)', ylim=(0, max(3600, a[:, 1].max()*1.05)))
    axes[1].set(ylabel='Raw C (kg/kg)', ylim=(0, 1))
    axes[2].set(ylabel='Stage increment (kg)', xlabel='Physical time (µs)')
    if (b[active, 1:] > 0).all():
        axes[2].set_yscale('log')
    else:
        axes[2].set_yscale('symlog', linthresh=1e-17)
    for axis in axes:
        axis.axvline(a[active, 0][0]*1e6, color='#555555', ls='--', lw=.9)
        axis.legend(frameon=False, loc='upper right')
        axis.grid(alpha=.2)
    fig.suptitle(f"G2 ignition and source stages · job {history['job']}\nCompleted steps; repeated PIMPLE evaluations are not summed", fontsize=13)
    report['artifacts'] = {}
    for suffix in ['png', 'svg']:
        file = args.out/f'source-history.{suffix}'
        fig.savefig(file, dpi=180)
        report['artifacts'][file.name] = sha(file)
    plt.close(fig)
    (args.out/'evidence.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
