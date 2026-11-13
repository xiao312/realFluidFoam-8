"""Compare all saved radial profiles with fixed paper data and prior saved times."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from plot import read_samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    reference = json.loads(args.reference.read_text())
    times = sorted((float(p.name), p) for p in args.samples.iterdir() if p.is_dir())
    rows, previous = [], {}
    for time, directory in times:
        for height in [.01, .04]:
            file, data = read_samples(directory, height)
            if not all(np.isfinite(v).all() for v in data.values()):
                raise ValueError('Nonfinite saved sample: '+str(file))
            r, temperature, co = data['r_m'], data['T_K'], data['Y_CO']
            row = {'time_s': time, 'height_m': height, 'Tmax_K': float(temperature.max()),
                   'T_peak_radius_mm': float(1000*r[np.argmax(temperature)]),
                   'near_axis_T_K': float(temperature[0]), 'COmax': float(co.max()),
                   'CO_peak_radius_mm': float(1000*r[np.argmax(co)]),
                   'sample_sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
            for quantity, values in [('T_K', temperature), ('Y_CO', co)]:
                curve = next(c for c in reference['curves'] if c['height_m'] == height and c['quantity'] == quantity)
                x = np.array([p['r_m'] for p in curve['points']])
                y = np.array([p['value'] for p in curve['points']])
                covered = (x >= r[0]) & (x <= r[-1])
                delta = np.interp(x[covered], r, values)-y[covered]
                row[quantity+'_RMSE'] = float(np.sqrt(np.mean(delta**2)))
                row[quantity+'_covered_points'] = int(covered.sum())
                row[quantity+'_reference_points'] = len(x)
                if height in previous:
                    old_time, old = previous[height]
                    if not np.array_equal(r, old['r_m']):
                        raise ValueError('Explicit remapping required for different saved grids')
                    row['previous_time_s'] = old_time
                    row['interval_s'] = time-old_time
                    row[quantity+'_max_change'] = float(abs(values-old[quantity]).max())
                    row[quantity+'_rms_change'] = float(np.sqrt(np.mean((values-old[quantity])**2)))
            previous[height] = time, data
            rows.append(row)
    report = {'schema': 'maders-profile-history/v1', 'rows': rows,
              'reference_sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest(),
              'analysis_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': 'Errors use digitized detailed markers at covered coordinates. Near-axis is first sample, not exact r=0. No steady-state or scientific acceptance inferred.'}
    (args.out/'history.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with (args.out/'history.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    plt.rcParams.update({'font.family': 'Arial', 'font.size': 10, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(2, 2, figsize=(9, 6), constrained_layout=True)
    for height, color in [(.01, '#7451b8'), (.04, '#21867a')]:
        selected = [row for row in rows if row['height_m'] == height]
        x = [1000*row['time_s'] for row in selected]
        for ax, key, label in zip(axes.flat, ['T_K_RMSE', 'Y_CO_RMSE', 'near_axis_T_K', 'T_peak_radius_mm'],
                                 ['Temperature RMS error [K]', 'CO mass-fraction RMS error',
                                  'Near-axis temperature [K]', 'Temperature-peak radius [mm]']):
            ax.plot(x, [row[key] for row in selected], '-o', color=color, ms=3, lw=1.1,
                    label=f'H = {1000*height:g} mm')
            ax.set(xlabel='Physical time [ms]', ylabel=label)
            ax.grid(alpha=.2)
            ax.legend(frameon=False)
    fig.savefig(args.out/'history.png', dpi=180)
    fig.savefig(args.out/'history.svg')
    print(json.dumps({'saved_times': len(times), 'latest': rows[-2:]}))


if __name__ == '__main__':
    main()
