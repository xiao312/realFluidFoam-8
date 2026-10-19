"""Check operational completion without claiming scientific convergence."""
import csv
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import inspect, scalar, times


def check_progress(log, last_sample, end, dt, interval):
    steps = [float(v) for v in re.findall(r'^Time = ([^\s]+)', log, re.M)]
    if not re.search(r'^End\s*$', log, re.M) or not steps or abs(steps[-1]-end) > dt*.1:
        raise ValueError('Solver did not complete the requested endpoint')
    # OF8 restores the checkpoint time index. Modulo-based output need not
    # fall on the segment endpoint. The log proves completion separately.
    if not -1e-12 <= end-last_sample < interval+1e-12:
        raise ValueError('Diagnostic history does not cover the final output interval')
    courant = [float(v) for v in re.findall(r'Courant Number mean: [^\n]* max: ([^\s]+)', log)]
    if not courant or not all(math.isfinite(v) for v in courant) or max(courant) > .1:
        raise ValueError('Missing or excessive Courant number')
    return max(courant)


def check(job):
    inputs = json.loads((job/'case-inputs.json').read_text())
    case = job/'case'
    rows = list(csv.DictReader((case/'processor0/flame-speed.csv').open()))
    end = float(inputs['controls']['endTime'])
    dt = float(inputs['controls']['deltaT'])
    for row in rows:
        if row['status'] != 'valid' or not all(math.isfinite(float(row[k])) for k in
                ['x_m', 'rho_unburned', 'rho_local', 'grad_OH', 'speed_m_s']):
            raise ValueError('Missing contour or nonfinite diagnostic')
        if row['stage'] != 'instantaneous_checkpoint' and abs(float(row['delta_t_s'])-dt) > dt*1e-8:
            raise ValueError('Unexpected time step')
    last = max(float(r['time_s']) for r in rows)
    courant = check_progress((job/'solver.log').read_text(), last, end, dt,
                             inputs['config']['diagnostic_interval_s'])
    latest = times(case, 8)[-1]
    if not -1e-12 <= end-float(latest) < inputs['config']['field_interval_s']+1e-12:
        raise ValueError('Saved fields do not cover the final output interval')
    fields, _ = inspect(case, 8, latest)
    heat = []
    for rank in range(8):
        heat += scalar(case/f'processor{rank}'/latest/'Qdot', 1000)
    if not all(math.isfinite(q) for q in heat):
        raise ValueError('Nonfinite heat release')
    # Uniform 8000-cell mesh: dx=0.5 um, cross-sectional area=1e-10 m².
    return {'rows': len(rows), 'end_s': end, 'last_diagnostic_s': last, 'dt_s': dt,
            'maximum_courant': courant, 'latest_fields': fields,
            'heat_release': {'saved_time_s': float(latest), 'min_W_m3': min(heat),
                             'max_W_m3': max(heat), 'net_W': sum(heat)*5e-17},
            'scientific_acceptance': False}


if __name__ == '__main__':
    print(json.dumps(check(Path(sys.argv[1])), indent=2))
