"""Fast diagnostic failure signal on complete recorded solver rows."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics

LEVELS = (1e-5, 2e-5, 3e-5)
STAGES = ('integrated_species_solve', 'instantaneous_end_step')


def load(path):
    raw = path.read_bytes()
    end = raw.rfind(b'\n') + 1
    rows = list(csv.DictReader(raw[:end].decode().splitlines()))
    if not rows or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError('Missing or incomplete CSV rows')
    return rows


def evaluate(rows, end=None, window=5e-6, tolerance=.5):
    end = end if end is not None else max(float(r['time_s']) for r in rows)
    start = end - window
    medians = {}
    for side in ('left', 'right'):
        for stage in STAGES:
            for level in LEVELS:
                selected = [r for r in rows if r['side'] == side and r['stage'] == stage
                            and abs(float(r['OH_level'])-level) < 1e-15
                            and start-1e-12 <= float(r['time_s']) <= end+1e-12]
                if len(selected) < 3 or any(r['status'] != 'valid' for r in selected):
                    raise ValueError('Insufficient valid contour history')
                values = [float(r['speed_m_s'])*100 for r in selected]
                if not all(math.isfinite(v) for v in values):
                    raise ValueError('Nonfinite speed')
                medians[(side, stage, level)] = statistics.median(values)
    spread = max(max(medians[s, stage, level] for level in LEVELS)
                 - min(medians[s, stage, level] for level in LEVELS)
                 for s in ('left', 'right') for stage in STAGES)
    gap = max(abs(medians[s, STAGES[0], level]-medians[s, STAGES[1], level])
              for s in ('left', 'right') for level in LEVELS)
    return {'status': 'PASS' if max(spread, gap) <= tolerance else 'UNRESOLVED',
            'window_s': [start, end], 'tolerance_cm_s': tolerance,
            'max_marker_spread_cm_s': spread, 'max_source_stage_gap_cm_s': gap,
            'median_speeds_cm_s': {'|'.join(map(str, k)): v for k, v in medians.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--end-us', type=float)
    args = parser.parse_args()
    result = evaluate(load(args.csv), None if args.end_us is None else args.end_us*1e-6)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 2)
