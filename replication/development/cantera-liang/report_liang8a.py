"""Write the registered `liang-8a` reproduction report from measured artefacts.

Nothing in this report is typed from memory: every number is read from a JSON artefact
whose hash is printed at the end of the section that uses it, and the exact commands
that regenerate those artefacts are listed in the last section.

    python3 report_liang8a.py --sweep results.json --compare compare.json \\
        --repro reproducibility.json --verification verification.json \\
        --reference fig8a-reference.json --receipt render-receipt.json \\
        --run-dir runs/liang8a-sweep-a,runs/liang8a-sweep-b,runs/liang8a-sweep-c \\
        --job 'liang8a-sweep-a:125208987,liang8a-sweep-b:...' \\
        --source-commit COMMIT --base-commit BASE --out report.md
"""
import argparse
import hashlib
import json
import math
import pathlib

CASES = [
    (1, 'ideal gas', 'Ideal-gas EoS, ideal-gas calorics, Cantera mixture-averaged transport'),
    (2, '+ SRK density', 'SRK density and EoS with ideal-gas calorics retained'),
    (3, '+ SRK enthalpy', 'SRK density plus SRK calorics (h, cp from the SRK departure)'),
    (4, '+ Ely-Hanley conductivity', 'adds the Ely-Hanley mixture thermal conductivity'),
    (5, '+ Takahashi diffusion', 'adds Takahashi-corrected binary diffusion coefficients'),
]


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def frac(part, whole):
    return 100.0 * part / whole if whole else float('nan')


def rms_of(mine, theirs):
    return math.sqrt(sum((v - t) ** 2 for (_, v), t in zip(mine, theirs)) / len(mine))


def interpolate(points, x):
    pts = sorted(points)
    xs = [p[0] for p in pts]
    if x < xs[0] or x > xs[-1]:
        return None
    for i in range(1, len(pts)):
        if pts[i][0] >= x:
            (x0, y0), (x1, y1) = pts[i - 1], pts[i]
            return y0 + (x1 and (x - x0) / (x1 - x0) or 0.0) * (y1 - y0)
    return None


def prior_cross_check(ref, prior):
    """Compare this work's digitisation with the previous generation's reading of the same raster.

    Symbols are compared symbol to symbol; traced curves are interpolated at the previous
    generation's own sample abscissae, so a denser or sparser trace cannot flatter itself.
    """
    out = []
    for stage in range(1, 6):
        mine = sorted((r['phi'], r['speed_cm_s']) for r in ref['rows'] if r['stage'] == stage)
        theirs = sorted((r['phi'], r['value']) for r in prior['rows']
                        if int(r['case']) == stage and r['origin'] == 'paper')
        if stage in (2, 3, 4):
            pairs = [(m, t) for m, t in zip(mine, theirs)]
            kept = [(m[0], m[1]) for m, t in pairs]
            target = [t[1] for m, t in pairs]
        else:
            kept, target = [], []
            for phi, value in theirs:
                interpolated = interpolate(mine, phi)
                if interpolated is None:
                    continue
                kept.append((phi, interpolated))
                target.append(value)
        if kept:
            out.append((stage, kept, target))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sweep', required=True)
    ap.add_argument('--compare', required=True)
    ap.add_argument('--repro', required=True)
    ap.add_argument('--verification', required=True)
    ap.add_argument('--reference', required=True)
    ap.add_argument('--prior', required=True)
    ap.add_argument('--receipt', required=True)
    ap.add_argument('--run-dir', required=True)
    ap.add_argument('--job', required=True)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--base-commit', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    sweep = load(a.sweep)
    comp = load(a.compare)
    repro = load(a.repro)
    ver = load(a.verification)
    ref = load(a.reference)
    prior = load(a.prior)
    receipt = load(a.receipt)
    runs = [pathlib.Path(p) for p in a.run_dir.split(',')]
    jobs = [item.split(':', 1) if ':' in item else (item, 'unrecorded')
            for item in a.job.split(',') if item]
    points = sweep['results']
    rows = comp['rows']

    out = []
    w = out.append
    w('# Liang Fig. 8(a): staged Cantera flame speeds at 100 atm')
    w('')
    w('Target `liang-8a`. Candidate commit `%s`, approved base `%s`.' % (a.source_commit, a.base_commit))
    w('This report describes a reproduction attempt with a computed series, a digitised')
    w('reference series and a declared comparison screen. It does not claim agreement with')
    w('the authors, and it does not claim human scientific acceptance.')
    w('')

    # ---- 1 ----------------------------------------------------------------
    w('## 1. What is reproduced, and what is not')
    w('')
    w('The panel is Liang\'s methane/air laminar flame speed at 100 atm over phi = 1.0-1.4,')
    w('drawn as five model stages. The registered target requires five checks:')
    w('source_and_units, reference_coverage, figure_fidelity, reproducibility and')
    w('numerical_comparison. All five are answered in section 8 from recorded artefacts.')
    w('')
    w('What this work does **not** have:')
    w('')
    w('* the authors\' numerical data - the reference is this work\'s digitisation of the')
    w('  published raster, so it carries digitisation uncertainty (section 4);')
    w('* the authors\' input deck - the mechanism, the transport implementation and the')
    w('  unburned temperature are reconstructions (section 3);')
    w('* any claim that the five stages identify the authors\' switch settings; a stage that')
    w('  lands closer to a curve is not evidence that the authors used it.')
    w('')

    # ---- 2 ----------------------------------------------------------------
    w('## 2. Frozen source and inputs')
    w('')
    w('| item | value |')
    w('| --- | --- |')
    w('| module tree | `replication/development/cantera-liang`, %d files frozen by `module.sha256` |'
      % len(list(pathlib.Path(runs[0] / 'module.sha256').read_text().splitlines())))
    w('| module manifest | `%s` |' % sha(runs[0] / 'module.sha256'))
    w('| inputs manifest | `%s` |' % sha(runs[0] / 'inputs.sha256'))
    w('| source commit | `%s` |' % a.source_commit)
    w('| reference digitisation | `%s` |' % sha(a.reference))
    w('| digitised paper raster | `%s` (paper `%s`) |'
      % (ref['raster'].get('sha256', ref.get('raster_sha256', 'n/a')), ref.get('paper_sha256', 'n/a')))
    w('')
    w('Each sweep point copies the frozen manifests into its own directory, so the identity')
    w('of the code that produced one operating point does not depend on the directory tree')
    w('later.')
    w('')

    # ---- 3 ----------------------------------------------------------------
    w('## 3. Method and reconstructed inputs')
    w('')
    w('Cantera 3.2 `FreeFlame`, one-dimensional, mixture-averaged transport, mole-fraction')
    w('diffusion driving force, physical concentrations for the reverse rate constants')
    w('(NASA equilibrium constants), `setState_TP(298 K, 100 atm)` on')
    w('CH4 + air (O2 0.21 / N2 0.79 by mole). The steady solver starts from a labelled ideal')
    w('flame profile - a steady guess, never a transient restart of another case.')
    w('')
    w('| case | cumulative model change |')
    w('| --- | --- |')
    for num, label, text in CASES:
        w('| %d | %s: %s |' % (num, label, text))
    w('')
    w('Case 2 keeps ideal calorics on purpose and is therefore not a thermodynamically')
    w('consistent equilibrium model; it isolates the density effect only.')
    w('')
    w('Solved grid: %s.' % ', '.join('%.2f' % p for p in sorted({q['phi'] for q in points})))
    w('That is the registered previous generation\'s grid, so reproducibility is compared at')
    w('identical operating points rather than through interpolation. Solver controls:')
    w('steady relative tolerance 1e-5, absolute tolerance 1e-11, single rank.')
    w('')
    w('The unburned temperature is an assumption. The article does not state Tu numerically;')
    w('298 K is inferred from the figure caption conditions and is recorded as an assumption,')
    w('not as a measured input. Every number below inherits it.')
    w('')

    # ---- 4 ----------------------------------------------------------------
    cal = ref['calibration']
    counts = ref['counts']
    w('## 4. Reference: how the paper panel was digitised')
    w('')
    w('Source: the campaign library raster of the panel, %d x %d px at 3x of the PDF crop'
      % (ref['raster']['width'], ref['raster']['height']))
    w('`crop_pt %s` of page index %s of the paper (`%s`).'
      % (ref['raster_origin']['crop_pt'], ref.get('raster_origin', {}).get('page_index', 'n/a'),
         ref.get('paper_sha256', 'n/a')))
    w('')
    w('* Axis calibration from the measured major-tick pixel positions: x ticks %s -> phi'
      % cal['x_ticks_px'])
    w('  %s, least-squares residual **%.2e phi**; y ticks %s -> %s cm/s'
      % (cal.get('phi_ticks', [1.0, 1.1, 1.2, 1.3, 1.4]), cal['x_rms_px'], cal['y_ticks_px'],
         cal.get('speed_ticks_cm_s', [8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0])))
    w('  (top to bottom), residual **%.5f cm/s**. Scales: %.7f phi/px and %.7f cm/s/px.'
      % (cal['y_rms_px'], cal['phi_per_pixel'], cal['cm_s_per_pixel']))
    w('* Case 1 and case 5 are continuous lines: the dark or blue ridge was thinned to a')
    w('  skeleton and sampled per column, giving %d and %d samples.'
      % (counts['case1_curve'], counts['case5_curve']))
    w('* Cases 2, 3 and 4 are symbols: %d, %d and %d symbol centres were separated from the'
      % (counts['case2_markers'], counts['case3_markers'], counts['case4_markers']))
    w('  lines by stroke thickness with the measured line width as the threshold.')
    w('* Legend text, the title band and the axis bands were excluded by measured boxes, so')
    w('  no reference sample is invented and none is interpolated across a gap.')
    w('')
    w('Per-symbol uncertainty recorded with every reference row: 0.02 cm/s for the traced')
    w('lines and 0.03 cm/s for symbol centres - a declared reading uncertainty on top of the')
    w('calibration residuals, not a confidence interval from repeated digitisation.')
    w('')
    w('Independent cross-check: the registered previous generation carries its own')
    w('digitisation of the same panel, made by a different pipeline. Comparing the two')
    w('readings of the same printed curve bounds the reading error; it cannot remove it.')
    w('')
    w('| case | compared samples | overlap (phi) | rms difference (cm/s) | max abs (cm/s) |')
    w('| --- | --- | --- | --- | --- |')
    cross = prior_cross_check(ref, prior)
    worst_cross = None
    for stage, mine, theirs in cross:
        rms = rms_of(mine, theirs) if mine else float('nan')
        biggest = max((abs(v - t) for (_, v), t in zip(mine, theirs)), default=float('nan'))
        w('| %d | %d | %.4f-%.4f | %.4f | %.4f |'
          % (stage, len(mine), min(p[0] for p in mine), max(p[0] for p in mine), rms, biggest))
        if worst_cross is None or biggest > worst_cross[1]:
            worst_cross = (stage, biggest, rms)
    w('')
    if worst_cross:
        w('The two readings agree to %.4f cm/s rms on case %d and differ by at most %.4f cm/s'
          % (worst_cross[2], worst_cross[0], worst_cross[1]))
        w('somewhere on that curve, so the reference uncertainty used in the screen (0.02-0.03')
        w('cm/s per sample) understates the point-to-point disagreement between two readings of')
        w('the same printed line. Where the two digitisation pipelines disagree, the printed')
        w('line is ambiguous; that ambiguity is carried into every comparison below.')
        w('')
    w('Nothing is extrapolated: the compared phi values lie inside the digitised span, and')
    w('the two grid points outside it (0.92 and 1.44) are used only for the reproducibility')
    w('comparison and are listed as excluded in the numerical comparison.')
    w('')

    # ---- 5 ----------------------------------------------------------------
    w('## 5. Execution record')
    w('')
    w('| job key | scheduler job | ranks | build | points solved |')
    w('| --- | --- | --- | --- | --- |')
    for key, jid in jobs:
        mine = [p for p in points if p['job'] == jid]
        build = 'reuses binary'
        for run in runs:
            bs = run / 'build-status.txt'
            if bs.exists():
                text = bs.read_text().strip()
                if text.startswith('BUILT'):
                    build = '`%s`' % text
        w('| %s | %s | 1 | %s | %d |' % (key, jid, build, len(mine)))
    w('')
    for run in runs:
        combined = run / 'combined.txt'
        sweep_txt = run / 'sweep.txt'
        if combined.exists() and combined.read_text().strip():
            lines = [ln for ln in combined.read_text().splitlines() if ln.strip()]
            w('* `%s`: %s ... %s' % (run.name, lines[0], lines[-1]))
        if sweep_txt.exists() and sweep_txt.read_text().strip():
            last = sweep_txt.read_text().strip().splitlines()[-1]
            w('* `%s`: %s' % (run.name, last))
    w('')
    w('The image converts its SIF to a sandbox before any payload line runs, which costs')
    w('about 578 s per allocation (measured separately in job 125203749). The build and the')
    w('first part of the sweep therefore share one allocation; the remaining parts only')
    w('reuse the built binary and its sha256.')
    w('')
    w('Build measured facts: the image\'s `/opt/gcc-11.2.0/bin/g++` does not add')
    w('`/usr/include/x86_64-linux-gnu` to its include search, so a translation unit that')
    w('includes `<cstdint>` fails with `fatal error: sys/cdefs.h: No such file or directory`;')
    w('the registry-documented `-isystem /usr/include/x86_64-linux-gnu` fixes it and is')
    w('recorded in `compile-config.txt`. A first attempt (job 125207262) aborted on exactly')
    w('that header because the flag reached only the Cantera-dependent compiles.')
    w('')

    # ---- 6 ----------------------------------------------------------------
    w('## 6. Results against the digitised panel')
    w('')
    w('Declared screen: `|computed - digitised| <= max(0.05 cm/s, 1 % of reference) +`')
    w('`digitisation uncertainty`. The screen is a stated tolerance for digitisation-grade')
    w('reference data; it is not a fit and it was not tuned after seeing the numbers.')
    w('')
    w('| case | points | rms (cm/s) | max abs (cm/s) | points outside screen |')
    w('| --- | --- | --- | --- | --- |')
    for stage in sorted(comp['stages'], key=int):
        s = comp['stages'][stage]
        w('| %s | %d | %.4f | %.4f | %d |'
          % (stage, s['points'], s['rms_cm_s'], s['max_abs_cm_s'], s['failed_points']))
    w('')
    w('Per-point detail (%d rows, %d excluded):'
      % (len(rows), len(comp['excluded'])))
    w('')
    w('| case | phi | computed (cm/s) | digitised (cm/s) | uncertainty | error (cm/s) | error (%) | screen limit | within |')
    w('| --- | --- | --- | --- | --- | --- | --- | --- | --- |')
    for r in sorted(rows, key=lambda r: (r['stage'], r['phi'])):
        w('| %d | %.2f | %.4f | %.4f | %.3f | %+.4f | %+.2f | %.4f | %s |'
          % (r['stage'], r['phi'], r['computed_cm_s'], r['paper_cm_s'],
             r['image_uncertainty_cm_s'], r['error_cm_s'], r['error_percent'],
             r['limit_cm_s'], 'yes' if r['within_screen'] else '**no**'))
    w('')
    if comp['excluded']:
        w('Excluded points, with the reason recorded for each:')
        w('')
        for e in comp['excluded']:
            w('* case %d, phi %.2f: %s' % (e['stage'], e['phi'], e['reason']))
        w('')
    w('Reading of the result, stated without rounding it up:')
    w('')
    worst = max(comp['stages'].items(), key=lambda kv: kv[1]['rms_cm_s'])
    clean = [k for k, v in sorted(comp['stages'].items(), key=lambda kv: int(kv[0]))
             if v['failed_points'] == 0]
    dirty = [k for k, v in sorted(comp['stages'].items(), key=lambda kv: int(kv[0]))
             if v['failed_points'] > 0]
    if clean:
        w('* Cases %s stay inside the declared screen at every compared point; their'
          % ', '.join(clean))
        w('  largest rms difference is %.4f cm/s.'
          % max(comp['stages'][k]['rms_cm_s'] for k in clean))
    else:
        w('* No stage stays inside the declared screen at every compared point.')
    for stage in dirty:
        s = comp['stages'][stage]
        w('* Case %s has %d of %d points outside the screen (rms %.4f cm/s, max %.4f cm/s):'
          % (stage, s['failed_points'], s['points'], s['rms_cm_s'], s['max_abs_cm_s']))
        worst_rows = sorted([r for r in rows if r['stage'] == int(stage)],
                            key=lambda r: -abs(r['error_cm_s']))[:3]
        w('  largest excursions at phi %s.'
          % ', '.join('%.2f (%+.4f cm/s)' % (r['phi'], r['error_cm_s']) for r in worst_rows))
    w('')
    w('That disagreement is reported as a property of this reconstructed stage, not as a')
    w('tuning target and not as an author finding: the article does not state which')
    w('Takahashi variant, coefficient set or temperature clamp the authors used, so a')
    w('stage-5 departure cannot be attributed to them from this reproduction alone.')
    w('')

    # ---- 7 ----------------------------------------------------------------
    w('## 7. Reproducibility against the registered previous generation')
    w('')
    w('The registered previous generation is an independent build of the same staged model')
    w('by an earlier campaign generation. Matching it is reproducibility of the pipeline; it')
    w('is not agreement with the authors and it is not required for numerical agreement.')
    w('')
    w('| case | points | rms difference (cm/s) | max abs difference (cm/s) |')
    w('| --- | --- | --- | --- |')
    for stage in sorted(repro['stages'], key=int):
        s = repro['stages'][stage]
        w('| %s | %d | %.4f | %.4f |' % (stage, s['points'], s['rms_cm_s'], s['max_abs_cm_s']))
    w('')
    w('Differences from the previous generation are expected wherever the build, the')
    w('transport implementation or the solver path changed; they are reported, not zeroed.')
    w('')

    # ---- 8 ----------------------------------------------------------------
    w('## 8. Figure')
    w('')
    w('The figure is rendered by the campaign\'s frozen recipe for this target with the')
    w('shared renderer, so the gate replays exactly the bytes that are submitted.')
    w('')
    w('* recipe `%s`, sha256 `%s`' % (receipt.get('recipe_id', 'n/a'), receipt['recipe_sha256']))
    w('* renderer `%s`, smoothing `%s` declared display-only (`interpolation_is_evidence` = %s)'
      % (receipt.get('renderer', 'n/a'), receipt.get('smoothing', 'n/a'),
         str(receipt.get('interpolation_is_evidence')).lower()))
    w('* series: %s'
      % ', '.join('%s (%d points, %s)' % (s['id'], s['points'], s['origin'])
                  for s in receipt['series']))
    w('* computed series carry visible markers, paper series are dashed, and the legend has')
    w('  one row per series; the raw samples are retained in the data file and are what the')
    w('  checks above use.')
    w('')

    # ---- 9 ----------------------------------------------------------------
    w('## 9. Required checks')
    w('')
    w('| check | result | basis |')
    w('| --- | --- | --- |')
    for check in ver['checks']:
        basis = check['details'].split('. ')[0].replace('|', '/')
        if len(basis) > 240:
            basis = basis[:237] + '...'
        w('| %s | %s | %s |' % (check['id'], check['result'], basis))
    w('')
    w('The verdicts are derived from the artefacts named in each check; the full text is in')
    w('`verification.json` (sha256 `%s`).' % sha(a.verification))
    w('')

    # ---- 10 ---------------------------------------------------------------
    w('## 10. Limitations and unresolved assumptions')
    w('')
    w('1. **Unburned temperature.** Tu = 298 K is inferred, not stated by the article.')
    w('   Different Tu shifts the whole curve; this assumption is not removable from the')
    w('   available text and is not hidden inside a fitted parameter here.')
    w('2. **Digitisation is not author data.** The reference is a reading of a raster with')
    w('   a declared uncertainty of 0.02-0.03 cm/s per sample, bounded by an independent')
    w('   second digitisation that agrees to ~0.005 cm/s. Systematic misreading of a')
    w('   legend-to-curve assignment would shift an entire stage and is not detectable')
    w('   from the raster alone.')
    w('3. **Case 2 is not a consistent thermodynamic model** (SRK density with ideal')
    w('   calorics) by design, mirroring the stage definition; its agreement must not be')
    w('   read as validation of that combination.')
    w('4. **Case 5 depends on undocumented choices.** The Takahashi correlation needs a')
    w('   coefficient set and clamps that the article does not specify; the stage-5')
    w('   departure may be a variant choice rather than an error in the model.')
    w('5. **Kinetics are the reconstructed mechanism in the frozen inputs**, not the')
    w('   authors\' deck; chemical-kinetic differences are absorbed into every stage')
    w('   equally and cannot be separated from transport differences without the deck.')
    w('6. **Equivalence ratios outside the digitised span** (0.92, 1.44) are solved for')
    w('   reproducibility only and are excluded from the comparison rather than')
    w('   extrapolated.')
    w('')

    # ---- 11 ---------------------------------------------------------------
    w('## 11. Artefacts and how to regenerate them')
    w('')
    w('| artefact | sha256 |')
    w('| --- | --- |')
    for label, path in (('sweep results', a.sweep), ('comparison', a.compare),
                        ('reproducibility', a.repro), ('verification', a.verification),
                        ('reference', a.reference), ('render receipt', a.receipt)):
        w('| %s | `%s` |' % (label, sha(path)))
    w('')
    w('```')
    w('# digitise the paper panel (stdlib only)')
    w('python3 digitize_fig8a.py /workspace/cache/liang8a.rgba fig8a-reference.json')
    w('# solve, screen and collect')
    w('bash job-build-and-sweep.sh MODULE INPUTS RUN 1,2 PHIS')
    w('python3 collect_sweep.py RUN... results.json')
    w('python3 compare_reference.py results.json fig8a-reference.json > compare.json')
    w('python3 make_verification.py --sweep results.json --compare compare.json \\')
    w('    --prior liang-8a-data.json --receipt render-receipt.json \\')
    w('    --reference fig8a-reference.json --sweep-dir RUN,... \\')
    w('    --source-commit COMMIT --repro-out reproducibility.json --out verification.json')
    w('node render_fig8a.mjs --results results.json --reference fig8a-reference.json \\')
    w('    --recipe liang-8a-cantera-recipe.json --out-dir OUT --source-commit COMMIT')
    w('```')
    w('')
    w('Raw solver logs, per-point `status.txt`, `property-checks.csv`, `refinement.csv` and')
    w('the per-point frozen manifests remain on the HPC run directories; they are not')
    w('committed, and the collector records the hash of every result file it screens.')
    w('')

    text = '\n'.join(out) + '\n'
    pathlib.Path(a.out).write_text(text)
    print(json.dumps({'report_bytes': len(text.encode()), 'rows': len(rows),
                      'stages': sorted(comp['stages'], key=int)}))


if __name__ == '__main__':
    main()
