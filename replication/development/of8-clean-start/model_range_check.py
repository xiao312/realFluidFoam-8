#!/usr/bin/env python3
"""Decide, statically, whether a requested operating state is inside the frozen thermo table.

Usage:
    model_range_check.py --thermo CONSTANT_DIR --temperature 100 --pressure 60e5 \
                         --composition H2=0.5,O2=0.5 [--json out.json]

Exit status: 0 supported, 3 unsupported (a model-range stop, not a crash), 2 unreadable
table. Nothing is submitted on exit status 3: the point is to refuse the admission before
an allocation is spent, and to say which species, at which temperature, against which
floor. Pressure is reported for the record only; the janaf table is a temperature table.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from admission import state_range_problems, thermo_ranges  # noqa: E402


def parse_composition(text):
    out = {}
    for item in text.split(','):
        item = item.strip()
        if not item:
            continue
        name, _, value = item.partition('=')
        out[name.strip()] = float(value)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--thermo', required=True, help='case constant/ directory')
    ap.add_argument('--temperature', type=float, required=True)
    ap.add_argument('--pressure', type=float, default=None)
    ap.add_argument('--composition', required=True, help='H2=0.5,O2=0.5')
    ap.add_argument('--json', default=None)
    args = ap.parse_args(argv)

    composition = parse_composition(args.composition)
    ranges = thermo_ranges(args.thermo)
    if not ranges:
        record = {'requested': {'temperature_K': args.temperature,
                                'pressure_Pa': args.pressure,
                                'composition': composition},
                  'verdict': 'unreadable',
                  'reason': 'no janaf ranges readable from %s' % args.thermo}
        print(json.dumps(record, indent=1))
        return 2

    problems = state_range_problems(args.thermo, args.temperature, composition)
    checked = {s: ranges[s] for s in composition if s in ranges}
    record = {
        'requested': {'temperature_K': args.temperature,
                      'pressure_Pa': args.pressure,
                      'composition': composition},
        'thermo_table': {'path': str(Path(args.thermo) / 'thermo.inputData_GRI'),
                         'species': len(ranges)},
        'checked_species': checked,
        'verdict': 'unsupported' if problems else 'supported',
        'problems': problems,
        'note': ('the janaf table is a temperature table; a state below Tlow is clamped by '
                 'the solver at Tlow rather than extrapolated, so a solved field is not a '
                 'solution at the requested temperature'),
    }
    text = json.dumps(record, indent=1, sort_keys=True)
    if args.json:
        Path(args.json).write_text(text + '\n')
    print(text)
    return 3 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
