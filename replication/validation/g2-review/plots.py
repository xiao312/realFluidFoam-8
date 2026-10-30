"""Plot actual samples and references without smoothing or filling missing cells."""
import numpy as np
import matplotlib.pyplot as plt
from inputs import image_grid


def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12,
        'axes.labelsize': 12, 'axes.titlesize': 13, 'legend.fontsize': 10,
        'lines.linewidth': 1.8, 'lines.markersize': 3.5,
        'axes.spines.top': False, 'axes.spines.right': False, 'savefig.facecolor': 'white'})


def save(fig, out, name):
    fig.savefig(out / (name + '.png'), dpi=180)
    fig.savefig(out / (name + '.svg'))
    plt.close(fig)
    return name


def line_with_gaps(x, y, spacing):
    order = np.argsort(x, kind='stable')
    x, y = np.asarray(x)[order], np.asarray(y)[order]
    if len(x) > 1 and (np.diff(x) <= 0).any():
        raise ValueError('Duplicate or decreasing sampled coordinate')
    px, py = [], []
    for i in range(len(x)):
        if i and x[i] - x[i - 1] > 1.5 * spacing:
            px.append(np.nan); py.append(np.nan)
        px.append(x[i]); py.append(y[i])
    return np.asarray(px), np.asarray(py)


def time_label(record):
    label = f"{record['time_s'] * 1000:g} ms"
    if record['kind'] == 'mean':
        counter = record['averaging']['fields'].get('T')
        label += f"; {counter['accumulatedTime_s'] * 1000:g} ms accumulated" if counter else '; counters unverified'
    return label


def centerline(data, reference, out, origin, label):
    panels = []
    for kind in ('instantaneous', 'mean'):
        records = [r for r in data['records'] if r['kind'] == kind and r['name'] == 'nearAxis']
        if not records:
            continue
        fig, ax = plt.subplots(figsize=(7.2, 5.3))
        fig.subplots_adjust(left=.12, right=.97, top=.86, bottom=.22)
        for name, color, marker in [('fine', '#c25932', 's'), ('finer', '#3164af', 'o')]:
            points = np.asarray(reference['series'][name]['points'])
            x, y = line_with_gaps(points[:, 0], points[:, 1], reference['reading_uncertainty']['x_one_pixel_m'])
            ax.plot(x, y, color=color, alpha=.85, marker=marker, markevery=24,
                    label=f'Paper {name}: time mean')
        colors = plt.cm.viridis(np.linspace(.15, .8, len(records)))
        for record, color in zip(records, colors):
            field = 'TMean' if kind == 'mean' else 'T'
            values = record['fields']
            if 'x' not in values:
                raise ValueError('Near-axis profile requires x coordinate')
            x, y = line_with_gaps(values['x'] - origin, values[field], .1998 / 399)
            ax.plot(x, y, color=color, lw=2.2, label=f'{label}: {time_label(record)}')
        radius = data['observations']['nearAxisRadius_m'] * 1000
        ax.set(xlabel='Axial position (m)', ylabel='Temperature (K)',
               title=f"{'Instantaneous' if kind == 'instantaneous' else 'Running-mean'} near-axis temperature | r = {radius:g} mm")
        ax.grid(alpha=.18)
        ax.set_xlim(min(0, min(r['fields']['x'].min() - origin for r in records)),
                    max(.2, max(r['fields']['x'].max() - origin for r in records)))
        ax.set_ylim(min(0, min(r['fields'][field].min() for r in records)),
                    max(3800, max(r['fields'][field].max() for r in records) * 1.05))
        ax.legend(loc='upper right')
        note = 'Instantaneous diagnostic versus paper means; not an equivalent statistic.' if kind == 'instantaneous' else 'Running means; statistical convergence has not been established.'
        fig.text(.12, .085, note, fontsize=9)
        fig.text(.12, .04, f'Our x_plot = x_mesh - ({origin:g} m); paper coordinates unchanged. No acceptance assigned.', fontsize=9)
        panels.append({'name': save(fig, out, 'axial-' + kind), 'title': ax.get_title(), 'kind': kind})
    return panels


def radial(data, out, origin, label):
    panels = []
    for kind in ('instantaneous', 'mean'):
        records = [r for r in data['records'] if r['kind'] == kind and r['name'].startswith('radial')]
        if not records:
            continue
        temperature, oh = ('TMean', 'OHMean') if kind == 'mean' else ('T', 'OH')
        has_oh = any(oh in r['fields'] for r in records)
        fig, axes = plt.subplots(1, 2 if has_oh else 1, figsize=(10 if has_oh else 6, 4.8), squeeze=False)
        fig.subplots_adjust(left=.10, right=.96, bottom=.24, top=.80, wspace=.35)
        for record in records:
            values = record['fields']
            if 'y' not in values:
                raise ValueError('Radial profile requires y coordinate')
            position = data['observations']['radialPositions_m'][int(record['name'][6:])] - origin
            caption = f"x_plot={position:g} m; {time_label(record)}"
            for axis, field in zip(axes[0], [temperature, oh]):
                if field not in values:
                    continue
                x, y = line_with_gaps(values['y'] * 1000, values[field], .0247 / 199 * 1000)
                axis.plot(x, y, label=caption)
                axis.set(xlabel='Radius (mm)', ylabel='Temperature (K)' if field == temperature else 'OH mass fraction')
                axis.grid(alpha=.18)
                axis.legend(fontsize=8)
        fig.suptitle(f"{label}\nG2 radial profiles | {kind}", fontsize=12)
        fig.text(.08, .065, 'OH is the chemical species mass fraction, not OH* chemiluminescence. No paper radial data inferred.', fontsize=9)
        panels.append({'name': save(fig, out, 'radial-' + kind), 'title': f'Radial profiles: {kind}', 'kind': kind})
    return panels


def maps(data, out, origin, label):
    panels = []
    for record in data['records']:
        if record['geometry'] != 'plane':
            continue
        temperature, oh = ('TMean', 'OHMean') if record['kind'] == 'mean' else ('T', 'OH')
        fields = [name for name in (temperature, oh) if name in record['fields']]
        fig, axes = plt.subplots(len(fields), 1, figsize=(10, 2.2 * len(fields) + 1.2), squeeze=False)
        fig.subplots_adjust(left=.08, right=.88, bottom=.17, top=.83, hspace=.65)
        missing = None
        for axis, field in zip(axes[:, 0], fields):
            x, y, values = image_grid(record['fields'], data['observations'].get('imageGrid'), field)
            missing = int(np.ma.getmaskarray(values).sum())
            color = plt.colormaps['inferno' if field == temperature else 'viridis'].copy()
            color.set_bad('#e7e7e7')
            zero_oh = field == oh and np.all(values.compressed() == 0)
            bounds = {'vmin': 0, 'vmax': 1} if zero_oh else {}
            mesh = axis.pcolormesh((x - origin) * 1000, y * 1000, values, shading='nearest', cmap=color, rasterized=True, **bounds)
            bar = fig.colorbar(mesh, ax=axis, pad=.015, fraction=.025, ticks=[0] if zero_oh else None)
            bar.set_label('T (K)' if field == temperature else 'OH mass fraction')
            if zero_oh:
                bar.ax.set_visible(False)
            axis.set(xlabel='Axial position after explicit offset (mm)', ylabel='Radius (mm)',
                     xlim=((x[0]-origin)*1000, (x[-1]-origin)*1000), ylim=(y[0]*1000, y[-1]*1000))
            if zero_oh:
                axis.set_title('OH mass fraction = 0 at every retained sample', fontsize=10)
        title = f"G2 sampled plane | {record['kind']} | {time_label(record)}"
        fig.suptitle(label + '\n' + title, fontsize=12)
        fig.text(.08, .055, f'{missing} missing grid points remain gray; no interpolation or mirroring. OH is not OH*.', fontsize=9)
        name = f"map-{record['kind']}-{record['time_s']:.9g}"
        panels.append({'name': save(fig, out, name), 'title': title, 'kind': record['kind'], 'masked_points': missing})
    return panels
