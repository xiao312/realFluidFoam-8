"""Replay conservative Liang Fig.8(a) bounds against computed phi=1.10 results."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('--require-paper-agreement', action='store_true')
    args = parser.parse_args()
    records = json.loads(args.results.read_text(encoding='utf-8-sig'))['results']
    values = {r['stage']: r['speed_cm_s'] for r in records if abs(r['phi']-1.1)<1e-8}
    if not {1, 2, 3, 4}.issubset(values):
        raise ValueError('Need completed Cases 1–4 at phi=1.10')
    checks = {
        'ideal_within_visual_7.40_to_7.55_cm_s': 7.40 <= values[1] <= 7.55,
        'eos_change_below_0.05_cm_s': abs(values[2]-values[1]) <= .05,
        'enthalpy_within_visual_7.00_to_7.18_cm_s': 7.00 <= values[3] <= 7.18,
        'conductivity_increment_below_0.15_cm_s': abs(values[4]-values[3]) <= .15,
    }
    print(json.dumps({'speeds_cm_s': values, 'increments_cm_s': {
        str(stage): values[stage]-values[stage-1] for stage in range(2, 5)},
        'checks': checks, 'agreement': all(checks.values()),
        'reference': 'Liang Fig.8(a), conservative visual bounds, not exact author values'}, indent=2))
    if args.require_paper_agreement and not all(checks.values()):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
