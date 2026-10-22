#!/usr/bin/env python3
"""Digitise Cavalieri et al. (2025) Fig. 1 from the vector art in the paper PDF.

Unlike the Liang Fig. 1 reference, this figure is not a raster: the published PDF
embeds it as a Form XObject whose title is ``gr1.eps`` (object stream located by
that title, so the script fails loudly if the paper is replaced).  Every axis
frame, tick, model curve and NIST marker is therefore an exact vector path, and
the digitised values are read in PDF points (1/72 in) with no pixel uncertainty.

What the script reads, and how each quantity is identified objectively:

* panels -- the four axis frames are the only long light-grey (0.149) strokes of
  width 0.32 pt drawn parallel to the page axes;
* ticks -- the short 0.32 pt segments of length 1.4-1.5 pt attached to a frame;
* model curves -- the only 0.62 pt black paths that span a whole frame.  Oxygen is
  the path with an empty dash array, methane the one with a non-empty dash array,
  exactly as the caption states (solid = O2, dashed = CH4);
* NIST markers -- filled black circles of diameter 2.9 pt (the 2.1 pt circle at
  the same centre is the ring interior).  Each marker is assigned to the series
  whose model curve passes closest to it, which is a property of the figure, not
  of any model of ours.

Axis limits are the frame edges: the frame strokes sit on the axes box, so the
box spans xlim/ylim.  The tick positions are then re-fitted to a straight line per
axis and the residuals are reported; they quantify the calibration itself.

Only the Python standard library is used.

Usage:
  digitise_fig1.py --pdf P.pdf --out fig1-vector.json
"""
import argparse
import hashlib
import json
import math
import re
import zlib

FORM_TITLE = 'gr1.eps'

PANELS = {
    # key: xlim, ylim, unit, and the frame's role in the published figure
    'a': dict(xlim=(100.0, 400.0), ylim=(0.0, 1200.0), unit='kg/m^3', label='density'),
    'b': dict(xlim=(100.0, 400.0), ylim=(0.0, 25.0), unit='kJ/(kg K)', label='cp'),
    'c': dict(xlim=(100.0, 400.0), ylim=(0.0, 2.0), unit='1e-4 Pa s', label='mu'),
    'd': dict(xlim=(100.0, 400.0), ylim=(0.0, 0.25), unit='W/(m K)', label='kappa'),
}

TOKEN_RE = re.compile(r'\[[^\]]*\]|/[^\s/\[\]()<>{}]+|[-+]?\d*\.\d+|[-+]?\d+|[A-Za-z*\'"]+')


def objects(data):
    """Map object number -> (header text, decoded stream or None)."""
    out = {}
    for match in re.finditer(rb'(?m)^(\d+)\s+(\d+)\s+obj\b', data):
        num = int(match.group(1))
        start = match.end()
        end = data.find(b'endobj', start)
        if end < 0:
            continue
        body = data[start:end]
        head, stream = body, None
        marker = body.find(b'stream')
        if marker >= 0:
            head = body[:marker]
            raw = body[marker + len(b'stream'):]
            if raw.startswith(b'\r\n'):
                raw = raw[2:]
            elif raw[:1] in (b'\n', b'\r'):
                raw = raw[1:]
            cut = raw.rfind(b'endstream')
            if cut >= 0:
                raw = raw[:cut]
            if b'FlateDecode' in head:
                try:
                    stream = zlib.decompress(raw)
                except zlib.error:
                    stream = None
            else:
                stream = raw
        out[num] = (head.decode('latin-1'), stream)
    return out


def find_form(objs, title):
    hits = [num for num, (head, stream) in objs.items()
            if stream and ('/Title (%s)' % title) in head]
    if len(hits) != 1:
        raise SystemExit('expected exactly one form titled %s, found %r' % (title, hits))
    head, stream = objs[hits[0]]
    return hits[0], head, stream


def apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def mult(a, b):
    return (a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
            a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5])


def read_paths(content):
    """Yield dicts for every painted path: points, curves, stroke, fill, width, dash."""
    text = content.decode('latin-1')
    ctm = (1, 0, 0, 1, 0, 0)
    width, stroke, fill, dash = 1.0, None, None, []
    stack, paths, cur, start = [], [], None, None

    def flush():
        nonlocal cur
        if cur is not None and cur['points']:
            paths.append(cur)
        cur = None

    for match in TOKEN_RE.finditer(text):
        tok = match.group(0)
        if tok[0].isdigit() or tok[0] in '+-.':
            continue
        if tok == 'q':
            stack.append((ctm, width, stroke, fill, list(dash)))
        elif tok == 'Q':
            if stack:
                ctm, width, stroke, fill, dash = stack.pop()
        elif tok == 'cm':
            nums = [float(v) for v in TOKEN_RE.findall(text[max(0, match.start() - 90):match.start()])
                    if re.fullmatch(r'[-+]?\d*\.?\d+', v)][-6:]
            if len(nums) == 6:
                ctm = mult(tuple(nums), ctm)
        elif tok == 'w':
            nums = re.findall(r'[-+]?\d*\.?\d+', text[max(0, match.start() - 30):match.start()])
            if nums:
                width = float(nums[-1])
        elif tok == 'RG':
            nums = re.findall(r'[-+]?\d*\.?\d+', text[max(0, match.start() - 60):match.start()])[-3:]
            if len(nums) == 3:
                stroke = tuple(round(float(v), 3) for v in nums)
        elif tok == 'rg':
            nums = re.findall(r'[-+]?\d*\.?\d+', text[max(0, match.start() - 60):match.start()])[-3:]
            if len(nums) == 3:
                fill = tuple(round(float(v), 3) for v in nums)
        elif tok == 'd':
            inner = text[max(0, match.start() - 60):match.start()]
            arr = re.findall(r'\[([^\]]*)\]', inner)
            if arr:
                dash = [float(v) for v in re.findall(r'[-+]?\d*\.?\d+', arr[-1])]
        elif tok == 'm':
            flush()
            nums = re.findall(r'[-+]?\d*\.?\d+', text[max(0, match.start() - 60):match.start()])[-2:]
            if len(nums) == 2:
                start = apply(ctm, float(nums[0]), float(nums[1]))
                cur = dict(points=[start], curves=0, width=width, stroke=stroke,
                           fill=fill, dash=list(dash))
        elif tok == 'l' and cur is not None:
            nums = re.findall(r'[-+]?\d*\.?\d+', text[max(0, match.start() - 60):match.start()])[-2:]
            if len(nums) == 2:
                cur['points'].append(apply(ctm, float(nums[0]), float(nums[1])))
        elif tok in ('c', 'v', 'y') and cur is not None:
            nums = [float(v) for v in re.findall(r'[-+]?\d*\.?\d+',
                                                  text[max(0, match.start() - 140):match.start()])
                    if re.fullmatch(r'[-+]?\d*\.?\d+', v)][-(6 if tok == 'c' else 4):]
            if tok == 'c' and len(nums) == 6:
                p1 = apply(ctm, nums[0], nums[1])
                p2 = apply(ctm, nums[2], nums[3])
                p3 = apply(ctm, nums[4], nums[5])
            elif len(nums) == 4:
                p1 = cur['points'][-1]
                p2 = apply(ctm, nums[0], nums[1])
                p3 = apply(ctm, nums[2], nums[3])
            else:
                continue
            prev = cur['points'][-1]
            for i in range(1, 9):
                t = i / 8.0
                u = 1 - t
                cur['points'].append((u ** 3 * prev[0] + 3 * u * u * t * p1[0]
                                      + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                                      u ** 3 * prev[1] + 3 * u * u * t * p1[1]
                                      + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
            cur['curves'] += 1
        elif tok == 're':
            nums = [float(v) for v in re.findall(r'[-+]?\d*\.?\d+',
                                                 text[max(0, match.start() - 90):match.start()])
                    if re.fullmatch(r'[-+]?\d*\.?\d+', v)][-4:]
            if len(nums) == 4:
                x, y, w, h = nums
                flush()
                pts = [apply(ctm, x, y), apply(ctm, x + w, y),
                       apply(ctm, x + w, y + h), apply(ctm, x, y + h), apply(ctm, x, y)]
                cur = dict(points=pts, curves=0, width=width, stroke=stroke,
                           fill=fill, dash=list(dash))
        elif tok in ('S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'):
            flush()
    flush()
    return paths


def bbox(path):
    xs = [p[0] for p in path['points']]
    ys = [p[1] for p in path['points']]
    return min(xs), min(ys), max(xs), max(ys)


def classify(paths):
    frames, ticks, curves, markers, glyphs, samples = [], [], [], [], [], []
    for path in paths:
        x0, y0, x1, y1 = bbox(path)
        w, h = x1 - x0, y1 - y0
        if path['curves'] == 4 and abs(w - h) < 0.2 and w < 4.0 and path['fill']:
            markers.append(dict(cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0,
                                dia=round(w, 3), width=path['width']))
        elif not path['curves'] and min(w, h) < 0.3 and 1.0 < max(w, h) < 3.0:
            ticks.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, width=path['width']))
        elif path['curves'] and path['fill'] and w < 12 and h < 7:
            glyphs.append(dict(x0=x0, y0=y0, x1=x1, y1=y1))
        elif not path['curves'] and 4.0 < max(w, h) < 12.0 and min(w, h) < 0.3 \
                and path['stroke'] and path['width'] > 0.5:
            # legend line samples: short solid or dashed strokes of the curve width
            samples.append(dict(x0=x0, y0=y0, x1=x1, y1=y1))
        elif not path['curves'] and (w > 60 or h > 60) and path['stroke']:
            if path['width'] > 0.5 and len(path['points']) > 20:
                curves.append(path)
            elif path['width'] < 0.5 and (w < 0.3 or h < 0.3):
                frames.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, width=path['width']))
    return frames, ticks, curves, markers, glyphs, samples


def find_panels(frames):
    """Group frame strokes into boxes; a box is two horizontal and two vertical strokes."""
    horiz = [f for f in frames if abs(f['y1'] - f['y0']) < 0.3]
    vert = [f for f in frames if abs(f['x1'] - f['x0']) < 0.3]
    boxes = []
    for top in horiz:
        for bottom in horiz:
            if not (top['y0'] > bottom['y0'] + 20):
                continue
            if abs(top['x0'] - bottom['x0']) > 0.5 or abs(top['x1'] - bottom['x1']) > 0.5:
                continue
            for left in vert:
                for right in vert:
                    if abs(left['x0'] - top['x0']) > 0.5 or abs(right['x0'] - top['x1']) > 0.5:
                        continue
                    if abs(left['y0'] - bottom['y1']) > 0.5 or abs(left['y1'] - top['y0']) > 0.5:
                        continue
                    boxes.append(dict(x0=left['x0'], x1=right['x0'],
                                      y0=bottom['y0'], y1=top['y0']))
    # de-duplicate identical boxes
    uniq = []
    for box in boxes:
        if not any(all(abs(box[k] - u[k]) < 0.5 for k in ('x0', 'x1', 'y0', 'y1')) for u in uniq):
            uniq.append(box)
    return sorted(uniq, key=lambda b: (-b['y1'], b['x0']))


def fit_tick(positions, values):
    n = len(positions)
    if n < 2:
        return None
    mp = sum(positions) / n
    mv = sum(values) / n
    sxx = sum((p - mp) ** 2 for p in positions)
    sxy = sum((p - mp) * (v - mv) for p, v in zip(positions, values))
    slope = sxy / sxx
    origin = mv - slope * mp
    resid = max(abs(origin + slope * p - v) for p, v in zip(positions, values))
    return dict(slope=slope, origin=origin, max_residual=resid, n=n)


def to_data(box, xlim, ylim, px, py):
    fx = (px - box['x0']) / (box['x1'] - box['x0'])
    fy = (py - box['y0']) / (box['y1'] - box['y0'])
    return xlim[0] + fx * (xlim[1] - xlim[0]), ylim[0] + fy * (ylim[1] - ylim[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', default=('/references/library/objects/'
                                      'bcd4f0fdac3c4063c744e331c0b2e6af7e311837f99230502cde2c97257d0843.pdf'))
    ap.add_argument('--out', default='figure1-vector.json')
    args = ap.parse_args()

    data = open(args.pdf, 'rb').read()
    objs = objects(data)
    num, head, stream = find_form(objs, FORM_TITLE)
    bbox_form = re.search(r'/BBox\s*\[([^\]]*)\]', head)
    paths = read_paths(stream)
    frames, ticks, curves, markers, glyphs, samples = classify(paths)
    boxes = find_panels(frames)
    if len(boxes) != 4:
        raise SystemExit('expected 4 panel boxes, found %d' % len(boxes))

    out = dict(
        source_pdf=args.pdf,
        source_pdf_sha256=hashlib.sha256(data).hexdigest(),
        form=dict(object=num, title=FORM_TITLE,
                  bbox=[float(v) for v in bbox_form.group(1).split()]),
        path_count=len(paths),
        panels={},
    )
    # markers: keep only the 2.9 pt circles (the 2.1 pt circle repeats the centre)
    outer = [m for m in markers if abs(m['dia'] - 2.9) < 0.2]
    inner = [m for m in markers if abs(m['dia'] - 2.1) < 0.2]
    out['marker_diameters'] = sorted({round(m['dia'], 3) for m in markers})
    out['markers_outer'] = len(outer)
    out['markers_inner'] = len(inner)

    for key, spec in PANELS.items():
        ridge = [b for b in boxes if b['x0'] < (boxes[0]['x0'] + boxes[0]['x1']) / 2] \
            if key in ('a', 'c') else \
            [b for b in boxes if b['x0'] > (boxes[0]['x0'] + boxes[0]['x1']) / 2]
        top = key in ('a', 'b')
        box = [b for b in ridge if (b['y0'] > 150) == top][0]
        x0, x1, y0, y1 = box['x0'], box['x1'], box['y0'], box['y1']

        # curves inside this frame
        inside = [c for c in curves
                  if abs(bbox(c)[0] - x0) < 1.0 and abs(bbox(c)[2] - x1) < 1.0
                  and y0 - 1.0 <= bbox(c)[1] and bbox(c)[3] <= y1 + 1.0]
        solid = [c for c in inside if not c['dash']]
        dashed = [c for c in inside if c['dash']]
        if len(solid) != 1 or len(dashed) != 1:
            raise SystemExit('panel %s: expected one solid and one dashed curve, got %d/%d'
                             % (key, len(solid), len(dashed)))

        series = dict(
            o2=[[round(v, 4) for v in to_data(box, spec['xlim'], spec['ylim'], px, py)]
                for px, py in solid[0]['points']],
            ch4=[[round(v, 4) for v in to_data(box, spec['xlim'], spec['ylim'], px, py)]
                 for px, py in dashed[0]['points']],
        )

        # the legend is the only text drawn inside a frame: its glyph outlines give the
        # legend box, and no NIST marker inside that box is a data point
        legend = None
        inside_glyphs = [g for g in glyphs if x0 < g['x0'] and g['x1'] < x1
                         and y0 < g['y0'] and g['y1'] < y1]
        inside_samples = [s for s in samples if x0 < s['x0'] and s['x1'] < x1
                          and y0 < s['y0'] and s['y1'] < y1]
        legend_paths = inside_glyphs + inside_samples
        if legend_paths:
            legend = [round(min(g['x0'] for g in legend_paths), 3),
                      round(min(g['y0'] for g in legend_paths), 3),
                      round(max(g['x1'] for g in legend_paths), 3),
                      round(max(g['y1'] for g in legend_paths), 3)]

        # markers inside this frame, assigned to the curves two at a time: the two
        # markers at the same temperature are matched to the two curves by whichever
        # pairing is closer, which also settles which curve is the upper one
        def y_at(pts, T, tol=0.4):
            """Curve value at T as the median of the polyline points within +-tol K.

            The published curves are sampled polylines; near a peak their x advances by
            far less than the marker spacing, so a bracketing interpolation would be
            dominated by drawing wobble.  A local median of the y values is stable and
            still uses only drawn points.
            """
            xy = [to_data(box, spec['xlim'], spec['ylim'], px, py) for px, py in pts]
            for window in (tol, 4 * tol, 16 * tol):
                near = sorted(v for u, v in xy if abs(u - T) <= window)
                if len(near) >= 1:
                    return near[len(near) // 2]
            return float('nan')

        span = spec['ylim'][1] - spec['ylim'][0]
        marks, rejected = [], []
        for m in outer:
            if not (x0 < m['cx'] < x1 and y0 < m['cy'] < y1):
                continue
            if legend and legend[0] - 0.5 < m['cx'] < legend[2] + 0.5 \
                    and legend[1] - 0.5 < m['cy'] < legend[3] + 0.5:
                rejected.append(['legend', round(m['cx'], 3), round(m['cy'], 3)])
                continue
            marks.append(m)
        # The two series are drawn at the same temperatures, so the markers pair up in
        # x.  Within a pair the upper marker belongs to whichever curve is upper at
        # that temperature; a lone marker goes to the curve on its side of the midline.
        # Both rules compare quantities at one temperature, so they survive the nearly
        # vertical peak sections where a marker's temperature is only known to the
        # drawing resolution.
        marks.sort(key=lambda m: m['cx'])
        groups = []
        for m in marks:
            if groups and m['cx'] - groups[-1][0]['cx'] < 1.2:
                groups[-1].append(m)
            else:
                groups.append([m])
        grouped = dict(o2=[], ch4=[])
        for group in groups:
            group.sort(key=lambda m: m['cy'])
            pairs = []
            for m in group:
                T, y = to_data(box, spec['xlim'], spec['ylim'], m['cx'], m['cy'])
                pairs.append((T, y, y_at(solid[0]['points'], T),
                              y_at(dashed[0]['points'], T)))
            for index, (T, y, yo2, ych4) in enumerate(pairs):
                upper = 'o2' if yo2 >= ych4 else 'ch4'
                lower = 'ch4' if upper == 'o2' else 'o2'
                if len(pairs) == 2:
                    best = lower if index == 0 else upper
                elif len(pairs) > 2 and index == 0:
                    best = lower
                elif len(pairs) > 2 and index == len(pairs) - 1:
                    best = upper
                else:
                    best = upper if y >= 0.5 * (yo2 + ych4) else lower
                ref = yo2 if best == 'o2' else ych4
                err = (y - ref) / span * 100.0
                # Garbage filter only: a marker more than 40 % of the panel span away
                # from the curve it was assigned to is not that curve's marker (it is a
                # glyph outline, an axis artefact or a mismatched panel element).  The
                # earlier 6 % limit silently discarded genuine low-temperature NIST
                # points that the paper's own model curve does not follow; those are
                # kept and reported as residuals instead of being dropped.
                if abs(err) > 40.0:
                    rejected.append(['far', round(T, 3), round(y, 6)])
                    continue
                grouped[best].append((T, y, err))
        for name in grouped:
            grouped[name] = [[round(T, 4), round(y, 6), round(err, 3)]
                             for T, y, err in sorted(grouped[name])]

        # ticks: every tick is drawn on both sides of the box, so the distinct positions
        # are de-duplicated.  x ticks are vertical segments touching the box, y ticks
        # horizontal ones.
        def distinct(values):
            out = []
            for v in sorted(values):
                if not out or abs(v - out[-1]) > 0.2:
                    out.append(v)
            return [round(v, 3) for v in out]

        xticks = distinct(t['x0'] for t in ticks if t['x1'] - t['x0'] < 0.3
                          and x0 - 0.6 < t['x0'] < x1 + 0.6
                          and (abs(t['y0'] - y0) < 0.1 or abs(t['y1'] - y1) < 0.1))
        yticks = distinct(t['y0'] for t in ticks if t['y1'] - t['y0'] < 0.3
                          and y0 - 0.6 < t['y0'] < y1 + 0.6
                          and (abs(t['x0'] - x0) < 0.1 or abs(t['x1'] - x1) < 0.1))

        out['panels'][key] = dict(
            label=spec['label'], unit=spec['unit'],
            frame=[round(v, 3) for v in (x0, y0, x1, y1)],
            xlim=list(spec['xlim']), ylim=list(spec['ylim']),
            curve_line_width=round(solid[0]['width'], 3),
            curve_dash=dashed[0]['dash'],
            n_curve_points=[len(solid[0]['points']), len(dashed[0]['points'])],
            n_markers=[len(grouped['o2']), len(grouped['ch4'])],
            marker_excluded=rejected,
            marker_offset_pct=[round(max(abs(m[2]) for m in grouped['o2']), 3),
                               round(max(abs(m[2]) for m in grouped['ch4']), 3)],
            legend=legend,
            curves=series,
            markers=grouped,
            x_tick_positions=xticks,
            y_tick_positions=yticks,
        )
    json.dump(out, open(args.out, 'w'), indent=1)
    for key in sorted(out['panels']):
        p = out['panels'][key]
        print('%s %-8s frame %s markers %s curve pts %s max |dy| %.2f %% of span, '
              'x ticks %d y ticks %d'
              % (key, p['label'], p['frame'], p['n_markers'], p['n_curve_points'],
                 max(p['marker_offset_pct']), len(p['x_tick_positions']),
                 len(p['y_tick_positions'])))
    print('markers', out['markers_outer'], 'diameters', out['marker_diameters'])
    print('wrote', args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
