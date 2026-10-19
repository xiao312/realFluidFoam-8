"""Check operational completion without claiming scientific convergence."""
import csv
import json
import math
from pathlib import Path
import re
import sys

job = Path(sys.argv[1])
inputs = json.loads((job/'case-inputs.json').read_text())
rows = list(csv.DictReader((job/'case/processor0/flame-speed.csv').open()))
end = float(inputs['controls']['endTime'])
dt = float(inputs['controls']['deltaT'])
if abs(max(float(r['time_s']) for r in rows)-end) > dt*.1:
    raise ValueError('Segment did not reach requested end time')
for row in rows:
    if row['status'] != 'valid' or not all(math.isfinite(float(row[k])) for k in
            ['x_m', 'rho_unburned', 'rho_local', 'grad_OH', 'speed_m_s']):
        raise ValueError('Missing contour or nonfinite diagnostic')
    if row['stage'] != 'instantaneous_checkpoint' and abs(float(row['delta_t_s'])-dt) > dt*1e-8:
        raise ValueError('Unexpected time step')
log = (job/'solver.log').read_text()
courant = [float(v) for v in re.findall(r'Courant Number mean: [^\n]* max: ([^\s]+)', log)]
if not courant or not all(math.isfinite(v) for v in courant) or max(courant) > .1:
    raise ValueError('Missing or excessive Courant number')
print(json.dumps({'rows': len(rows), 'end_s': end, 'dt_s': dt,
                  'maximum_courant': max(courant), 'scientific_acceptance': False}, indent=2))
