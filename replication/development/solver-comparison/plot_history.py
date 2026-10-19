"""Plot frozen tracking histories; never read or modify live simulation cases."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

STYLES = [('#0072B2', '-', 'o'), ('#D55E00', '--', 's'),
          ('#009E73', '-.', '^'), ('#CC79A7', ':', 'D'),
          ('#56B4E9', '--', 'v'), ('#8C564B', '-.', 'P'),
          ('#9467BD', '-', 'X'), ('#595959', ':', '*')]


def read_case(case, base):
    path = base / case['csv']
    groups = defaultdict(dict)
    statuses = Counter()
    latest = 0.
    first = np.inf
    with path.open(encoding='utf8', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'time_s', 'side', 'marker', 'status', 'density_weighted_m_s'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f'{path}: missing tracking columns')
        for row in reader:
            if row.get('primary', '1') != '1' or row['marker'] not in ('T', 'OH'):
                continue
            time = float(row['time_s'])
            if not np.isfinite(time):
                raise ValueError(f'{path}: nonfinite time')
            latest = max(latest, time)
            first = min(first, time)
            statuses[row['status']] += 1
            side = row['side']
            if side not in ('left', 'right'):
                raise ValueError(f'{path}: unexpected side {side}')
            key = (row['marker'], time)
            if side in groups[key]:
                raise ValueError(f'{path}: duplicate primary observation {key}, {side}')
            speed = float(row['density_weighted_m_s']) * 100 if row['status'] == 'valid' else np.nan
            if row['status'] == 'valid' and not np.isfinite(speed):
                raise ValueError(f'{path}: nonfinite valid speed')
            groups[key][side] = speed
    if not np.isfinite(first):
        raise ValueError(f'{path}: no primary tracking rows')
    if 'expected_start_time_s' in case and abs(first-case['expected_start_time_s']) > 1e-12:
        raise ValueError(f'{path}: first time {first} differs from declared start')
    rows = []
    for (marker, time), sides in sorted(groups.items()):
        left, right = sides.get('left', np.nan), sides.get('right', np.nan)
        valid = np.isfinite(left) and np.isfinite(right)
        rows.append(dict(case=case['key'], job=case['job'], marker=marker,
                         time_us=time*1e6, left_cm_s=left, right_cm_s=right,
                         mean_cm_s=(left+right)/2 if valid else np.nan,
                         lower_cm_s=min(left, right) if valid else np.nan,
                         upper_cm_s=max(left, right) if valid else np.nan))
    audit = dict(case, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                 first_time_us=first*1e6, latest_time_us=latest*1e6,
                 status_counts=dict(statuses), markers={})
    for marker in ('T', 'OH'):
        valid = [r for r in rows if r['marker'] == marker and np.isfinite(r['mean_cm_s'])]
        audit['markers'][marker] = dict(valid_points=len(valid))
        if valid:
            audit['markers'][marker].update(first_time_us=valid[0]['time_us'],
                last_time_us=valid[-1]['time_us'], last_mean_cm_s=valid[-1]['mean_cm_s'],
                min_mean_cm_s=min(r['mean_cm_s'] for r in valid),
                max_mean_cm_s=max(r['mean_cm_s'] for r in valid))
    return rows, audit


def figure(config, all_rows, zoom):
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
                         'font.size': 10, 'axes.linewidth': .8, 'pdf.fonttype': 42})
    expanded = len(config['cases']) > 4
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 6.4) if expanded else (10.6, 5.5), sharex=True, sharey=True)
    fig.subplots_adjust(left=.075, right=.98, top=.66 if expanded else .73, bottom=.25, wspace=.10)
    for ax, marker, title in zip(axes, ('T', 'OH'),
                                ('(a) Temperature front: 780.872 K', r'(b) OH front: $Y_{OH}=2\times10^{-5}$')):
        for case, (color, style, symbol) in zip(config['cases'], STYLES):
            rows = [r for r in all_rows if r['case'] == case['key'] and r['marker'] == marker]
            x = np.array([r['time_us'] for r in rows])
            y = np.array([r['mean_cm_s'] for r in rows])
            ax.plot(x, y, color=color, ls=style, lw=1.3, marker=symbol,
                    markersize=3.4, markerfacecolor='white', markevery=max(1, len(x)//12),
                    label=case['label'])
            ax.fill_between(x, [r['lower_cm_s'] for r in rows],
                            [r['upper_cm_s'] for r in rows], color=color, alpha=.14, linewidth=0)
        ax.axhline(config['reference_cm_s'], color='.2', ls=(0, (5, 3)), lw=1.,
                   label=f"Cantera FreeFlame: {config['reference_cm_s']:.3f} cm/s")
        for start in sorted({case['first_time_us'] for case in config['cases']}):
            if start > 1e-6:
                ax.axvline(start, color='.65', ls=':', lw=.8)
        ax.set_title(title, fontsize=11, pad=9)
        ax.set_xlabel(r'Physical time ($\mu$s)')
        ax.tick_params(direction='in', top=True, right=True)
        ax.grid(axis='y', color='.9', lw=.5)
        ax.set_xlim(0, max(200, max(r['time_us'] for r in all_rows)))
        if zoom:
            ax.set_ylim(4, 10)
    axes[0].set_ylabel(r'Density-normalized front speed (cm s$^{-1}$)')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.53, .90),
               ncol=2, frameon=False, fontsize=9.3, handlelength=3.3)
    fig.suptitle(r'Methane/air: $\phi=1.10$, 100 atm, $T_u=298$ K' +
                 (' — detail: 4–10 cm/s' if zoom else ' — full speed range'), y=.98, fontsize=13)
    starts = sorted({round(case['first_time_us'], 3) for case in config['cases']})
    start_note = ('All tracking histories start at 0 μs.' if starts == [0.]
                  else 'Recorded start times (μs): '+', '.join(f'{value:g}' for value in starts)+'.')
    footer = ('5 μs fits; lines = mean of left/right fronts; shading = their range (not uncertainty).\n'
              + start_note + '\n'
              'Transport models differ. These are transient diagnostics, not accepted steady flame speeds.\n'
              f"Snapshot: {config['capture_utc']}" )
    fig.text(.075, .055, footer, va='bottom', fontsize=9, linespacing=1.5)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf8'))
    if not 1 <= len(config['cases']) <= len(STYLES):
        raise ValueError('Supply one to eight named comparison cases')
    if len({c['key'] for c in config['cases']}) != len(config['cases']):
        raise ValueError('Case keys must be unique')
    rows, audits = [], []
    for case in config['cases']:
        values, audit = read_case(case, args.config.parent)
        rows.extend(values); audits.append(audit)
    if not rows:
        raise ValueError('No tracking observations')
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output/'plotted-history.csv').open('w', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    audit = dict(config, cases=audits, definition='outward sign * mean_window[rho_front/rho_fresh * (fitted dx/dt - U_front)]; mean of both fronts',
                 fit_window_s=5e-6, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output/'audit.json').write_text(json.dumps(audit, indent=2)+'\n', encoding='utf8')
    with PdfPages(args.output/'flame-speed-history.pdf') as pdf:
        for zoom, stem in [(False, 'flame-speed-history'), (True, 'flame-speed-history-detail')]:
            fig = figure(dict(config, cases=audits), rows, zoom)
            fig.savefig(args.output/(stem+'.png'), dpi=220)
            pdf.savefig(fig); plt.close(fig)
    print(json.dumps(audits, indent=2))


if __name__ == '__main__':
    main()
