"""Compare retained Reynolds window statistics with declared Schmitt G2 references."""
import argparse
import html
import json
import math
import os
from pathlib import Path
import shutil
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'g2-review'))
from inputs import read_csv, sha256
sys.path.insert(0, str(HERE.parent / 'g2-window-average'))
from inlet_scale import inlet_scale


def checked_assets(root, receipt, key, hashes):
    for name, expected in receipt[key].items():
        if Path(name).name != name:
            raise ValueError('Asset must be a basename: ' + name)
        path = root / name
        if sha256(path) != expected:
            raise ValueError('Changed retained asset: ' + str(path))
        hashes[str(path.resolve())] = expected


def crossing(x, values):
    """First bracket after observed values >=0.1; do not invent an upstream root."""
    for i in range(1, len(x)):
        if values[i-1] >= .1 and values[i] < .1:
            return [float(x[i-1]), float(x[i])]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['reference', 'statistics', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--x-origin-m', type=float, required=True)
    parser.add_argument('--origin-note', required=True)
    parser.add_argument('--inlet-audit-case', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not math.isfinite(args.x_origin_m) or not args.origin_note.strip():
        raise ValueError('Require finite origin and its explicit evidence note')
    reference_path, manifest_path = args.reference / 'receipt.json', args.statistics / 'manifest.json'
    reference = json.loads(reference_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    if reference.get('schema') != 'schmitt-fig21-reference/v1' or reference.get('mode') != 'applied':
        raise ValueError('Require applied Schmitt reference extraction')
    if manifest.get('schema') != 'g2-saved-window-statistics/v1' or manifest.get('mode') != 'applied':
        raise ValueError('Require applied saved-sample statistics')
    hashes = {str(p.resolve()): sha256(p) for p in [reference_path, manifest_path]}
    checked_assets(args.reference, reference, 'outputHashes', hashes)
    checked_assets(args.statistics, manifest, 'outputHashes', hashes)
    groups = [g for g in manifest['groups'] if g['name'] == 'nearAxis' and g.get('output')]
    if len(groups) != 1:
        raise ValueError('Require exactly one available near-axis statistics group')
    group = groups[0]
    values = read_csv(args.statistics / group['output'])
    if not {'x', 'O2Mean', 'O2RMS'} <= values.keys() or not np.all(np.diff(values['x']) > 0):
        raise ValueError('Require ordered actual Reynolds O2 mean/RMS and axial coordinate')
    velocity_present = {'U_0Mean', 'U_0RMS'} <= values.keys()
    scale = inlet_scale(args.inlet_audit_case, manifest)
    hashes.update(scale['inputHashes'])
    curves = {name: np.genfromtxt(args.reference / (name + '.csv'), delimiter=',', names=True)
              for name in ['velocity_mean', 'oxygen_mean']}
    for name, rows in curves.items():
        if not len(rows) or not all(np.isfinite(rows[key]).all() for key in rows.dtype.names):
            raise ValueError('Invalid reference values: ' + name)
    oxygen = curves['oxygen_mean']
    x = values['x'] - args.x_origin_m
    observations = manifest['caseInput']['observations']
    streams = manifest['caseInput']['streams']
    conditions = {'paper': {'pressure_Pa': 5600000, 'oxygen_K': 83, 'methane_K': 300,
                            'sample': 'centerline', 'weighting': 'Reynolds', 'averaging_s': .05,
                            'geometry': '50 x 50 x 400 mm three-dimensional chamber'},
                  'ours': {'pressure': manifest['caseInput'].get('pressure'),
                           'oxygen_K': streams['loxinlet']['temperature'],
                           'methane_K': streams['ch4inlet']['temperature'],
                           'near_axis_radius_m': observations['nearAxisRadius_m'],
                           'origin_m': args.x_origin_m, 'origin_note': args.origin_note}}
    result = {'schema': 'schmitt-fig21-comparison/v1', 'mode': 'applied' if args.apply else 'read-only-plan',
              'inputHashes': hashes, 'runIdentity': manifest['runIdentity'],
              'requestedWindow_s': manifest['requestedWindow_s'], 'quadrature': group['quadrature'],
              'conditions': conditions, 'velocityAvailable': velocity_present,
              'velocityNormalization': scale, 'paperRMSAvailable': False,
              'paperOxygenThresholdBracket_x_over_d': crossing(oxygen['x_over_d'], oxygen['value']),
              'ourNearAxisThresholdBracket_m': crossing(x, values['O2Mean']),
              'metricInterpretation': 'Crossing brackets are diagnostics; no interpolation, error score, or validated flame length',
              'scientificAcceptance': False, 'statisticalConvergenceEstablished': False}
    if not args.apply:
        print(json.dumps(result, indent=2)); return
    if any(sha256(path) != expected for path, expected in hashes.items()):
        raise ValueError('Inputs changed before rendering')
    args.out.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR', str((args.out / 'matplotlib-cache').resolve()))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    shutil.copyfile(args.reference / 'original-figure21.jpg', args.out / 'original-figure21.jpg')
    panels = []
    for name, field, unit in [('velocity', 'U_0', 'Axial velocity (m/s)'), ('oxygen', 'O2', 'Oxygen mass fraction')]:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout='constrained')
        if name == 'velocity' and not velocity_present:
            axes[0].text(.5, .5, 'No actual U_0 samples retained\nVelocity remains unavailable',
                         ha='center', va='center', transform=axes[0].transAxes)
            axes[0].set_axis_off()
        else:
            axes[0].plot(x * 1000, values[field + 'Mean'], color='#553488', label='Our Reynolds mean')
            axes[0].plot(x * 1000, values[field + 'RMS'], color='#553488', ls='--', label='Our Reynolds RMS')
            axes[0].legend(fontsize=9)
        axes[0].set(xlabel='Axial distance from declared exit (mm)', ylabel=unit,
                    title='Our provisional saved-sample window')
        paper = curves[name + '_mean']
        axes[1].plot(paper['x_over_d'], paper['value'], color='#2659a5', label='Paper G2 mean (digitized)')
        stride = 15
        axes[1].errorbar(paper['x_over_d'][::stride], paper['value'][::stride],
                         xerr=np.vstack((paper['x_over_d'] - paper['x_lower'], paper['x_upper'] - paper['x_over_d']))[:, ::stride],
                         yerr=np.vstack((paper['value'] - paper['value_lower'], paper['value_upper'] - paper['value']))[:, ::stride],
                         fmt='none', ecolor='#8896a8', lw=.6, alpha=.6, label='Pixel-reading bounds')
        axes[1].set(xlabel='x/d (paper)', ylabel='Mean ux/u0 (paper)' if name == 'velocity' else unit,
                    title='Paper Reynolds mean; 50 ms averaging')
        axes[1].legend(fontsize=9)
        for axis in axes:
            axis.grid(alpha=.18)
        fig.suptitle(f'Schmitt Figure 21: {name} | separate physical and normalized axes')
        for ext in ['png', 'svg']:
            fig.savefig(args.out / f'schmitt-{name}.{ext}', dpi=170)
        plt.close(fig); panels.append('schmitt-' + name)
    if scale['status'] == 'available-initialized-state-inference':
        for name, field, unit in [('oxygen', 'O2', 'Oxygen mass fraction'), ('velocity', 'U_0', 'Mean Ux / initialized O2 bulk speed')]:
            if name == 'velocity' and not velocity_present:
                continue
            fig, ax = plt.subplots(figsize=(8, 5), layout='constrained')
            denominator = scale['velocity_m_s'] if name == 'velocity' else 1
            ax.plot(x / scale['diameter_m'], values[field + 'Mean'] / denominator,
                    color='#553488', label='Our provisional Reynolds mean')
            paper = curves[name + '_mean']
            ax.plot(paper['x_over_d'], paper['value'], color='#2659a5', label='Paper G2 mean (digitized)')
            ax.set(xlabel='x/d: independently declared diameters', ylabel=unit,
                   title='Inlet-scale diagnostic; unmatched conditions and statistics')
            ax.grid(alpha=.18); ax.legend(fontsize=9)
            fig.text(.5, .005, 'Paper u0 = O2 bulk speed is an inference, not an author-supplied value.', ha='center', fontsize=8)
            for ext in ['png', 'svg']:
                fig.savefig(args.out / f'schmitt-{name}-inferred-scale.{ext}', dpi=170)
            plt.close(fig); panels.append('schmitt-' + name + '-inferred-scale')
    q = group['quadrature']
    coverage = f"{q['contributingSampleCount']} snapshots; {q['duration_s']*1e6:.6g} microseconds used; {q['coverageFraction']*100:.4g}% requested coverage"
    esc = html.escape
    page = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Schmitt G2 comparison</title><style>body{font:17px/1.6 system-ui,sans-serif;color:#26312c;max-width:1250px;margin:36px auto;padding:0 20px}img{width:100%}.note{background:#fff0df;padding:18px}pre{white-space:pre-wrap;font-size:13px}a{color:#00687b}</style>'
    page += '<h1>Schmitt Figure 21: G2 development comparison</h1><p class="note">Our saved-sample startup statistics are not the paper 50 ms Reynolds statistics. Dimensional CFD and paper-normalized coordinates remain separate unless explicitly audited inlet scales are supplied. No numerical agreement score or scientific acceptance.</p>'
    page += '<p>' + esc(coverage) + '</p><p>Paper O2/CH4: 83/300 K, 56 bar, exact centerline. Our inlet temperatures: ' + esc(f"{conditions['ours']['oxygen_K']}/{conditions['ours']['methane_K']} K; sampled radius {observations['nearAxisRadius_m']*1000:g} mm.") + '</p>'
    page += '<nav>' + ' · '.join(f'<a href="#{p}">{p}</a>' for p in panels) + ' · <a href="#reference">Original paper</a></nav>'
    for panel in panels:
        page += f'<section id="{panel}"><h2>{esc(panel)}</h2><img src="{panel}.png"><a href="#reference">Original figure and caption</a></section>'
    page += f'<section id="reference"><h2>Original Figure 21</h2><img src="original-figure21.jpg"><p>{esc(reference["paper"]["caption"])}</p><p><a href="{reference["paper"]["url"]}">Schmitt (2020)</a>. Oxygen RMS remains undigitized because its dashed blue stroke overlaps the steep mean. Reading bounds are pixel uncertainty, not experimental confidence intervals. No paper u0 or numerical diameter was inferred.</p>'
    page += ' · '.join(f'<a href="#{p}">Return: {p}</a>' for p in panels) + '</section><h2>Provenance and qualifications</h2><pre>'
    page += esc(json.dumps({k: result[k] for k in ['quadrature', 'conditions', 'velocityNormalization', 'metricInterpretation']}, indent=2)) + '</pre><a href="receipt.json">Full evidence receipt</a>'
    (args.out / 'index.html').write_text(page, encoding='utf-8')
    dependencies = [Path(__file__), HERE.parent / 'g2-review/inputs.py', HERE.parent / 'g2-window-average/inlet_scale.py']
    result['sourceHashes'] = {str(p.relative_to(HERE.parent)): sha256(p) for p in dependencies}
    result['panels'] = panels
    result['outputHashes'] = {p.name: sha256(p) for p in args.out.iterdir() if p.is_file()}
    (args.out / 'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'out': str(args.out), 'velocityAvailable': velocity_present, 'panels': panels, 'scientificAcceptance': False}))


if __name__ == '__main__':
    main()
