"""Plot retained accepted flamelet states without interpolation or curve fitting."""
import hashlib
import json
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, required=True)
parser.add_argument('--out', type=Path)
parser.add_argument('--plan', action='store_true')
args = parser.parse_args()
source = args.input.resolve()
phase = json.loads((source/'phase-receipt.json').read_text())
if phase['schema'] != 'seeded-flamelet-family-phase/v1':
    raise ValueError('Expected the actual seeded-family phase receipt')
if sorted(case['chi_st_s_inverse'] for case in phase['cases']) != [10000, 100000]:
    raise ValueError('This renderer requires the two declared dissipation cases')
if not all(case['exit_code'] == 0 and case['actual_final_time_s'] == .0002
           for case in phase['cases']):
    raise ValueError('This complete-experiment renderer requires both 200 us results')
if args.plan:
    print(json.dumps({'input': str(source), 'job_id': phase['job_id'],
                      'source': phase['source_commit'], 'cases': phase['cases'],
                      'writes': False, 'scientific_acceptance': False}))
    raise SystemExit(0)
if not args.out:
    parser.error('Supply --out NEW_DIRECTORY or use --plan')
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
plt.rcParams.update({'font.size': 12, 'axes.titlesize': 13, 'axes.spines.top': False,
                     'axes.spines.right': False, 'lines.linewidth': 1.8})
fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
records = []
shared_seed = None
for chi, color in [(10000, '#126c91'), (100000, '#c36b19')]:
    path = source/f'chi-{chi}'/'trajectory.npz'
    audit = json.loads((source/f'chi-{chi}-coordinate-audit.json').read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == audit['raw_sha256']
    with np.load(path, allow_pickle=False) as data:
        time = data['time_s']*1e6
        z = data['Z']
        temp = data['T_K']
        assert float(data['pressure_pa']) == 5610000
        assert time[0] == 0 and time[-1] == 200 and z[0] == 0 and z[-1] == 1
        if shared_seed is None:
            shared_seed = (z.copy(), temp[0].copy())
        else:
            assert np.array_equal(z, shared_seed[0]) and np.array_equal(temp[0], shared_seed[1])
        names = list(data['species'])
        carbon = data['Y'][:, :, names.index('CO2')]+data['Y'][:, :, names.index('CO')]
        water = carbon+data['Y'][:, :, names.index('H2O')]
        label = rf'$\chi_{{st}}={chi:g}\;s^{{-1}}$'
        axes[0, 0].plot(time, temp.max(axis=1), color=color, label=label)
        axes[0, 1].plot(z, temp[-1], color=color, label=label)
        if chi == 10000:
            axes[0, 1].plot(z, temp[0], color='#727b88', linestyle='--', label='Shared fresh seed')
        actual_z = []
        for row, target in [(1, .2), (2, .24)]:
            i = int(np.argmin(abs(z-target)))
            actual_z.append(float(z[i]))
            for col, values, title in [(0, carbon, 'CO₂ + CO'), (1, water, 'CO₂ + CO + H₂O')]:
                axes[row, col].plot(time, values[:, i], color=color)
                axes[row, col].set_title(f'{title} at Z = {z[i]:.5f}')
                axes[row, col].set_ylabel('Mass fraction')
        assert audit['physical_source_commit'] == phase['source_commit']
        records.append(dict(chi_st_s_inverse=chi, raw_sha256=digest,
                            frames=len(time), actual_z=actual_z,
                            actual_end_time_s=float(time[-1]/1e6)))
axes[0, 0].set_title('Peak temperature during ignition or extinction')
axes[0, 0].set_ylabel('Temperature (K)')
axes[0, 1].set_title('Profiles at 200 microseconds')
axes[0, 1].set_ylabel('Temperature (K)')
axes[0, 1].set_xlabel('Mixture fraction Z')
axes[0, 1].set_xlim(0, .65)
for row in range(3):
    for col in range(2):
        ax = axes[row, col]
        ax.grid(alpha=.15)
        if (row, col) != (0, 1):
            ax.set_xscale('symlog', linthresh=.001)
            ax.set_xticks([0, .001, .1, 10, 200], ['0', '0.001', '0.1', '10', '200'])
            ax.set_xlim(0, 200)
            ax.set_xlabel('Time (µs; logarithmic after 0.001 µs)')
axes[0, 0].legend(fontsize=11)
axes[0, 1].legend(fontsize=10)
fig.suptitle('Fresh CH₄/O₂ flamelets: ignition depends on scalar dissipation', fontsize=17)
fig.supxlabel(f"Job {phase['job_id']} · 5.61 MPa · O₂ 85 K / CH₄ 288 K · physical accepted states\n"
              'GRI30 / corrected Spitfire · ideal-gas chemistry · no table replacement or scientific acceptance', fontsize=10)
for ext in ['png', 'svg']:
    fig.savefig(out/f'ignition-family.{ext}', dpi=170)
plt.close(fig)
receipt = dict(job_id=phase['job_id'], science_source=phase['source_commit'],
               plot_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               data=records, fitted_curves=False, scientific_acceptance=False)
(out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
print(json.dumps(receipt))
