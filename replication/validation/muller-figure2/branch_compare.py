"""Compare retained steady branch states without changing their convergence verdicts."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', required=True, type=Path)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text())
    summary = json.loads((args.branch / 'branch-summary.json').read_text())
    states, records = [], []
    for item in summary['cases']:
        receipt_path = args.branch / item['receipt_path']
        if digest(receipt_path) != item['receipt_sha256']:
            raise ValueError(f'Receipt hash mismatch: {receipt_path}')
        receipt = json.loads(receipt_path.read_text())
        profile = receipt_path.parent / 'steady.npz'
        if digest(profile) != receipt['artifacts']['steady.npz']:
            raise ValueError(f'Profile hash mismatch: {profile}')
        with np.load(profile) as data:
            state = {key: data[key].copy() for key in data.files}
        if not all(np.isfinite(state[key]).all() for key in ('Z', 'T_K', 'Y')):
            raise ValueError(f'Nonfinite primary profile: {profile}')
        states.append(state)
        records.append({'source_commit': receipt['source_commit'], 'profile_sha256': digest(profile),
            'receipt_sha256': digest(receipt_path), 'chi_st_s_inverse': float(state['chi_st']),
            'peak_temperature_k': float(state['T_K'].max()), 'process_exit': item['process_exit'],
            'steady_numerically_converged': receipt['steady_numerically_converged'],
            'scaled_rhs_max': receipt['scaled_rhs_max'], 'status': receipt['status']})
    result = {'schema': 'muller-branch-comparison/v1', 'reference_sha256': digest(args.reference),
        'records': records, 'scientific_acceptance': False,
        'interpretation': 'Retained numerical states, not accepted steady solutions. Known upstream energy indexing defect remains in this source. No extinction bracket is claimed.'}
    if not args.apply:
        print(json.dumps(result, indent=2))
        return
    args.output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.labelsize': 12})
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6), layout='constrained')
    for ax in axes:
        for name, color in [('gri30', '#244e80'), ('reduced', '#9099a4')]:
            points = np.array(reference['series'][name]['points'])
            ax.semilogx(points[:, 0], points[:, 1], color=color, lw=1.7,
                        ls='-' if name == 'gri30' else '--', label=f'Paper: {name}')
        for converged, marker in [(False, 'x'), (True, 'o')]:
            rows = [row for row in records if row['steady_numerically_converged'] == converged]
            if rows:
                ax.scatter([r['chi_st_s_inverse'] for r in rows], [r['peak_temperature_k'] for r in rows],
                           marker=marker, s=48, color='#c14b31', zorder=5,
                           label='Computed, residual not passed' if not converged else 'Computed, residual passed')
        ax.set(xlabel=r'Stoichiometric scalar dissipation $\chi_{st}$ [s$^{-1}$]',
               ylabel='Peak temperature [K]', xlim=(1, 1e6))
        ax.grid(alpha=.18)
    axes[0].set(ylim=(2500, 4000), title='Burning-branch detail')
    axes[1].set(ylim=(0, 4000), title='All retained states')
    axes[1].legend(frameon=False, fontsize=9, loc='lower left')
    fig.suptitle('Müller & Pfitzner (2015), Fig. 3 — preliminary diagnostic', fontsize=13)
    fig.savefig(args.output / 'comparison.png', dpi=200)
    fig.savefig(args.output / 'comparison.svg')
    plt.close(fig)
    for index, state in enumerate(states):
        columns = ['Z', 'T_K'] + ['Y_' + str(name) for name in state['species']]
        values = np.column_stack((state['Z'], state['T_K'], state['Y']))
        np.savetxt(args.output / f'profile-{index:02d}.csv', values, delimiter=',',
                   header=','.join(columns), comments='')
    (args.output / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
