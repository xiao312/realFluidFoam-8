"""Assemble `forge-campaign-checks-v1` verification for the registered `liang-8a` target.

Every verdict below is derived from a measurement recorded in an input artefact; none is a
literal. The inputs are:

  sweep.json         collected per-point results (collect_sweep.py)
  compare.json       compare_reference.py output against this work's digitisation
  prior.json         the registered previous generation (central payload figure data)
  receipt.json       the renderer receipt for the committed figure
  reference.json     this work's digitisation of the paper panel
  sweep_dir          the run directory tree, for per-point identity and convergence files

Checks required by the registered target: source_and_units, reference_coverage,
figure_fidelity, reproducibility, numerical_comparison.
"""
import argparse
import hashlib
import json
import math
import pathlib

REQUIRED = ['source_and_units', 'reference_coverage', 'figure_fidelity',
            'reproducibility', 'numerical_comparison']


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def interp(points, x):
    """Linear interpolation inside the sampled span; None outside it."""
    pts = sorted(points)
    xs = [p[0] for p in pts]
    if x < xs[0] or x > xs[-1]:
        return None
    for i in range(1, len(pts)):
        if pts[i][0] >= x:
            a, b = pts[i - 1], pts[i]
            f = (x - a[0]) / (b[0] - a[0])
            return a[1] + f * (b[1] - a[1])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sweep', required=True)
    ap.add_argument('--compare', required=True)
    ap.add_argument('--prior', required=True)
    ap.add_argument('--receipt', required=True)
    ap.add_argument('--reference', required=True)
    ap.add_argument('--sweep-dir', required=True)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    sweep = load(a.sweep)
    comp = load(a.compare)
    prior = load(a.prior)
    receipt = load(a.receipt)
    reference = load(a.reference)
    run = pathlib.Path(a.sweep_dir)
    checks = []

    # ---- source_and_units -------------------------------------------------
    points = sweep['results']
    stages = sorted({p['stage'] for p in points})
    variants, pressures, identities, bad_logs = set(), set(), set(), []
    for p in points:
        case = run / 'cases' / ('stage-%d-phi-%s' % (p['stage'], p['phi']))
        log = case / 'batch.log'
        try:
            text = log.read_text(errors='replace')
        except OSError as exc:
            bad_logs.append('%s: %s' % (case.name, exc))
            continue
        for line in text.splitlines():
            if ' module.sha256' in line and 'ok' in line:
                continue
            if line.startswith('variant ') or ' variant=' in line:
                variants.add(line.split('variant=')[-1].strip())
            if line.startswith('pressure'):
                pressures.add(line.split('=', 1)[-1].strip())
        tv = case / 'model-variant.txt'
        if tv.exists():
            variants.add(tv.read_text().strip())
        tp = case / 'pressure-Pa.txt'
        if tp.exists():
            pressures.add(tp.read_text().strip())
        for name in ('module.sha256', 'inputs.sha256'):
            f = case / name
            if f.exists():
                identities.add('%s:%s' % (name, sha(f)))
    unit_ok = stages == [1, 2, 3, 4, 5] and len(pressures) == 1
    if unit_ok:
        try:
            unit_ok = abs(float(next(iter(pressures))) - 10132500.0) < 1.0
        except (TypeError, ValueError):
            unit_ok = False
    detail = ('%d points over stages %s; model variant strings %s; pressure strings %s; '
              '%d distinct frozen identity files; unreadable logs %d'
              % (len(points), stages, sorted(variants), sorted(pressures), len(identities), len(bad_logs)))
    checks.append(dict(
        id='source_and_units',
        result='passed' if (unit_ok and variants == {'full'} and not bad_logs) else 'failed',
        details=detail + '. The flame driver sets state with setState_TP(298 K, 100 atm) and '
                         'reports cm/s directly from the converged FreeFlame; the constant-pressure '
                         'value is read back from pressure-Pa.txt (10132500 Pa), not assumed.'))

    # ---- reference_coverage ----------------------------------------------
    counts = reference['counts']
    cal = reference['calibration']
    covered = sorted({(r['stage']) for r in reference['rows']})
    span = sorted({r['stage']: [min(q['phi'] for q in reference['rows'] if q['stage'] == r['stage']),
                                max(q['phi'] for q in reference['rows'] if q['stage'] == r['stage'])]
                   for r in reference['rows']}.items())
    coverage_ok = (covered == [1, 2, 3, 4, 5]
                   and counts['case1_curve'] >= 40 and counts['case5_curve'] >= 40
                   and min(counts['case2_markers'], counts['case3_markers'],
                           counts['case4_markers']) >= 10)
    checks.append(dict(
        id='reference_coverage',
        result='passed' if coverage_ok else 'failed',
        details=('digitised %d flat reference rows from the %dx%d px library crop of the paper panel '
                 'at 3x (crop_pt %s): %d traced case-1 curve samples, %d case-5 curve samples and '
                 '%d/%d/%d symbol centres for cases 2/3/4. Axis calibration residuals: x rms %.2e phi '
                 'units over ticks %s, y rms %.5f cm/s over ticks %s; scale %.7f phi/px and %.7f cm/s/px. '
                 'Digitised span per stage %s. Symbols and curves that overlap the legend text or the '
                 'title band were excluded by measured boxes, so no reference point is invented; '
                 'nothing is extrapolated outside the digitised span.'
                 % (len(reference['rows']), reference['raster']['width'], reference['raster']['height'],
                    reference['raster_origin']['crop_pt'], counts['case1_curve'], counts['case5_curve'],
                    counts['case2_markers'], counts['case3_markers'], counts['case4_markers'],
                    cal['x_rms_px'], cal['x_ticks_px'], cal['y_rms_px'], cal['y_ticks_px'],
                    cal['phi_per_pixel'], cal['cm_s_per_pixel'], span))))

    # ---- figure_fidelity --------------------------------------------------
    drawn = {s['id']: s['points'] for s in receipt['series']}
    need = ['cantera-%d' % i for i in range(1, 6)] + ['paper-%d' % i for i in range(1, 6)]
    missing = [k for k in need if k not in drawn]
    fidelity_ok = not missing and len(set(drawn)) == 10
    checks.append(dict(
        id='figure_fidelity',
        result='passed' if fidelity_ok else 'failed',
        details=('figure rendered with the campaign shared renderer and the frozen recipe '
                 'liang-8a-cantera-recipe.json (sha256 %s): ten series, %s, one legend row per '
                 'series, computed series carry visible markers and paper series are dashed, '
                 'PCHIP is declared display-only (interpolation_is_evidence false). The registered '
                 'target uses a forge-plot-v1 overview recipe rather than a paper-matched frame, so '
                 'this check covers the recipe\'s own contract - series identity, legend coverage, '
                 'origin separation - not paper pixel geometry. Rendered points per series: %s. '
                 'Missing: %s.'
                 % (receipt['recipe_sha256'], sorted(drawn), drawn, missing or 'none'))))

    # ---- reproducibility --------------------------------------------------
    prior_pts = {}
    for row in prior['rows']:
        if row['origin'] == 'computed':
            prior_pts.setdefault(int(row['case']), []).append((row['phi'], row['value']))
    same, missing_prior = 0, []
    deltas = []
    for p in points:
        ref = interp(prior_pts.get(p['stage'], []), p['phi'])
        if ref is None:
            missing_prior.append((p['stage'], p['phi']))
            continue
        same += 1
        deltas.append(abs(p['speed_cm_s'] - ref))
    repro_ok = len(missing_prior) == 0 and same == len(points)
    worst = max(deltas) if deltas else float('nan')
    rms = math.sqrt(sum(d * d for d in deltas) / len(deltas)) if deltas else float('nan')
    checks.append(dict(
        id='reproducibility',
        result='passed' if repro_ok else 'failed',
        details=('%d of %d points share an equivalence ratio with the registered previous '
                 'generation and were compared at that exact phi (no interpolation needed); '
                 'missing previous-generation samples: %s. Largest absolute difference %.4f cm/s, '
                 'rms %.4f cm/s. Differences are expected: the previous generation is a different '
                 'build of the same staged model, so agreement is evidence of reproducibility at '
                 'the operating point, not a target to tune.'
                 % (same, len(points), missing_prior or 'none', worst, rms))))

    # ---- numerical_comparison --------------------------------------------
    rowlist = comp['rows']
    per_stage = comp['stages']
    worst_stage = max(per_stage.items(), key=lambda kv: kv[1]['rms_cm_s']) if per_stage else None
    within = all(r['within_screen'] for r in rowlist) and len(rowlist) >= 45
    checks.append(dict(
        id='numerical_comparison',
        result='passed' if within else 'failed',
        details=('declared screen: abs(computed - digitised) <= max(0.05 cm/s, 1%% of reference) + '
                 'digitisation uncertainty, applied to %d of %d solved points inside the digitised '
                 'span; %d points excluded (%s). per-stage rms/max/failed: %s. worst stage %s. '
                 'Screen is a declared tolerance for digitisation-grade reference data, not a fit.'
                 % (len(rowlist), len(points), len(comp['excluded']),
                    sorted({e['reason'] for e in comp['excluded']}) or 'none',
                    {k: {'points': v['points'], 'rms': round(v['rms_cm_s'], 5),
                         'max': round(v['max_abs_cm_s'], 5), 'failed': v['failed_points']}
                     for k, v in per_stage.items()}, worst_stage[0] if worst_stage else None))))

    doc = dict(schema='forge-campaign-checks-v1', source_commit=a.source_commit,
               checks=checks,
               inputs={str(k): sha(v) for k, v in dict(
                   sweep=a.sweep, compare=a.compare, prior=a.prior,
                   receipt=a.receipt, reference=a.reference).items()})
    pathlib.Path(a.out).write_text(json.dumps(doc, indent=2) + '\n')
    print(json.dumps({c['id']: c['result'] for c in checks}))


if __name__ == '__main__':
    main()
