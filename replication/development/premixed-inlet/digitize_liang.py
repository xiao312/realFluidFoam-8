"""Extract Liang's black Figure 12 curve from the inspected owner-supplied PDF."""
import hashlib
import json
from pathlib import Path
import sys
import pymupdf
import numpy as np

pdf, output = (Path(v).resolve() for v in sys.argv[1:3])
if output.exists():
    raise ValueError('Refusing existing output: ' + str(output))
document = pymupdf.open(pdf)
page = document[12]
path = page.get_drawings()[521]
assert path['color'] == (0., 0., 0.) and len(path['items']) == 17
assert abs(path['rect'].x0-378.04284668) < .001
points = []
for item in path['items']:
    if item[0] == 'l':
        points.extend([tuple(item[1]), tuple(item[2])])
    elif item[0] == 'c':
        p = np.array([tuple(v) for v in item[1:]])
        for t in np.linspace(0, 1, 101):
            points.append((1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3])
    else:
        raise ValueError('Unexpected vector primitive')
points = np.array(points)
x0, x1, y0, y1 = 357.69073486328125, 532.8677368164062, 175.70819091796875, 61.56732177734375
phi = .85+(points[:, 0]-x0)/(x1-x0)*.6
speed = 4+(y0-points[:, 1])/(y0-y1)*4
assert np.all(np.diff(phi) >= 0) and .919 < phi.min() < .921
rows = []
for integer in range(90, 141, 5):
    v = integer/100
    extrapolated = v < phi.min()
    value = (speed[0]+(v-phi[0])*(np.interp(.95, phi, speed)-speed[0])/(.95-phi[0])
             if extrapolated else np.interp(v, phi, speed))
    rounded = round(float(value), 2)
    rows.append({'key': f'phi-{integer:03d}-liang', 'phi': v, 'speed_cm_s_approx': rounded,
                 'inlet_speed_m_s': rounded/100,
                 'method': 'short secant extrapolation from curve start to phi=0.95' if extrapolated else 'vector-curve interpolation'})
record = {'source': 'Nguyen et al. CPC 273 (2022) 108264, Figure 12 black curve attributed to Liang et al. [52]',
          'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(), 'page': 13,
          'path_index': 521, 'axes_pdf_points': [x0, x1, y0, y1],
          'displayed_phi_range': [float(phi.min()), float(phi.max())],
          'qualification': 'Approximate graphical inlet guesses only; not measured flame speed or author numerical table.',
          'cases': rows}
output.mkdir(parents=True)
(output/'liang-inlets.json').write_text(json.dumps(record, indent=2)+'\n')
np.savetxt(output/'liang-curve.csv', np.column_stack([phi, speed]), delimiter=',', header='phi,speed_cm_s', comments='')
print(json.dumps(record, indent=2))
