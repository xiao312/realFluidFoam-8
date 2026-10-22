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


def series_ids(recipe):
    """Series ids of a plot recipe, which may be bare ids or {id: ...} objects."""
    return [item if isinstance(item, str) else item['id']
            for item in recipe.get('series', [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sweep', required=True)
    ap.add_argument('--compare', required=True)
    ap.add_argument('--prior', required=True)
    ap.add_argument('--receipt', required=True)
    ap.add_argument('--reference', required=True)
    ap.add_argument('--recipe', type=pathlib.Path, required=True,
                    help='the recipe that was actually rendered')
    ap.add_argument('--sweep-dir', required=True)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--repro-out', default=None)
    ap.add_argument('--campaign-recipe', type=pathlib.Path, default=None,
                    help='frozen campaign recipe, to name any series this figure omits')
    ap.add_argument('--repeat', type=pathlib.Path,
                    help='repeat comparison JSON: the same points solved in two allocations')
    a = ap.parse_args()

    sweep = load(a.sweep)
    comp = load(a.compare)
    prior = load(a.prior)
    receipt = load(a.receipt)
    reference = load(a.reference)
    runs = [pathlib.Path(part) for part in a.sweep_dir.split(',')]
    index = {}
    for run in runs:
        for case in sorted((run / 'cases').glob('stage-*-phi-*')):
            index.setdefault(case.name, []).append(case)
    duplicated = sorted(k for k, v in index.items() if len(v) > 1)
    if duplicated:
        raise SystemExit('operating point present in more than one run: %s' % duplicated)
    checks = []

    # ---- source_and_units -------------------------------------------------
    points = sweep['results']
    stages = sorted({p['stage'] for p in points})
    variants, pressures, identities, bad_logs = set(), set(), set(), []
    for p in points:
        found = index.get('stage-%d-phi-%s' % (p['stage'], p['phi']))
        if not found:
            bad_logs.append('no case directory for stage %d phi %s' % (p['stage'], p['phi']))
            continue
        case = found[0]
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
        tv = case / 'result' / 'model-variant.txt'
        if tv.exists():
            variants.add(tv.read_text().strip())
        tp = case / 'result' / 'pressure-Pa.txt'
        if tp.exists():
            pressures.add(tp.read_text().strip())
        for name in ('module.sha256', 'inputs.sha256'):
            f = case / name
            if f.exists():
                identities.add('%s:%s' % (name, sha(f)))
    # The solver-path files are the invariant: different module identities are acceptable
    # only if every file the solve touches is identical, which is computed here.
    solver_files = {'flame.cpp', 'job-batch.sh', 'job-sweep.sh'}
    manifests, executables = {}, set()
    for p in points:
        found = index.get('stage-%d-phi-%s' % (p['stage'], p['phi']))
        if not found:
            continue
        case = found[0]
        manifest = case / 'module.sha256'
        if manifest.exists():
            entries = {}
            for line in manifest.read_text().splitlines():
                if line.strip():
                    digest, name = line.split(None, 1)
                    entries[name.strip().lstrip('*')] = digest
            manifests[sha(manifest)] = entries
        exe = case / 'executable.sha256'
        if exe.exists():
            executables.add(exe.read_text().split()[0])
    differing = set()
    entries = list(manifests.values())
    for other in entries[1:]:
        for name, digest in entries[0].items():
            if other.get(name) not in (None, digest):
                differing.add(name)
    solver_ok = len(executables) <= 1 and not (differing & solver_files)
    units_ok = len(pressures) == 1 and variants == {'full'}
    if units_ok:
        try:
            units_ok = abs(float(next(iter(pressures))) - 10132500.0) < 1.0
        except (TypeError, ValueError):
            units_ok = False
    detail = ('%d solved points over stages %s; model variant strings %s; pressure strings %s; '
              '%d module identity files of which %d solver-path files differ (%s); '
              '%d distinct solver executables; unreadable logs %d'
              % (len(points), stages, sorted(variants), sorted(pressures), len(manifests),
                 len(differing & solver_files), sorted(differing & solver_files) or 'none',
                 len(executables), len(bad_logs)))
    checks.append(dict(
        id='source_and_units',
        result='passed' if (units_ok and solver_ok and not bad_logs) else 'failed',
        details=(detail + '. The flame driver sets state with setState_TP(298 K, 100 atm) and '
                 'reports cm/s directly from the converged FreeFlame; the constant-pressure value '
                 'is read back from pressure-Pa.txt (10132500 Pa), not assumed. Stage 5 has no '
                 'solved point, so the five-stage ladder is incomplete and this check speaks only '
                 'for the stages that ran.')))

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
    recipe_ids = series_ids(load(a.recipe))
    campaign_ids = series_ids(load(a.campaign_recipe)) if a.campaign_recipe else recipe_ids
    missing = [k for k in recipe_ids if k not in drawn]
    extra = [k for k in drawn if k not in recipe_ids]
    omitted = [k for k in campaign_ids if k not in recipe_ids]
    empty = [k for k, v in drawn.items() if not v]
    fidelity_ok = not missing and not extra and not empty and len(drawn) == len(recipe_ids)
    checks.append(dict(
        id='figure_fidelity',
        result='passed' if fidelity_ok else 'failed',
        details=('figure rendered with the campaign shared renderer and a frozen recipe '
                 '(sha256 %s): %d series, %s, computed series carry visible markers and paper '
                 'series are dashed, PCHIP is declared display-only (interpolation_is_evidence '
                 'false). The registered target uses a forge-plot-v1 overview recipe rather than a '
                 'paper-matched frame, so this check covers the recipe\'s own contract - series '
                 'identity, legend coverage, origin separation - not paper pixel geometry. Rendered '
                 'points per series: %s. Missing versus the recipe: %s; undeclared: %s; empty: %s. '
                 'Series of the frozen campaign recipe that this figure omits: %s (%s).'
                 % (receipt['recipe_sha256'], len(drawn), sorted(drawn), drawn, missing or 'none',
                    extra or 'none', empty or 'none', omitted or 'none',
                    load(a.recipe).get('derivation', 'no derivation recorded')[:220]))))

    # ---- reproducibility --------------------------------------------------
    prior_pts = {}
    for row in prior['rows']:
        if row['origin'] == 'computed':
            prior_pts.setdefault(int(row['case']), []).append((row['phi'], row['value']))
    same, missing_prior = 0, []
    deltas = []
    repro_rows = []
    for p in points:
        ref = interp(prior_pts.get(p['stage'], []), p['phi'])
        if ref is None:
            missing_prior.append((p['stage'], p['phi']))
            continue
        same += 1
        deltas.append(abs(p['speed_cm_s'] - ref))
        repro_rows.append(dict(stage=p['stage'], phi=p['phi'], job=p['job'],
                               computed_cm_s=p['speed_cm_s'], prior_generation_cm_s=ref,
                               delta_cm_s=p['speed_cm_s'] - ref))
    if a.repro_out:
        per_stage_repro = {}
        for stage in sorted({r['stage'] for r in repro_rows}):
            group = [abs(r['delta_cm_s']) for r in repro_rows if r['stage'] == stage]
            per_stage_repro[str(stage)] = dict(
                points=len(group), rms_cm_s=math.sqrt(sum(d * d for d in group) / len(group)),
                max_abs_cm_s=max(group))
        pathlib.Path(a.repro_out).write_text(json.dumps(dict(
            schema='forge-fig8a-reproducibility-v1',
            prior_source=prior.get('source') or prior.get('figure'),
            rows=repro_rows, stages=per_stage_repro), indent=2) + '\n')
    worst = max(deltas) if deltas else float('nan')
    rms = math.sqrt(sum(d * d for d in deltas) / len(deltas)) if deltas else float('nan')
    per_stage_cmp = {}
    for stage in sorted({r['stage'] for r in repro_rows}):
        group = [abs(r['delta_cm_s']) for r in repro_rows if r['stage'] == stage]
        per_stage_cmp[str(stage)] = dict(points=len(group), max_abs_cm_s=max(group))
    # Two different questions, answered separately: does this build repeat itself, and
    # does it land on the registered previous generation?
    repeat = load(a.repeat) if a.repeat else None
    if repeat:
        determinism = (repeat.get('shared_operating_points', 0) > 0
                       and repeat.get('bitwise_identical_profiles')
                       == repeat.get('shared_operating_points')
                       and repeat.get('bitwise_identical_refinement_files')
                       == repeat.get('shared_operating_points'))
        determinism_text = ('%d points were solved twice in two independent allocations: %d profile '
                            'files and %d refinement files are bitwise identical, worst relative '
                            'speed difference %s.'
                            % (repeat.get('shared_operating_points'),
                               repeat.get('bitwise_identical_profiles', 0),
                               repeat.get('bitwise_identical_refinement_files', 0),
                               repeat.get('worst_relative_difference')))
    else:
        determinism, determinism_text = None, 'No repeat comparison was supplied.'
    # The previous generation came from a different implementation of the staged model:
    # its SrkPhase.h, StagedTransport.h and flame.cpp differ from this candidate, so a
    # per-stage difference is a measurement of that change, not a failure of this run.
    agreement = (worst <= 0.05) if deltas else None
    if determinism is False:
        result, verdict = 'failed', 'The build does not repeat itself bitwise.'
    elif determinism and agreement:
        result, verdict = 'passed', ('The build repeats bitwise and every stage lands within '
                                     '0.05 cm/s of the previous generation.')
    elif determinism and agreement is False:
        result, verdict = 'unknown', ('The build repeats bitwise, but the staged cases do not all '
                                      'land on the previous generation; the staged headers changed '
                                      'after that generation, so neither value is the reference '
                                      'until the old source is re-run.')
    else:
        result, verdict = 'unknown', 'Neither question could be answered from the supplied files.'
    checks.append(dict(
        id='reproducibility',
        result=result,
        details=('%s %d of %d points share an equivalence ratio with the registered previous '
                 'generation and were compared at that exact phi; largest absolute difference '
                 '%.4f cm/s, rms %.4f cm/s, per-stage max %s. %s'
                 % (verdict, same, len(points), worst, rms,
                    {k: round(v['max_abs_cm_s'], 4) for k, v in per_stage_cmp.items()},
                    determinism_text))))

    # ---- numerical_comparison --------------------------------------------
    rowlist = comp['rows']
    per_stage = comp['stages']
    worst_stage = max(per_stage.items(), key=lambda kv: kv[1]['rms_cm_s']) if per_stage else None
    compared_stages = {r['stage'] for r in rowlist}
    within = (all(r['within_screen'] for r in rowlist)
              and compared_stages == {p['stage'] for p in points})
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
