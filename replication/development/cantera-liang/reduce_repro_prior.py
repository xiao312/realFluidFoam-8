#!/usr/bin/env python3
"""Reduce the previous-generation re-run of Liang Fig. 8(a) to a per-stage delta table.

The registered previous generation of `liang-8a` is the payload's own data file, whose
rows name the source commit that produced them. That commit is an ancestor in this
repository, so the generation is not lost: its `cantera-liang` module can be extracted and
rebuilt, and the same frozen inputs can be pushed through it. This reducer compares what
that rebuild produces against what the generation recorded, point by point.

Two things must be kept apart and are reported separately:

  harness   stage 1 uses the ideal-gas phase and mixture-averaged transport, i.e. none of
            the staged-model code the later stages add. If stage 1 reproduces and the
            later stages do not, the difference is in the staged model, not in the machine,
            the mechanism, the inputs or the flame solver.
  grid      each case records the grid points and the refinement levels the run reached.
            A non-reproducing point that also stopped on a coarser grid is flagged, so a
            convergence shortfall cannot be reported as a model difference.

Usage:
  python3 reduce_repro_prior.py --expected EXPECTED.json --cases CASES.txt --out OUT.json

CASES.txt is written by `job-repro-prior.sh`: one
`stage|phi|tree|rc|elapsed_s|points|speed` line per attempted point, speed empty when the
case did not complete. `tree` is the short commit hash of the archived tree the point was run
with. The declared rows of the previous generation do not all come from one tree, so a point
run with a tree other than its own is rejected rather than compared: that would measure the
two builds against each other, not the reproduction.
"""
import argparse
import json
import math

TOL_CM_S = 1.0e-3          # declared agreement threshold, same order as the stage-1 spread
GRID_MIN_POINTS = 200      # below this the case is treated as under-refined, not a model test


def read_cases(path):
    cases = []
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            fields = line.split('|')
            if len(fields) != 7:
                raise ValueError(f'case line has {len(fields)} fields, expected 7: {line!r}')
            stage, phi, tree, rc, elapsed, points, speed = fields
            cases.append({
                'stage': int(stage),
                'phi': float(phi),
                'tree': tree,
                'rc': int(rc),
                'elapsed_s': int(elapsed),
                'points': int(points) if points not in ('', '-') else None,
                'speed_cm_s': float(speed) if speed not in ('', '-') else None,
            })
    return cases


def reduce_table(expected, cases):
    wanted = {(p['stage'], round(float(p['phi']), 4)): p for p in expected['points']}
    rows = []
    seen = set()
    for case in cases:
        key = (case['stage'], round(case['phi'], 4))
        declared = wanted.get(key)
        if declared is None:
            raise ValueError(f'case {key} is not in the declared point list')
        seen.add(key)
        computed = case['speed_cm_s']
        prior = float(declared['value_cm_s'])
        declared_source = declared.get('declared_source') or expected['prior_source_commit']
        declared_tree = declared_source[:8]
        row = {
            'stage': case['stage'],
            'phi': case['phi'],
            'declared_prior_cm_s': prior,
            'computed_cm_s': computed,
            'rc': case['rc'],
            'elapsed_s': case['elapsed_s'],
            'points': case['points'],
            'declared_job': declared.get('declared_job'),
            'declared_source': declared_source,
            'declared_tree': declared_tree,
            'tree': case['tree'],
            'tree_matches_declared': case['tree'] == declared_tree,
        }
        if not row['tree_matches_declared']:
            row['delta_cm_s'] = None
            row['reproduced'] = False
            row['reason'] = 'run with a tree other than the one that declared this value'
        elif computed is None:
            row['delta_cm_s'] = None
            row['reproduced'] = False
            row['reason'] = 'case did not complete'
        else:
            delta = computed - prior
            row['delta_cm_s'] = delta
            row['reproduced'] = abs(delta) <= TOL_CM_S
            if not row['reproduced']:
                row['reason'] = ('under-refined grid' if case['points'] is not None
                                 and case['points'] < GRID_MIN_POINTS else 'numerical difference')
            else:
                row['reason'] = 'within the declared threshold'
        rows.append(row)
    missing = [k for k in wanted if k not in seen]
    return rows, missing


def stage_summary(rows):
    summary = {}
    for stage in sorted({r['stage'] for r in rows}):
        block = [r for r in rows if r['stage'] == stage]
        deltas = [r['delta_cm_s'] for r in block if r['delta_cm_s'] is not None]
        summary[str(stage)] = {
            'points': len(block),
            'completed': len(deltas),
            'reproduced': sum(1 for r in block if r['reproduced']),
            'rms_cm_s': (math.sqrt(sum(d * d for d in deltas) / len(deltas)) if deltas else None),
            'max_abs_cm_s': (max(abs(d) for d in deltas) if deltas else None),
            'min_points': min((r['points'] for r in block if r['points'] is not None), default=None),
        }
    return summary


def verdict(rows, missing):
    if any(not r['tree_matches_declared'] for r in rows):
        return 'wrong_tree'
    if missing:
        return 'incomplete'
    if not rows:
        return 'no_cases'
    if all(r['reproduced'] for r in rows):
        return 'reproduced'
    stage1 = [r for r in rows if r['stage'] == 1]
    staged = [r for r in rows if r['stage'] != 1]
    if stage1 and all(r['reproduced'] for r in stage1) and staged and not any(
            r['reproduced'] for r in staged):
        return 'harness_reproduced_staged_model_differs'
    if any(r['computed_cm_s'] is None for r in rows):
        return 'incomplete'
    return 'not_reproduced'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected', required=True)
    parser.add_argument('--cases', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--binaries', default=None,
                        help='file of `sha256  path` lines, one per archived tree')
    args = parser.parse_args()

    expected = json.load(open(args.expected, encoding='utf-8'))
    binaries = {}
    if args.binaries:
        with open(args.binaries, encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                digest, path = line.split(None, 1)
                tag = path.rsplit('/', 1)[-1].split('-')[0]
                binaries[tag] = {'sha256': digest, 'path': path.rsplit('/', 1)[-1]}
    cases = read_cases(args.cases)
    rows, missing = reduce_table(expected, cases)
    payload = {
        'schema': 'forge-liang8a-prior-rerun-v2',
        'target': 'liang-8a',
        'reference_file': expected['reference_file'],
        'reference_sha256': expected['reference_sha256'],
        'prior_source_commit': expected['prior_source_commit'],
        'prior_source_commits': sorted({r['declared_source'] for r in rows}),
        'prior_module_archive_sha256': expected['prior_module_archive_sha256'],
        'prior_binaries': binaries,
        'threshold_cm_s': TOL_CM_S,
        'grid_floor_points': GRID_MIN_POINTS,
        'cli': expected['cli'],
        'rows': rows,
        'stages': stage_summary(rows),
        'missing': [{'stage': s, 'phi': p} for s, p in missing],
        'verdict': verdict(rows, missing),
        'reading': (
            'stage 1 is the harness control: it uses the ideal-gas phase and mixture-averaged '
            'transport, so it exercises none of the staged-model code. If it reproduces and '
            'stages 2-4 do not, the divergence is in the staged model that the two '
            'generations implement differently, not in the machine or the inputs. Each point '
            'is compared only against the row that its own tree declared, because the '
            'registered rows do not all come from one tree.'),
        'scope': 'this rerun rebuilds the previous generation from its own source commit and '
                 'its own frozen inputs; it does not assert paper agreement and it does not '
                 'replace the determinism evidence of repeated runs of the current tree.',
    }
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')
    print(json.dumps({'verdict': payload['verdict'], 'rows': len(rows),
                      'stages': payload['stages']}, indent=1))


if __name__ == '__main__':
    main()
