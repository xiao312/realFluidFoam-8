"""Plot all equivalence-ratio tracking cases from one frozen snapshot."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from plot_history import read_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.snapshot/'snapshot.json').read_text())
    states = {line.split('|')[0]: line.split('|')[1]
              for line in manifest['sacct'].splitlines() if '|' in line}
    plt.rcParams.update({'font.family': 'serif', 'font.size': 9, 'pdf.fonttype': 42})
    fig, axes = plt.subplots(3, 4, figsize=(12, 8), sharex=True, sharey=True)
    all_rows, audits, all_values = [], [], []
    for ax, item in zip(axes.flat, manifest['jobs']):
        folder = args.snapshot/item['job']
        for name, expected in item['files'].items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest() != expected:
                raise ValueError(f'Hash mismatch: {folder/name}')
        config = json.loads((folder/'tracking-inputs.json').read_text())
        case = dict(key=item['key'], label=item['key'], job=item['job'],
                    csv=item['job']+'/front-tracking.csv', source=item['source'],
                    state=states[item['job']], phi=config['phi'])
        if 'expected_start_time_s' in item:
            case['expected_start_time_s']=item['expected_start_time_s']
        rows, audit = read_case(case, args.snapshot)
        audit['reference_cm_s'] = config['temperature_anchor']['speed_cm_s']
        audit['temperature_anchor_K'] = config['temperature_anchor']['temperature_anchor_K']
        audits.append(audit); all_rows.extend(rows)
        for marker, color, style in [('T', '#0072B2', '-'), ('OH', '#D55E00', '--')]:
            selected = [r for r in rows if r['marker'] == marker]
            x = [r['time_us'] for r in selected]
            y = [r['mean_cm_s'] for r in selected]
            all_values.extend(v for v in y if np.isfinite(v))
            ax.plot(x, y, color=color, ls=style, lw=1.1, label=marker+' front')
            ax.fill_between(x, [r['lower_cm_s'] for r in selected],
                            [r['upper_cm_s'] for r in selected], color=color, alpha=.13)
        ax.axhline(audit['reference_cm_s'], color='.2', ls=':', lw=1, label='Cantera FreeFlame')
        ax.set_title(f"$\\phi={config['phi']:.2f}$ | {case['state'].lower()}\nJob {item['job']}", fontsize=9)
        ax.set_xlabel('Physical time (μs)', fontsize=9)
        ax.set_ylabel('Speed (cm/s)', fontsize=9)
        ax.tick_params(labelsize=8, direction='in', top=True, right=True, labelbottom=True)
        ax.grid(axis='y', color='.9', lw=.5)
        if not any(np.isfinite(r['mean_cm_s']) for r in rows):
            ax.text(.05,.85,'No complete tracking window',transform=ax.transAxes,fontsize=8)
    axes.flat[-1].axis('off')
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles, labels, loc='upper left', frameon=False, fontsize=9)
    axes.flat[-1].text(.02,.10,'5 μs fit; mean of both fronts\nShading: left–right range\nDensity-normalized speed\nTransient; no steady acceptance',
                       transform=axes.flat[-1].transAxes, fontsize=8, linespacing=1.5)
    axes.flat[0].set_xlim(0, max(205,max(row['time_us'] for row in all_rows)*1.025))
    # Shared full range: do not silently discard ignition transients.
    if all_values:
        lower, upper = min(0, min(all_values)), max(10, max(all_values))
        axes.flat[0].set_ylim(lower-.03*(upper-lower), upper+.03*(upper-lower))
    fig.suptitle('Native ideal-gas flame-speed histories: 100 atm, 298 K\nSnapshot '+manifest['timestamp_local']+' CST', fontsize=12)
    fig.tight_layout(rect=(0,0,1,.94))
    args.output.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output/'ideal-openfoam-histories.png', dpi=220)
    fig.savefig(args.output/'ideal-openfoam-histories.pdf')
    with (args.output/'sweep-history.csv').open('w', newline='', encoding='utf8') as stream:
        writer=csv.DictWriter(stream, fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(all_rows)
    (args.output/'sweep-audit.json').write_text(json.dumps(dict(timestamp_local=manifest['timestamp_local'],
        cases=audits, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
    print(json.dumps([dict(phi=c['phi'],state=c['state'],time_us=c['latest_time_us']) for c in audits]))


if __name__ == '__main__':
    main()
