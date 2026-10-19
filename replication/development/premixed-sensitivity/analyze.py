"""Compare matched physical windows without substituting source definitions."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from gate import LEVELS, STAGES, evaluate, load


def select(rows, stage, side, level, start, end):
    result = sorted((r for r in rows if r['stage'] == stage and r['side'] == side
                     and abs(float(r['OH_level'])-level) < 1e-15
                     and start-1e-12 <= float(r['time_s']) <= end+1e-12),
                    key=lambda r: float(r['time_s']))
    if len(result) < 3 or any(r['status'] != 'valid' for r in result):
        raise ValueError('Insufficient valid matched history')
    return {k: np.array([float(r[k]) for r in result]) for k in
            ['time_s', 'x_m', 'U_local', 'rho_local', 'rho_unburned', 'speed_m_s']}


def tracking(data, side):
    t = data['time_s']
    slope = float(np.polyfit(t-t.mean(), data['x_m'], 1)[0])
    sign = -1 if side == 'left' else 1
    weighted = sign*(slope-data['U_local'])*data['rho_local']/data['rho_unburned']
    return {'laboratory_outward_cm_s': sign*slope*100,
            'local_density_weighted_cm_s': float(np.mean(weighted))*100,
            'fit_window_s': [float(t[0]), float(t[-1])]}


def analyze(inputs, output, reference=None):
    datasets = {key: load(path) for key, path in inputs.items()}
    start = max(min(float(r['time_s']) for r in rows) for rows in datasets.values())
    end = min(max(float(r['time_s']) for r in rows) for rows in datasets.values())
    if end-start < 7e-6:
        raise ValueError('Need at least 7 us: 2 us settling and 5 us comparison')
    if reference:
        inputs = dict(inputs, uninterrupted=reference)
        datasets['uninterrupted'] = load(reference)
    output.mkdir(parents=True, exist_ok=False)
    summary = {'window_s': [start, end], 'comparison_window_s': [end-5e-6, end],
               'cases': {}, 'inputs': {}, 'temporal_comparisons': {}}
    plt.rcParams.update({'font.family': 'serif', 'font.size': 9,
                         'axes.linewidth': .7, 'lines.linewidth': 1.1})
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for key, rows in datasets.items():
        gate = evaluate(rows, end=end)
        metrics = []
        for side in ['left', 'right']:
            for level in LEVELS:
                data = select(rows, STAGES[1], side, level, end-5e-6, end)
                metrics.append(dict(side=side, level=level, **tracking(data, side)))
        summary['cases'][key] = {'gate': gate, 'tracking': metrics}
        summary['inputs'][key] = {'path': str(inputs[key]),
                                 'sha256': hashlib.sha256(inputs[key].read_bytes()).hexdigest()}
        for ax, stage in zip(axes[0], STAGES):
            data = select(rows, stage, 'left', 2e-5, start, end)
            ax.plot(data['time_s']*1e6, data['speed_m_s']*100, label=key)
        values = [gate['median_speeds_cm_s'][f'left|{STAGES[1]}|{level}'] for level in LEVELS]
        axes[1, 0].plot(np.array(LEVELS)*1e6, values, 'o-', label=key)
        tracked = [r['local_density_weighted_cm_s'] for r in metrics if r['side'] == 'left']
        axes[1, 1].plot(np.array(LEVELS)*1e6, tracked, 'o-', label=key)
    pairs = [('dt100', 'dt50'), ('dt50', 'dt25'), ('dt100', 'uninterrupted')]
    for a, b in pairs:
        if a not in summary['cases'] or b not in summary['cases']:
            continue
        ca, cb = summary['cases'][a], summary['cases'][b]
        ma, mb = ca['gate']['median_speeds_cm_s'], cb['gate']['median_speeds_cm_s']
        stage_difference = {k: ma[k]-mb[k] for k in ma}
        track_difference = {f"{x['side']}|{x['level']}": x['local_density_weighted_cm_s']-y['local_density_weighted_cm_s']
                            for x, y in zip(ca['tracking'], cb['tracking'])}
        summary['temporal_comparisons'][a+' minus '+b] = {
            'median_difference_cm_s': stage_difference, 'tracking_difference_cm_s': track_difference,
            'within_0_5_cm_s': max(abs(v) for v in [*stage_difference.values(), *track_difference.values()]) <= .5}
    for ax, title in zip(axes[0], ['Source used in OH solve', 'Instantaneous Eq.(40)']):
        ax.set(xlabel='Physical time (µs)', ylabel='Speed at OH=2e−5 (cm/s)', title=title)
    axes[1, 0].set(xlabel='OH mass fraction × 10⁶', ylabel='Median Eq.(40) (cm/s)',
                   title='Last 5 µs: instantaneous marker sensitivity')
    axes[1, 1].set(xlabel='OH mass fraction × 10⁶', ylabel='Tracked weighted speed (cm/s)',
                   title='Last 5 µs: local velocity and density correction')
    for ax in axes.flat:
        ax.grid(alpha=.15)
        ax.legend(fontsize=8)
    fig.suptitle('Products flame: controlled time-step comparison (left front)')
    fig.tight_layout()
    for ext in ['png', 'svg']:
        fig.savefig(output/('time-step-comparison.'+ext), dpi=200)
    plt.close(fig)
    (output/'analysis.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({'window_s': [start, end], 'comparisons': summary['temporal_comparisons']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('cases', nargs='+', help='KEY=CSV')
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    mapping = dict(entry.split('=', 1) for entry in args.cases)
    analyze({k: Path(v) for k, v in mapping.items()}, args.output, args.reference)
