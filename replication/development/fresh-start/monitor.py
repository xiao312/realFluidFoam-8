"""Read-only progress and Qdot monitoring for original-zero 1D flames."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import scalar, times


def contained(path, root):
    path = path.resolve(strict=True)
    path.relative_to(root)
    return path


def heat_release(case):
    """Integrate only the explicitly qualified, uniform one-dimensional mesh."""
    mesh = (case/'system/blockMeshDict').read_text()
    compact = re.sub(r'\s+', '', mesh)
    required = ['convertToMeters1;', '(800011)simpleGrading(111)',
                'vertices((000)(0.00400)(0.0040.000010)(00.000010)',
                '(000.00001)(0.00400.00001)(0.0040.000010.00001)(00.000010.00001))']
    if not all(token in compact for token in required):
        raise ValueError('Heat-release integral requires the declared 4-mm uniform mesh')
    counts = []
    for rank in range(8):
        address = (case/f'processor{rank}/constant/polyMesh/cellProcAddressing').read_text()
        counts.append(int(re.search(r'\n\s*(\d+)\s*\(', address)[1]))
    if sum(counts) != 8000:
        raise ValueError('Expected exactly 8000 cells')
    results, incomplete = [], []
    for time in times(case, 8):
        if float(time) <= 0:
            continue
        values = []
        try:
            for rank, count in enumerate(counts):
                path = case/f'processor{rank}'/time/'Qdot'
                before = path.stat()
                field = scalar(path, count)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError('Field changed while being read')
                values.extend(field)
            if not all(math.isfinite(v) for v in values):
                raise ValueError('Nonfinite Qdot')
            results.append(dict(time_s=float(time), minimum_W_m3=min(values),
                                maximum_W_m3=max(values), integral_W_m2=math.fsum(values)*0.004/8000))
        except (OSError, ValueError) as error:
            incomplete.append(dict(time_s=float(time), error=str(error)))
    return dict(saved=results, incomplete=incomplete,
                mesh_sha256=hashlib.sha256(mesh.encode()).hexdigest(), fronts=2)


def tracking(case):
    path = case/'processor0/front-tracking.csv'
    raw = path.read_bytes()
    # A live append can leave the final line incomplete; do not parse that line.
    complete = raw[:raw.rfind(b'\n')+1].decode()
    rows = list(csv.DictReader(complete.splitlines()))
    if not rows:
        raise ValueError('No complete tracking records')
    first, last = float(rows[0]['time_s']), float(rows[-1]['time_s'])
    primary = []
    for row in reversed(rows):
        if float(row['time_s']) != last:
            break
        if row['primary'] != '1':
            continue
        speed = float(row['density_weighted_m_s'])
        primary.append(dict(side=row['side'], marker=row['marker'], status=row['status'],
                            speed_cm_s=100*speed if math.isfinite(speed) else None))
    return dict(first_time_s=first, latest_time_s=last, original_zero_verified=first == 0,
                primary=primary, complete_csv_sha256=hashlib.sha256(complete.encode()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('jobs', nargs='+')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if any(not job.isdigit() for job in args.jobs):
        raise ValueError('Job identifiers must be numeric')
    raw = subprocess.check_output(['sacct', '-n', '-X', '-P', '-j', ','.join(args.jobs),
                                   '-o', 'JobIDRaw,State,Elapsed,ExitCode'], text=True)
    states = {line.split('|')[0]: line.split('|')[1:4] for line in raw.splitlines()}
    results = []
    for identifier in args.jobs:
        result = dict(job=identifier, scheduler=states.get(identifier, ['UNKNOWN']))
        try:
            case = contained(root/'jobs'/identifier/'case', root)
            result['tracking'] = tracking(case)
            result['heat_release'] = heat_release(case)
        except (OSError, ValueError) as error:
            result['error'] = str(error)
        results.append(result)
    print(json.dumps(dict(observed_utc=datetime.now(timezone.utc).isoformat(), jobs=results), indent=2))


if __name__ == '__main__':
    main()
