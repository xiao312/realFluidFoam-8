"""Instantaneous comparisons; never synthesize statistics or missing samples."""
import numpy as np
import matplotlib.pyplot as plt

from inputs import image_grid
from plots import save, line_with_gaps


def radial(data, references, out, origin):
    records = [r for r in data['records'] if r['kind'] == 'instantaneous' and r['name'].startswith('radial')]
    panels, missing = [], []
    for station in (15, 45, 70):
        matches = [r for r in records if abs(1000 * (data['observations']['radialPositions_m'][int(r['name'][6:])] - origin) - station) < 1e-6]
        if not matches:
            missing.append(f'Cavalieri {station} mm: no actual sample at the matched station')
            continue
        fig, ax = plt.subplots(figsize=(7.1, 5.2))
        fig.subplots_adjust(left=.12, right=.97, top=.86, bottom=.24)
        for grid, color, dash in [('M1', '#ababab', ':'), ('M2', '#b17b43', '--'), ('M3', '#356597', '-')]:
            curves = [c for c in references['curves'] if c['station_mm'] == station and c['statistic'] == 'mean' and c['grid'] == grid]
            if len(curves) != 1:
                raise ValueError(f'Missing or duplicate paper curve at {station} mm / {grid}')
            curve = curves[0]
            ax.plot(curve['radial_mm'], curve['temperature_K'], color=color, ls=dash,
                    lw=1.6, label=f'Paper {grid}: temporal mean')
        for record, color in zip(matches, plt.cm.viridis(np.linspace(.12, .72, len(matches)))):
            fields = record['fields']
            if 'y' not in fields:
                raise ValueError('Radial CFD profile needs its actual y coordinate')
            x, y = line_with_gaps(fields['y'] * 1000, fields['T'], .0247 / 199 * 1000)
            ax.plot(x, y, color=color, lw=2.2, label=f"Our instant: {record['time_s'] * 1e6:g} microseconds")
        upper = max(2200, max(float(r['fields']['T'].max()) for r in matches) * 1.07)
        ax.set(xlabel='Radius (mm)', ylabel='Temperature (K)', xlim=(0, 25), ylim=(0, upper),
               title=f'Cavalieri Fig. 6 | x = {station} mm from exit')
        ax.grid(alpha=.17); ax.legend(fontsize=9, loc='best')
        fig.text(.12, .10, 'PRELIMINARY: our instantaneous startup fields versus paper temporal means.', fontsize=9)
        fig.text(.12, .055, 'Paper statistics span 60 ms. No CFD RMS or statistical acceptance inferred.', fontsize=9)
        name = save(fig, out, f'cavalieri-{station}mm')
        panels.append({'name': name, 'title': f'Radial temperature at {station} mm',
                       'reference': 'cavalieri2025-fig-6', 'meaning': 'Different statistics: instantaneous startup versus temporal mean.'})
    return panels, missing


def maps(data, out, origin, proxies):
    panels = []
    missing = []
    common_bounds = {}
    for record in data['records']:
        if record['kind'] != 'instantaneous' or record['geometry'] != 'plane':
            continue
        available = {name: record['fields'][name] for name in ('T', 'rho', 'OH') if name in record['fields']}
        if record['time_s'] in proxies:
            available['cOHstar_LTE_proxy_mol_m3'] = proxies[record['time_s']]['cOHstar_LTE_proxy_mol_m3']
        for name, values in available.items():
            previous = common_bounds.get(name, (float('inf'), -float('inf')))
            common_bounds[name] = (min(previous[0], float(values.min())), max(previous[1], float(values.max())))
    for record in data['records']:
        if record['kind'] != 'instantaneous' or record['geometry'] != 'plane':
            continue
        fields = record['fields']
        for field, unit, cmap in [('T', 'Temperature (K)', 'inferno'),
                                  ('rho', 'Density (kg/m³)', 'cividis'),
                                  ('OH', 'Ground-state OH mass fraction', 'viridis')]:
            if field not in fields:
                missing.append(f"{field}: absent at {record['time_s']:g} s")
                continue
            panels.append(map_panel(data, record, fields, field, unit, cmap, out, origin, common_bounds[field]))
        if record['time_s'] in proxies:
            panels.append(map_panel(data, record, proxies[record['time_s']], 'cOHstar_LTE_proxy_mol_m3',
                                    '308 nm LTE population proxy (mol/m³)', 'magma', out, origin, common_bounds['cOHstar_LTE_proxy_mol_m3']))
    return panels, missing


def map_panel(data, record, fields, field, unit, cmap, out, origin, shared_bounds):
    x, y, values = image_grid(fields, data['observations']['imageGrid'], field)
    finite = values.compressed()
    if not finite.size:
        raise ValueError('Map contains no retained fluid points')
    lower, upper = float(finite.min()), float(finite.max())
    if shared_bounds[0] == shared_bounds[1]:
        delta = max(abs(shared_bounds[0])*.01, 1e-12)
        bounds = (shared_bounds[0]-delta, shared_bounds[1]+delta)
    else:
        bounds = shared_bounds
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.6), gridspec_kw={'height_ratios': [1, 1.6]})
    fig.subplots_adjust(left=.08, right=.87, top=.82, bottom=.16, hspace=.58)
    color = plt.colormaps[cmap].copy(); color.set_bad('#e6e6e6')
    for axis, limits, heading in zip(axes, [(0, 200), (0, 30)], ['Whole chamber sample', 'Injector region: 0–30 mm']):
        mesh = axis.pcolormesh((x-origin)*1000, y*1000, values, shading='nearest',
                               vmin=bounds[0], vmax=bounds[1], cmap=color, rasterized=True)
        axis.set(xlabel='Axial distance from explicit exit origin (mm)', ylabel='Radius (mm)',
                 xlim=limits, ylim=(0, 25), title=heading)
    color_axis = fig.add_axes([.9, .20, .018, .53])
    fig.colorbar(mesh, cax=color_axis).set_label(unit)
    if shared_bounds[0] == shared_bounds[1]:
        color_axis.set_yticks([shared_bounds[0]])
    when = record['time_s']*1e6
    fig.suptitle(f'{unit} | instantaneous {when:g} microseconds\nPRELIMINARY STARTUP: no statistical or optical acceptance', fontsize=13)
    missing = int(np.ma.getmaskarray(values).sum())
    fig.text(.08, .075, f"{values.shape[1]} × {values.shape[0]} points; {missing} missing remain gray. Shared scale across times; no interpolation/reflection.", fontsize=9)
    note = 'LTE thermal population approximation only; no line-of-sight integration or radiative calibration.' if field.startswith('cOHstar') else 'Ground-state OH is not OH* emission. The plotted fields are instantaneous, not time means.'
    fig.text(.08, .035, note, fontsize=9)
    name = save(fig, out, f'map-{field}-{record["time_s"]:.9g}')
    return {'name': name, 'title': f'{unit} at {when:g} microseconds',
            'reference': 'singla2005-fig4cd-g2-ohstar' if field.startswith('cOHstar') else ('sharma2023-fig-9' if field == 'OH' else None),
            'meaning': note, 'time_s': record['time_s'], 'field': field, 'min': lower, 'max': upper,
            'shared_color_limits': list(bounds),
            'sampled_points': int(finite.size), 'masked_points': missing}
