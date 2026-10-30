"""Compare current patched paper-condition flamelets with retained convergence evidence."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_cases(branch, expected_source):
    summary = json.loads((branch / 'branch-summary.json').read_text())
    records, states = [], {}
    for item in summary['cases']:
        identifier = item['case']['id']
        if not re.fullmatch(r'[a-z0-9-]+', identifier):
            raise ValueError('Unsafe case identifier')
        path = branch / identifier / 'receipt.json'
        if digest(path) != item['receipt_sha256']:
            raise ValueError(f'Case receipt hash mismatch: {identifier}')
        receipt = json.loads(path.read_text())
        if receipt['source_commit'] != expected_source:
            raise ValueError(f'Unexpected simulation source in {identifier}')
        runtime = receipt['spitfire_runtime']
        if not runtime.get('source_patch', {}).get('applied') or not runtime.get('cold_source_patch', {}).get('applied'):
            raise ValueError(f'Current comparison requires both declared runtime patches: {identifier}')
        row = {'id': identifier, 'chi_st_s_inverse': item['case']['chi_st_s_inverse'],
               'source_commit': receipt['source_commit'], 'receipt_sha256': digest(path),
               'process_exit': item['exit_code'], 'status': receipt['status'],
               'hard_wall_limited': item['hard_wall_limited'], 'steady_numerically_converged': False,
               'initialization': receipt.get('initialization_description'),
               'flamelet_seed': receipt.get('flamelet_seed'), 'runtime': runtime,
               'profile_available': False}
        profile = path.parent / 'steady.npz'
        if profile.is_file():
            if digest(profile) != receipt.get('artifacts', {}).get('steady.npz'):
                raise ValueError(f'Profile identity missing or mismatched: {identifier}')
            with np.load(profile) as raw:
                state = {key: raw[key].copy() for key in raw.files}
            if not all(np.isfinite(state[key]).all() for key in ('Z', 'T_K', 'Y')):
                raise ValueError(f'Nonfinite primary profile: {identifier}')
            measured = receipt['final_state_diagnostics']
            residual = measured['scaled_rhs_max']
            qualified = (receipt['steady_numerically_converged'] and residual is not None and residual <= 1e-6
                         and item['exit_code'] == 0 and not item['hard_wall_limited'])
            row.update(profile_available=True, profile_sha256=digest(profile),
                       peak_temperature_k=float(state['T_K'].max()), scaled_rhs_max=residual,
                       temperature_rhs_max_K_s=measured['temperature_rhs_max_K_s'],
                       species_rhs_max_per_s=measured['species_rhs_max_per_s'],
                       steady_numerically_converged=bool(qualified), burning=receipt['burning'],
                       griffon_enthalpy_mixing_max_error_J_kg=receipt.get('griffon_enthalpy_mixing_max_error_J_kg'),
                       local_relaxation_time_s=receipt.get('local_physical_relaxation_time_s'))
            states[identifier] = state
        records.append(row)
    return records, states


def figure3(reference, records, output, source):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.labelsize': 12})
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6), layout='constrained')
    for ax in axes:
        for key, label, color, style in [('gri30', 'Paper: GRI 3.0', '#244e80', '-'),
                                        ('reduced', 'Paper: Frassoldati reduced', '#8a919a', '--')]:
            points = np.asarray(reference['series'][key]['points'])
            ax.semilogx(points[:, 0], points[:, 1], color=color, ls=style, lw=1.7, label=label)
        for converged, marker in [(False, 'x'), (True, 'o')]:
            rows = [r for r in records if r.get('profile_available') and r['steady_numerically_converged'] == converged]
            if rows:
                ax.scatter([r['chi_st_s_inverse'] for r in rows], [r['peak_temperature_k'] for r in rows],
                           marker=marker, s=52, color='#bf4e35', linewidths=1.6, zorder=5, clip_on=False,
                           label='Computed: approximate (RHS criterion failed)' if not converged else 'Computed: RHS criterion passed')
        ax.set(xlabel=r'Stoichiometric scalar dissipation $\chi_{st}$ [s$^{-1}$]',
               ylabel='Peak temperature [K]', xlim=(10, 1e6))
        ax.grid(alpha=.18)
    axes[0].set(ylim=(2500, 4000), title='Published burning-branch range')
    axes[1].set(ylim=(0, 4000), title='All available computed states')
    axes[1].legend(frameon=False, fontsize=8.5, loc='lower left')
    fig.suptitle(f'Müller & Pfitzner (2015), Fig. 3 | current source {source[:7]}', fontsize=13)
    fig.savefig(output / 'figure3.png', dpi=200)
    fig.savefig(output / 'figure3.svg')
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5, 3.2), layout='constrained')
    rows = [r for r in records if r.get('profile_available')]
    ax.loglog([r['chi_st_s_inverse'] for r in rows], [r['scaled_rhs_max'] for r in rows], 'o', color='#bf4e35')
    ax.axhline(1e-6, color='#4e7464', ls='--', label='Unchanged steady criterion: 1e−6')
    ax.set(xlabel=r'$\chi_{st}$ [s$^{-1}$]', ylabel='Maximum scaled RHS [s⁻¹]',
           title='Residual evidence: temperature scaled by 1000 K; species by 1')
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=.18)
    fig.savefig(output / 'residuals.png', dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('branch', 'figure2-reference', 'figure3-reference', 'pdf', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.expected_source):
        raise ValueError('Expected source must be a full commit')
    reference2 = json.loads(args.figure2_reference.read_text())
    reference3 = json.loads(args.figure3_reference.read_text())
    if digest(args.pdf) != reference2['pdf_sha256'] or reference2['pdf_sha256'] != reference3['pdf_sha256']:
        raise ValueError('Paper PDF differs from the two calibrated references')
    records, states = load_cases(args.branch, args.expected_source)
    eligible = [r for r in records if r.get('profile_available') and r['burning']]
    if not eligible:
        raise ValueError('No finite burning profile is available for Figure 2')
    selected = min(eligible, key=lambda r: r['chi_st_s_inverse'])
    points = np.asarray(reference3['series']['gri30']['points'])
    for row in records:
        chi = row['chi_st_s_inverse']
        if row.get('profile_available') and points[0, 0] <= chi <= points[-1, 0]:
            expected = float(np.interp(np.log10(chi), np.log10(points[:, 0]), points[:, 1]))
            row.update(paper_GRI_peak_K=expected, peak_difference_K=row['peak_temperature_k'] - expected,
                       peak_relative_difference=(row['peak_temperature_k'] - expected) / expected)
    result = {'schema': 'muller-current-paper-comparison/v1', 'source_commit': args.expected_source,
              'renderer_files': {name: digest(Path(__file__).with_name(name)) for name in ('paper_compare.py', 'compare.py')},
              'branch_summary_sha256': digest(args.branch / 'branch-summary.json'), 'records': records,
              'figure2_case': selected['id'], 'pdf_sha256': digest(args.pdf),
              'reference_hashes': [digest(args.figure2_reference), digest(args.figure3_reference)],
              'completed_case_count': len(records), 'configured_case_count': 10, 'sweep_complete': len(records) == 10,
              'scientific_acceptance': False, 'extinction_bracket_qualified': False,
              'conditions': '5.61 MPa; CH4 288 K / O2 85 K; GRI 3.0; unity Lewis number; ideal-gas flamelet',
              'limitation': 'Approximate profiles retain measured residual failures. Griffon constant-Cp extension below Tmin; cold thermochemistry unqualified. Figure 2 near-zero chi is not numerically specified by the paper. PR-VTA density remains a separate calculation.'}
    phase_path = args.branch / 'phase-receipt.json'
    if phase_path.is_file():
        phase = json.loads(phase_path.read_text())
        if phase['artifacts']['run/branch-summary.json'] != result['branch_summary_sha256']:
            raise ValueError('Final phase receipt does not bind this branch summary')
        result.update(phase_receipt_sha256=digest(phase_path), job_id=phase['job_id'],
                      configured_case_count=phase['cases_expected'],
                      sweep_complete=phase['all_cases_recorded'] and len(records) == phase['cases_expected'])
    if not args.apply:
        print(json.dumps({'cases': len(records), 'selected': selected['id'], 'scientific_acceptance': False}))
        return
    args.output.mkdir(parents=True, exist_ok=False)
    state = states[selected['id']]
    profile = args.output / 'figure2-profile.csv'
    np.savetxt(profile, np.column_stack((state['Z'], state['T_K'], state['Y'])), delimiter=',',
               header=','.join(['Z', 'T', *['Y_' + str(name) for name in state['species']]]), comments='')
    label = f"current {args.expected_source[:7]}, chi={selected['chi_st_s_inverse']:g}/s, RHS={selected['scaled_rhs_max']:.3g}"
    subprocess.run([sys.executable, str(Path(__file__).with_name('compare.py')), '--reference', str(args.figure2_reference),
                    '--profile', str(profile), '--label', label, '--output', str(args.output / 'figure2')],
                   check=True, stdout=subprocess.PIPE, text=True)
    figure3(reference3, records, args.output, args.expected_source)
    import pymupdf
    doc = pymupdf.open(args.pdf)
    captions = {}
    for number, page, clip in [(2, 4, (60, 88, 535, 480)), (3, 5, (60, 88, 535, 289))]:
        captions[str(number)] = next(block[4].strip().replace('\n', ' ') for block in doc[page].get_text('blocks')
                                    if block[4].startswith(f'Figure {number}:'))
        doc[page].get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), clip=pymupdf.Rect(clip)).save(args.output / f'original-figure{number}.png')
    result['original_captions'] = captions
    table = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in
        [r['id'], f"{r['chi_st_s_inverse']:g}", f"{r.get('peak_temperature_k', float('nan')):.2f}",
         f"{r.get('scaled_rhs_max', float('nan')):.3g}", r['process_exit'],
         'criterion passed' if r['steady_numerically_converged'] else 'approximate / not qualified']) + '</tr>' for r in records)
    panels = ''.join(f'<section id="figure-{n}"><h2>Figure {n}</h2><div class="pair"><figure><img src="{computed}"><figcaption>Current computed comparison; markers identify our data.</figcaption></figure><figure><img src="original-figure{n}.png"><figcaption>{html.escape(captions[str(n)])}</figcaption></figure></div></section>'
                     for n, computed in [(2, 'figure2/comparison.png'), (3, 'figure3.png')])
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Current Müller flamelet comparisons</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1500px;margin:40px auto;padding:0 24px;color:#24313e;background:#faf9f6}}h1,h2{{font-weight:600}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}}figure{{margin:0;background:white;padding:16px;border:1px solid #deded8}}img{{width:100%;height:auto}}figcaption{{font-size:14px;color:#536170}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}.note{{padding:16px;background:#fff1da;border-left:4px solid #b37a27}}code{{font-size:13px}}@media(max-width:900px){{.pair{{grid-template-columns:1fr}}}}</style>
<h1>Müller flamelets: current development results</h1><p>{html.escape(result['conditions'])}</p>
<p>{len(records)}/10 cases recorded. Run source <code>{args.expected_source}</code>. <a href="#figure-2">Figure 2</a> · <a href="#figure-3">Figure 3</a> · <a href="comparison.json">Exact provenance and metrics</a></p>
<p class="note">{html.escape(result['limitation'])} No independent scientific acceptance or validated extinction bracket is claimed.</p>
{panels}<h2>Convergence evidence</h2><img src="residuals.png" style="max-width:850px"><table><tr><th>Case</th><th>χst [1/s]</th><th>Tmax [K]</th><th>Scaled RHS [1/s]</th><th>Process exit</th><th>Classification</th></tr>{table}</table>
<p>Original captions and crops come from the owner-provided Müller &amp; Pfitzner (2015) PDF, pages 5–6. PDF SHA256 <code>{digest(args.pdf)}</code>. Original and reduced-mechanism curves are paper data, not additional computed mechanisms.</p></html>'''
    (args.output / 'index.html').write_text(page, encoding='utf-8')
    result['artifacts'] = {str(p.relative_to(args.output)): digest(p) for p in args.output.rglob('*') if p.is_file()}
    (args.output / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cases': len(records), 'selected': selected['id'], 'output': str(args.output), 'scientific_acceptance': False}))


if __name__ == '__main__':
    main()
