"""Plot hash-bound completed-step extrema without smoothing or CFD mutation."""
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
    parser.add_argument('--history', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    data = json.loads(args.history.read_text())
    if data.get('schema') != 'g2-completed-step-history/v1' or data.get('CFDStart') != 0:
        raise ValueError('Hash-bound original-zero completed-step history required')
    if not re.fullmatch('[0-9a-f]{64}', data.get('nativeLogSha256', '')):
        raise ValueError('Native log identity absent')
    values = np.array([[r[k] for k in ['time_s', 'Tmin_K', 'Tmax_K', 'cmin', 'cmax']] for r in data['rows']])
    if len(values) < 2 or not np.isfinite(values).all() or not (np.diff(values[:, 0]) > 0).all():
        raise ValueError('Finite strictly increasing completed-step data required')
    events = []
    for line in data['rawIgnitionEvents']:
        event = dict(re.findall(r'(\w+)=([^\s]+)', line))
        events.append({'time_s': float(event['t']), 'cells': int(event['cells']), 'raw': line})
    report = {'readOnly': not args.apply, 'job': data['job'], 'rows': len(values),
              'historySha256': sha(args.history), 'nativeLogSha256': data['nativeLogSha256'],
              'plotCodeSha256': sha(Path(__file__)), 'events': events,
              'timeRange_s': [float(values[0, 0]), float(values[-1, 0])],
              'peakGlobalT_K': float(values[:, 2].max()), 'last': data['rows'][-1],
              'scientificAcceptance': False,
              'interpretation': 'Independent global extrema from completed steps; not a cell trajectory or paper mean'}
    if not args.apply:
        print(json.dumps(report))
        return
    args.out.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(2, 1, figsize=(8, 5.6), sharex=True, layout='constrained')
    for axis, column, color, marker, label in [
        (axes[0], 2, '#7451b8', 'o', 'Global maximum T'),
        (axes[1], 4, '#21867a', 's', 'Global maximum raw C')]:
        axis.plot(values[:, 0]*1e6, values[:, column], linestyle='none', marker=marker,
                  color=color, markersize=2.6, label=label)
        for event in events:
            axis.axvline(event['time_s']*1e6, color='#555555', ls='--', lw=.9)
        axis.grid(alpha=.2)
        axis.legend(frameon=False, loc='upper right')
    axes[0].set(ylabel='Temperature (K)', ylim=(0, max(3600, values[:, 2].max()*1.05)))
    axes[1].set(ylabel='Raw C (kg/kg)', xlabel='Physical time (µs)', ylim=(0, max(1, values[:, 4].max()*1.05)))
    fig.suptitle(f"G2 local-Z ignition · job {data['job']}\nCompleted-step extrema; dashed line marks ignition", fontsize=13)
    report['artifacts'] = {}
    for suffix in ['png', 'svg']:
        file = args.out/f'ignition-history.{suffix}'
        fig.savefig(file, dpi=180)
        report['artifacts'][file.name] = sha(file)
    plt.close(fig)
    (args.out/'evidence.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
