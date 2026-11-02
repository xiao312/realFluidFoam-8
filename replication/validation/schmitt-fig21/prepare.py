"""Extract only identifiable G2 mean curves from the pinned Figure 21 raster."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
import pymupdf

HERE = Path(__file__).resolve().parent
CAPTION = 'Fig. 21 Flame length. Centerline profiles of a mean axial velocity and b mean (continuous) and rms (dashed) oxygen mass fraction'
URL = 'https://doi.org/10.1007/s10494-019-00096-y'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def affine(value, anchors):
    (p0, v0), (p1, v1) = anchors
    return v0 + (value - p0) * (v1 - v0) / (p1 - p0)


def point(x, y, x_span, y_span, calibration, allowance):
    x_bounds = [affine(x_span[0] - allowance, calibration['x_anchors']),
                affine(x_span[1] + allowance, calibration['x_anchors'])]
    y_bounds = sorted([affine(y_span[0] - allowance, calibration['y_anchors']),
                       affine(y_span[1] + allowance, calibration['y_anchors'])])
    return {'pixel_x': float(x), 'pixel_y': float(y),
            'x_over_d': affine(x, calibration['x_anchors']),
            'value': affine(y, calibration['y_anchors']),
            'x_lower': x_bounds[0], 'x_upper': x_bounds[1],
            'value_lower': y_bounds[0], 'value_upper': y_bounds[1]}


def extract(image, calibration):
    rgb = np.asarray(image.convert('RGB'), dtype=np.int16)
    rule = calibration['blue_classifier']
    blue = ((rgb[:, :, 2] >= rule['minimum_B'])
            & (rgb[:, :, 2] - rgb[:, :, 0] >= rule['minimum_B_minus_R'])
            & (rgb[:, :, 2] - rgb[:, :, 1] >= rule['minimum_B_minus_G']))
    allowance = calibration['pixel_uncertainty']
    velocity, oxygen = [], []
    v, o = calibration['velocity'], calibration['oxygen']
    for x in range(v['columns'][0], v['columns'][1] + 1):
        ys = np.flatnonzero(blue[v['rows'][0]:v['rows'][1] + 1, x]) + v['rows'][0]
        if len(ys):
            velocity.append(point(x, np.median(ys), [x, x], [ys.min(), ys.max()], v, allowance))
    for x in range(o['plateau_columns'][0], o['plateau_columns'][1] + 1):
        ys = np.flatnonzero(blue[o['plateau_rows'][0]:o['plateau_rows'][1] + 1, x]) + o['plateau_rows'][0]
        if len(ys):
            oxygen.append(point(x, np.median(ys), [x, x], [ys.min(), ys.max()], o, allowance))
    for y in range(o['descending_rows'][0], o['descending_rows'][1] + 1):
        xs = np.flatnonzero(blue[y, o['descending_columns'][0]:o['descending_columns'][1] + 1]) + o['descending_columns'][0]
        if not len(xs):
            continue
        # Dashed RMS lies left of the solid mean here. Keep only the rightmost
        # contiguous stroke; the pinned annotated source region makes this auditable.
        cuts = np.flatnonzero(np.diff(xs) > 1)
        xs = xs[cuts[-1] + 1:] if len(cuts) else xs
        oxygen.append(point(np.median(xs), y, [xs.min(), xs.max()], [y, y], o, allowance))
    if len(velocity) < 500 or len(oxygen) < 350:
        raise ValueError('Insufficient clearly classified pixels; inspect the pinned raster and calibration')
    return {'velocity_mean': velocity, 'oxygen_mean': oxygen}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    calibration = json.loads((HERE / 'calibration.json').read_text())
    if sha(args.pdf) != calibration['pdf_sha256']:
        raise ValueError('PDF hash differs from the reviewed Schmitt source')
    with pymupdf.open(args.pdf) as document:
        page = document[calibration['pdf_page_index']]
        if 'Fig. 21' not in page.get_text() or calibration['image_xref'] not in [r[0] for r in page.get_images()]:
            raise ValueError('Pinned Figure 21 image not found on the declared page')
        native = document.extract_image(calibration['image_xref'])['image']
    if hashlib.sha256(native).hexdigest() != calibration['image_sha256']:
        raise ValueError('Native figure image changed')
    image = Image.open(io.BytesIO(native))
    if list(image.size) != calibration['native_size']:
        raise ValueError('Unexpected native figure dimensions')
    curves = extract(image, calibration)
    result = {'schema': 'schmitt-fig21-reference/v1', 'mode': 'applied' if args.apply else 'read-only-plan',
              'paper': {'url': URL, 'caption': CAPTION, 'pdf_page': 22, 'printed_page': 180},
              'calibration': calibration, 'seriesCounts': {k: len(v) for k, v in curves.items()},
              'inputHashes': {str(args.pdf.resolve()): sha(args.pdf)},
              'sourceHashes': {p.name: sha(p) for p in [Path(__file__), HERE / 'calibration.json']},
              'uncertainty': 'Pixel/stroke reading bounds plus two-pixel calibration allowance, not confidence intervals',
              'paper_u0': 'Not numerically or unambiguously defined in supplied text',
              'paper_d': 'Oxygen injector diameter; no numerical value inferred',
              'oxygen_rms': 'unavailable: overlapping dashed blue stroke not reliably separated',
              'scientificAcceptance': False}
    if not args.apply:
        print(json.dumps(result, indent=2)); return
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'original-figure21.jpg').write_bytes(native)
    for name, rows in curves.items():
        with (args.out / (name + '.csv')).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    os.environ.setdefault('MPLCONFIGDIR', str((args.out / 'matplotlib-cache').resolve()))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14.41, 4.23), layout='constrained')
    ax.imshow(image)
    for name, rows in curves.items():
        ax.scatter([p['pixel_x'] for p in rows][::5], [p['pixel_y'] for p in rows][::5], s=5,
                   color='#e97c20', label=name.replace('_', ' '))
    ax.set(xlim=(0, 1440), ylim=(422, 0), xlabel='Native image column', ylabel='Native image row')
    fig.savefig(args.out / 'extraction-overlay.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout='constrained')
    for ax, (name, rows) in zip(axes, curves.items()):
        ax.plot([p['x_over_d'] for p in rows], [p['value'] for p in rows], color='#2659a5', lw=1.6)
        ax.errorbar([p['x_over_d'] for p in rows][::15], [p['value'] for p in rows][::15],
                    xerr=[[p['x_over_d']-p['x_lower'] for p in rows][::15], [p['x_upper']-p['x_over_d'] for p in rows][::15]],
                    yerr=[[p['value']-p['value_lower'] for p in rows][::15], [p['value_upper']-p['value'] for p in rows][::15]],
                    fmt='none', color='#8a98ac', alpha=.55, lw=.7)
        ax.set(xlabel='x/d (paper)', ylabel='Mean ux/u0 (paper)' if name == 'velocity_mean' else 'Mean oxygen mass fraction',
               title='G2 mean velocity' if name == 'velocity_mean' else 'G2 oxygen mean: resolved part only')
        ax.grid(alpha=.18)
    fig.suptitle('Schmitt Figure 21: pixel-extracted means with reading bounds')
    fig.savefig(args.out / 'reference-curves.png', dpi=170); plt.close(fig)
    result['outputHashes'] = {p.name: sha(p) for p in args.out.iterdir() if p.is_file()}
    (args.out / 'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'out': str(args.out), 'seriesCounts': result['seriesCounts'], 'scientificAcceptance': False}))


if __name__ == '__main__':
    main()
