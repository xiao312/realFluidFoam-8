"""Plot saved development profiles and qualified kinematic Figure 12 estimates."""
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

root, snapshot, out = (Path(v).resolve() for v in sys.argv[1:4])
assert snapshot.is_relative_to(root) and out.is_relative_to(root)
out.mkdir(parents=True, exist_ok=True)
os.environ['MPLCONFIGDIR'] = str(root / 'cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

for font in Path('C:/Windows/Fonts').glob('times*.ttf'):
    font_manager.fontManager.addfont(str(font))
plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 10,
                     'mathtext.fontset': 'stix', 'xtick.direction': 'in',
                     'ytick.direction': 'in', 'axes.linewidth': .7})
data = json.loads(snapshot.read_text(encoding='utf-8-sig'))
atlas = root / 'output/figure-comparison-20261017'
x = (np.arange(4000) + .5) * .5e-6
levels = [2e-5, 5e-5, 1e-4]
colors = ['#1864ab', '#e67700']
summary = {'observed_at': data['observed_at'], 'snapshot_sha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(),
           'source_release': '4ae4c078ff3f1b85b7adfd488d6da3c80d5ef979',
           'method': 'Fixed rising-edge OH isolines; linear least-squares front motion; mean rho*(U-v_front)/rho_u over window.',
           'qualification': 'Interim kinematic estimate; not direct discrete Eq.40 evaluation; convergence and seed/mesh/domain independence unproved.',
           'jobs': []}


def marker(fields, level):
    oh = fields['OH']
    peak = int(oh.argmax())
    ids = np.flatnonzero((oh[:peak] < level) & (oh[1:peak+1] >= level))
    if len(ids) != 1:
        raise ValueError('Expected one rising OH crossing before primary peak')
    i = ids[0]
    position = x[i] + (level-oh[i])/(oh[i+1]-oh[i]) * (x[i+1]-x[i])
    return position, np.interp(position, x, fields['U']), np.interp(position, x, fields['rho'])


def estimate(rows, density):
    velocity = np.polyfit(rows[:, 0]-rows[0, 0], rows[:, 1], 1)[0]
    speed = np.mean(rows[:, 3]*(rows[:, 2]-velocity))/density
    return {'start_s': float(rows[0, 0]), 'end_s': float(rows[-1, 0]),
            'front_velocity_m_s': float(velocity), 'speed_cm_s': float(100*speed)}


for job in data['jobs']:
    for sample in job['samples']:
        sample['fields'] = {k: np.asarray(v) for k, v in sample['fields'].items()}
        assert all(a.shape == (4000,) and np.isfinite(a).all() for a in sample['fields'].values())
        assert all((sample['fields'][n] > 0).all() for n in ['T', 'rho', 'p'])
    result = {'job': job['job'], 'time_s': job['samples'][-1]['time_s'],
              'inlet_m_s': job['metadata']['config']['inlet_speed_m_s'],
              'binary_sha256': job['binary_sha256'], 'markers': {}}
    rho_u = job['runtime']['unburned_density_kg_m3']
    job['tracks'] = {}
    for level in levels:
        rows = np.array([[s['time_s'], *marker(s['fields'], level)] for s in job['samples']])
        job['tracks'][level] = rows
        result['markers'][str(level)] = {'50us': estimate(rows[-6:], rho_u), '100us': estimate(rows[-11:], rho_u)}
    last = job['samples'][-1]['fields']
    result['ranges'] = {k: [float(v.min()), float(v.max())] for k, v in last.items()}
    job['result'] = result
    summary['jobs'].append(result)
    # Full-resolution local CSVs retain the actual spatial fields used in plots.
    for sample in job['samples']:
        columns = ['x_m', *sample['fields']]
        values = np.column_stack([x, *sample['fields'].values()])
        np.savetxt(out / f"{job['job']}-{sample['time_s']:.6f}.csv", values, delimiter=',', header=','.join(columns), comments='')


def save(fig, name):
    fig.savefig(out / (name+'.png'), dpi=220, bbox_inches='tight')
    fig.savefig(out / (name+'.svg'), bbox_inches='tight')
    plt.close(fig)


# Independent spatial diagnostics; the paper does not publish these 1-D profiles.
fig, axes = plt.subplots(2, 2, figsize=(9.4, 6.1), constrained_layout=True)
for job, color in zip(data['jobs'], colors):
    sample = job['samples'][-1]; f = sample['fields']
    label = f"Uin={job['result']['inlet_m_s']:.2f} m/s; t={sample['time_s']*1e3:.2f} ms"
    axes[0, 0].plot(x*1e3, f['T'], color=color, label=label)
    axes[0, 1].plot(x*1e3, f['rho'], color=color)
    axes[1, 0].plot(x*1e3, f['U'], color=color)
    axes[1, 1].plot(x*1e3, (f['p']/10132500-1)*100, color=color)
for ax, ylabel in zip(axes.flat, ['Temperature [K]', 'Density [kg/m³]', 'Axial velocity [m/s]', 'Pressure departure [%]']):
    ax.set(xlabel='x [mm]', ylabel=ylabel, xlim=(0, 2))
axes[0, 0].legend(fontsize=8)
fig.suptitle('Single-front CH₄/air, φ=1.10, 100 atm: interim spatial profiles')
save(fig, 'latest-profiles')

fig, axes = plt.subplots(2, 2, figsize=(9.4, 6.1), constrained_layout=True)
for job, color in zip(data['jobs'], colors):
    sample = job['samples'][-1]; f = sample['fields']; xf = marker(f, 5e-5)[0]
    xx = (x-xf)*1e6
    label = f"Uin={job['result']['inlet_m_s']:.2f} m/s"
    axes[0, 0].plot(xx, f['T'], color=color, label=label)
    axes[0, 1].plot(xx, f['OH']*1e4, color=color)
    for species, style in [('CH4', '-'), ('O2', '--'), ('CO2', ':'), ('H2O', '-.')]:
        axes[1, 0].plot(xx, f[species], style, color=color, label=species if job is data['jobs'][0] else None)
    axes[1, 1].plot(xx, f['rho'], color=color)
for ax, ylabel in zip(axes.flat, ['Temperature [K]', 'OH mass fraction ×10⁴', 'Species mass fraction', 'Density [kg/m³]']):
    ax.set(xlabel='x − x(OH=5×10⁻⁵) [µm]', ylabel=ylabel, xlim=(-40, 100))
axes[0, 0].legend(fontsize=8); axes[1, 0].legend(fontsize=8)
fig.suptitle('Front-aligned profiles: latest saved states, not published paper profiles')
save(fig, 'front-aligned-profiles')

# Approximate red-square digitization from the existing inspected paper crop.
crop = atlas / 'originals/2022-fig12.png'
rgb = np.asarray(Image.open(crop).convert('RGB'))
mask = (rgb[:, :, 0] > 170) & (rgb[:, :, 1] < 90) & (rgb[:, :, 2] < 90)
pixels = set(zip(*np.where(mask)))
points = []
while pixels:
    start = pixels.pop(); component = [start]; stack = [start]
    while stack:
        y, xx = stack.pop()
        for p in [(y-1, xx), (y+1, xx), (y, xx-1), (y, xx+1)]:
            if p in pixels:
                pixels.remove(p); component.append(p); stack.append(p)
    if len(component) < 30: continue
    y, xx = np.mean(component, axis=0)
    if not (140 < xx < 550 and 100 < y < 280): continue
    points.append([.85 + (xx-129)/438*.6, 4 + (314-y)/285*4])
points = np.array(sorted(points))
assert points.shape == (11, 2)
ref = points[np.argmin(abs(points[:, 0]-1.1)), 1]
summary['paper_reference'] = {'figure': '2022 Figure 12', 'phi': 1.1, 'speed_cm_s_approx': float(ref),
    'method': 'Red-square centroid from local supplied-PDF crop; inspected pixel axes x=129..567 at phi=.85..1.45, y=314..29 at speed=4..8 cm/s.',
    'qualification': 'Approximate graphic digitization, not author tabulated data; report about 6.8 cm/s.',
    'crop_sha256': hashlib.sha256(crop.read_bytes()).hexdigest()}
np.savetxt(out/'paper-figure12-digitized.csv', points, delimiter=',', header='phi,speed_cm_s_approx', comments='')

fig, ax = plt.subplots(figsize=(6.38, 3.78), constrained_layout=True)
ax.plot(points[:, 0], points[:, 1], 's', color='#d40000', ms=5, label='Paper: approximate red-square digitization')
for job, color, symbol in zip(data['jobs'], colors, ['o', 'x']):
    r = job['result']; speed = r['markers']['5e-05']['50us']['speed_cm_s']
    r['difference_from_paper_percent_approx'] = float((speed/ref-1)*100)
    ax.plot(1.1, speed, symbol, color=color, ms=8, mfc='none', mew=1.5,
            label=f"Interim Uin={r['inlet_m_s']:.2f}: {speed:.2f} cm/s")
ax.set(xlim=(.85, 1.45), ylim=(4, 8), xlabel='Equivalence ratio, φ', ylabel='Laminar flame-speed estimate [cm/s]')
ax.text(.87, 7.77, 'CH₄/air; 100 atm; Tu=298 K', fontsize=10)
ax.legend(loc='lower center', fontsize=8, frameon=False)
save(fig, 'figure12-interim')

fig, ax = plt.subplots(figsize=(7.4, 3.6), constrained_layout=True)
for job, color in zip(data['jobs'], colors):
    rows = job['tracks'][5e-5]; rho_u = job['runtime']['unburned_density_kg_m3']
    rolling = [estimate(rows[i-5:i+1], rho_u) for i in range(5, len(rows)) if np.isclose(rows[i, 0]-rows[i-5, 0], 5e-5)]
    ax.plot([r['end_s']*1e3 for r in rolling], [r['speed_cm_s'] for r in rolling], 'o-', color=color,
            label=f"Uin={job['result']['inlet_m_s']:.2f} m/s")
ax.axhline(ref, color='#d40000', ls='--', label='Paper φ=1.10 ≈6.8 cm/s')
ax.set(xlabel='End of 50 µs fitting window [ms]', ylabel='Density-weighted speed [cm/s]', ylim=(6, 7))
ax.legend(fontsize=8)
save(fig, 'speed-history')
(out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

# Three-page comparison supplement. Original image/caption remain together.
pdf = canvas.Canvas(str(out/'premixed-paper-comparison.pdf'), pagesize=(842, 595))


def picture(path, xx, yy, width, height):
    image = ImageReader(str(path)); iw, ih = image.getSize()
    scale = min(width/iw, height/ih)
    pdf.drawImage(image, xx, yy+height-ih*scale, width=iw*scale, height=ih*scale, mask='auto')


def title(text):
    pdf.setFont('Helvetica-Bold', 15); pdf.drawString(30, 565, text)
    pdf.setFont('Helvetica', 9)


title('2022 Figure 12: interim single-front comparison')
picture(crop, 30, 265, 378, 260)
picture(atlas/'captions/2022-fig12.png', 30, 195, 378, 65)
picture(out/'figure12-interim.png', 434, 265, 378, 260)
lines = [
    'Left: original paper crop and caption. Right: digitized paper points and two interim development estimates.',
    'Both jobs use rfReactingFoam, the renamed upstream baseline, with half unburned / half ideal-gas HP product initialization.',
    'Jobs 124780751 / 124780755; source 4ae4c078ff3f1b85b7adfd488d6da3c80d5ef979; 4000 cells, 0.5 micrometre spacing.',
    'At phi=1.10, both give about 6.33 cm/s versus the paper point of approximately 6.8 cm/s (about 7% lower).',
    'Method: rho/rho_u times (local gas velocity - OH-front velocity), fitted over the latest 50 microseconds.',
    'This is not a direct discrete evaluation of Eq. 40. Mesh/domain/seed independence and final convergence remain unproved.',
    'The paper uses central ignition and two fronts; our inlet/outlet single-front case is a method cross-check.',
    'Only phi=1.10 has a development estimate. The full equivalence-ratio curve is not replicated.'
]
for i, line in enumerate(lines): pdf.drawString(30, 170-i*16, line)
pdf.showPage()
title('Latest saved spatial profiles: ' + ' and '.join(f"{j['result']['time_s']*1e3:.2f} ms" for j in data['jobs']))
picture(out/'latest-profiles.png', 30, 95, 780, 440)
pdf.drawString(30, 65, 'These premixed spatial profiles are diagnostics; the paper does not publish matching 1-D profiles for an overlay.')
pdf.drawString(30, 49, 'Source-field hashes and full-resolution CSVs accompany this report. The newest common checkpoint was excluded during extraction.')
pdf.showPage()
title('Front structure and finite-window sensitivity')
picture(out/'front-aligned-profiles.png', 30, 195, 485, 335)
picture(out/'speed-history.png', 525, 295, 290, 235)
pdf.setFont('Helvetica', 9)
notes = [
    'OH markers: 2e-5, 5e-5 and 1e-4, using the rising edge before the primary OH peak.',
    'A downstream product-relaxation OH crossing exists at 1e-4; it is excluded from flame tracking.',
    'Latest 50-microsecond estimates span about 6.325-6.335 cm/s across both cases and all three markers.',
    'Changing the fitting window to 100 microseconds gives about 6.311-6.325 cm/s.',
    'Agreement between two imposed inlet velocities is encouraging; it does not establish seed independence or steady convergence.',
    'The ideal-gas HP product seed is not SRK fugacity equilibrium. Real-fluid relaxation remains part of the qualification work.',
]
for i, line in enumerate(notes): pdf.drawString(30, 165-i*17, line)
pdf.save()
print(json.dumps(summary, indent=2))
