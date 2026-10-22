#!/usr/bin/env python3
"""Digitise Liang et al. (2019) Fig. 8(a) from the pinned raster crop.

Figure 8(a) is a raster panel, so every reference number here is a pixel
measurement.  The steps are recorded separately and none of them invents a point:

* frame detection -- the plot box is the longest dark row/column pair;
* axis calibration -- the five *major* x ticks and the seven *major* y ticks are
  detected from their tick strokes (the shorter minor ticks are rejected by stroke
  length), fitted by least squares, and reported with residuals;
* symbol reading -- the red (Case 3) and blue (Case 4) triangles are connected
  components of their own colour masks, the black (Case 2) diamonds are columns
  whose dark run through the curve is thicker than the 3-4 px Case-1 line and that
  sit on the traced Case-1 curve;
* curve tracing -- the Case-1 (black) and Case-5 (blue) lines are thinned to a 1 px
  ridge (Zhang-Suen), walked as an ordered path and read column by column, after the
  axis bands, the legend box, the panel title and the symbol rims are removed.

The reference identity is the crop supplied by the campaign library
(``library/objects/7b3a27b0...png``, 612x525, ``crop_pt [28, 50, 232, 225]`` of
PDF page 6).  It is a *crop of the paper*, not author data.  Only the Python
standard library is used.

    python3 digitize_fig8a.py <raster.rgba> <figure8a-reference.json>
"""
import argparse
import hashlib
import json
import os
import sys

PAPER_SHA = '24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe'
PAGE_INDEX = 5            # 0-based PDF page index of Fig. 8
CROP_PT = [28.0, 50.0, 232.0, 225.0]
RASTER_PX = [612, 525]    # 3x the crop box
TITLE_ROWS = 70           # the panel title "Methane/Air 100 atm" ends above top+70
BOTTOM_ROWS = 60          # the curve never goes below bottom-60; this also clears the minor ticks
AXIS_BAND = 12            # inward tick strokes are 9 px, so 12 px clears them

# Legend rows of Fig. 8(a): the Case-1 line sample, the Case-2 diamond, the Case-3
# and Case-4 symbols and the Case-5 line sample.  Nothing inside this box is data.
# The legend block (line sample, symbols and the five labels) spans x 140-487, y 288-415,
# but the tail of the longest label only reaches x~482 while the curves stay above y=290
# for x<470 and above y=360 for x<487, so two boxes cover the text without covering data.
LEGEND_BOXES = [[140, 288, 470, 415], [470, 360, 487, 415]]

SAMPLE_PHI = [round(0.95 + 0.01 * i, 2) for i in range(46)]     # 0.95 ... 1.40


def load_raw(path):
    raw = open(path, 'rb').read()
    end = raw.index(b'\n') + 1
    header = json.loads(raw[:end].decode('utf8'))
    width, height = int(header['width']), int(header['height'])
    pixels = raw[end:]
    if len(pixels) != width * height * 4:
        raise ValueError('unexpected raw payload: %d bytes for %dx%d' % (len(pixels), width, height))
    return width, height, pixels


def classify(pixels, width, x, y):
    o = 4 * (y * width + x)
    r, g, b = pixels[o], pixels[o + 1], pixels[o + 2]
    spread = max(r, g, b) - min(r, g, b)
    blue = b > 170 and spread > 60 and r < 170 and g < 170
    red = r > 150 and spread > 60 and g < 120 and b < 120
    black = r < 130 and g < 130 and b < 130 and spread < 70
    return blue, red, black


class Dump:
    def __init__(self, pixels, width, height):
        self.pixels, self.width, self.height = pixels, width, height

    def kind(self, x, y):
        return classify(self.pixels, self.width, x, y)

    def dark(self, x, y):
        return self.kind(x, y)[2]


def components_set(pixels):
    """8-connected components of a set of (x, y) pixels."""
    remaining = set(pixels)
    found = []
    while remaining:
        seed = next(iter(remaining))
        stack, pts = [seed], []
        remaining.discard(seed)
        while stack:
            cx, cy = stack.pop()
            pts.append((cx, cy))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nxt = (cx + dx, cy + dy)
                    if nxt in remaining:
                        remaining.discard(nxt)
                        stack.append(nxt)
        found.append(pts)
    return sorted(found, key=lambda pts: min(p[0] for p in pts))


def skeleton(pixels):
    """Zhang-Suen thinning to a 1 px ridge (same routine as ../liang-fig1-properties)."""
    pixels = set(pixels)
    while True:
        removed = []
        for step in (0, 1):
            drop = []
            for (x, y) in pixels:
                p2, p3, p4 = (x, y - 1) in pixels, (x + 1, y - 1) in pixels, (x + 1, y) in pixels
                p5, p6, p7 = (x + 1, y + 1) in pixels, (x, y + 1) in pixels, (x - 1, y + 1) in pixels
                p8, p9 = (x - 1, y) in pixels, (x - 1, y - 1) in pixels
                ring = [p2, p3, p4, p5, p6, p7, p8, p9]
                count = sum(ring)
                if count < 2 or count > 6:
                    continue
                transitions = sum(1 for i in range(8) if not ring[i] and ring[(i + 1) % 8])
                if transitions != 1:
                    continue
                if step == 0 and (p2 and p4 and p6 or p4 and p6 and p8):
                    continue
                if step == 1 and (p2 and p4 and p8 or p2 and p6 and p8):
                    continue
                drop.append((x, y))
            if not drop:
                break
            for pixel in drop:
                pixels.discard(pixel)
            removed.extend(drop)
        if not removed:
            break
    return pixels


def clusters(values, gap=1):
    values = sorted(values)
    out = []
    for value in values:
        if out and value - out[-1][-1] <= gap:
            out[-1].append(value)
        else:
            out.append([value])
    return out


def fit(axis_pixels, values):
    """Least-squares value = a + b*pixel with residuals."""
    n = len(axis_pixels)
    mp = sum(axis_pixels) / n
    mv = sum(values) / n
    sxx = sum((p - mp) ** 2 for p in axis_pixels)
    b = sum((p - mp) * (v - mv) for p, v in zip(axis_pixels, values)) / sxx
    a = mv - b * mp
    residuals = [v - (a + b * p) for p, v in zip(axis_pixels, values)]
    rms = (sum(r * r for r in residuals) / n) ** 0.5
    return [a, b], residuals, rms


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('raster')
    ap.add_argument('output')
    args = ap.parse_args()
    raw_sha = hashlib.sha256(open(args.raster, 'rb').read()).hexdigest()
    width, height, pixels = load_raw(args.raster)
    if [width, height] != RASTER_PX:
        raise ValueError('expected the pinned %s crop, got %dx%d' % (RASTER_PX, width, height))
    dump = Dump(pixels, width, height)

    dark = {(x, y) for y in range(height) for x in range(width) if dump.dark(x, y)}

    # ---- 1. plot frame ---------------------------------------------------
    row_counts = [sum(1 for x in range(width) if (x, y) in dark) for y in range(height)]
    col_counts = [sum(1 for y in range(height) if (x, y) in dark) for x in range(width)]
    top = max(range(height), key=lambda y: row_counts[y])
    bottom = max((y for y in range(top + 50, height)), key=lambda y: row_counts[y])
    left = max(range(width), key=lambda x: col_counts[x])
    right = max((x for x in range(left + 50, width)), key=lambda x: col_counts[x])
    frame = dict(top=top, bottom=bottom, left=left, right=right,
                 row_dark=[row_counts[top], row_counts[bottom]],
                 col_dark=[col_counts[left], col_counts[right]])

    # ---- 2. axis calibration --------------------------------------------
    x_peaks = []
    for x in range(left + 3, right - 2):
        stroke = sum(1 for y in range(bottom - 9, bottom) if (x, y) in dark)
        # major x ticks are 9 px strokes; the 5 px minor ticks are rejected here
        if stroke >= 8:
            x_peaks.append(x)
    x_centers = [sum(c) / len(c) for c in clusters(x_peaks)]
    y_peaks = []
    for y in range(top + 3, bottom - 2):
        stroke = sum(1 for x in range(left, left + 9) if (x, y) in dark)
        # major y ticks are 9 px strokes; the 7 px minor ticks are rejected here
        if stroke >= 8:
            y_peaks.append(y)
    y_centers = [sum(c) / len(c) for c in clusters(y_peaks)]

    if len(x_centers) != 5:
        raise ValueError('expected 5 major x ticks, found %r' % x_centers)
    if len(y_centers) != 7:
        raise ValueError('expected 7 major y ticks, found %r' % y_centers)
    x_values = [1.0, 1.1, 1.2, 1.3, 1.4]
    # Fig. 8(a) ordinate is labelled 5.0 ... 8.0 in 0.5 cm/s steps, top tick first.
    y_values = [8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0]
    xfit, xres, xrms = fit(x_centers, x_values)
    yfit, yres, yrms = fit(y_centers, y_values)

    def phi_of(x):
        return xfit[0] + xfit[1] * x

    def speed_of(y):
        return yfit[0] + yfit[1] * y

    def x_of(phi):
        return (phi - xfit[0]) / xfit[1]

    def legend(x, y, margin=0):
        for x0, y0, x1, y1 in LEGEND_BOXES:
            if x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin:
                return True
        return False

    # ---- 3. symbols ------------------------------------------------------
    def symbols(kind, limit=(6, 13), uncertainty=0.03):
        mask = {(x, y) for y in range(top + TITLE_ROWS, bottom - BOTTOM_ROWS) for x in range(left + 2, right - 1)
                if dump.kind(x, y)[{'blue': 0, 'red': 1}[kind]]}
        rows = []
        for pts in components_set(mask):
            if len(pts) < 18:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            bx0, bx1 = min(xs), max(xs)
            by0, by1 = min(ys), max(ys)
            w, h = bx1 - bx0 + 1, by1 - by0 + 1
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            if not (limit[0] <= w <= limit[1] and 5 <= h <= limit[1]):
                continue
            if legend(cx, cy):
                continue
            rows.append(dict(phi=round(phi_of(cx), 4), speed_cm_s=round(speed_of(cy), 4),
                             x_pixel=round(cx, 2), y_pixel=round(cy, 2),
                             bbox_px=[bx0, by0, bx1, by1], pixel_count=len(pts),
                             uncertainty_cm_s=uncertainty))
        rows.sort(key=lambda r: r['phi'])
        return rows

    case3 = symbols('red')
    case4 = symbols('blue')

    # ---- 4. curve tracing ------------------------------------------------
    symbol_rim = set()
    for symbol in case3 + case4:
        x0, y0, x1, y1 = symbol['bbox_px']
        for x in range(x0 - 3, x1 + 4):
            for y in range(y0 - 3, y1 + 4):
                symbol_rim.add((x, y))

    def curve(kind_flag):
        mask = set()
        for y in range(top + TITLE_ROWS, bottom - BOTTOM_ROWS):
            for x in range(left + AXIS_BAND, right - AXIS_BAND):
                if legend(x, y, margin=2) or (x, y) in symbol_rim:
                    continue
                if kind_flag == 'black':
                    if dump.dark(x, y):
                        mask.add((x, y))
                else:
                    if dump.kind(x, y)[0]:
                        mask.add((x, y))
        ridge = skeleton(mask)
        parts = components_set(ridge)
        if not parts:
            raise ValueError('no %s ridge found' % kind_flag)
        parts.sort(key=len, reverse=True)
        # The ridge is cut wherever a symbol rim was removed, so every fragment larger
        # than a speck is kept and the per-column median is taken over all of them.
        kept = [p for p in parts if len(p) >= 4]
        xs = [p[0] for part in kept for p in part]
        by_column = {}
        for part in kept:
            for x, y in part:
                by_column.setdefault(x, []).append(y)
        points = [(x, sum(sorted(by_column[x])) / len(by_column[x])) for x in sorted(by_column)]
        stats = dict(ridge_pixels=len(ridge), components=len(parts), kept_components=len(kept),
                     kept_pixels=sum(len(p) for p in kept),
                     dropped_pixels=sum(len(p) for p in parts if len(p) < 4),
                     largest_components=sorted([len(p) for p in parts], reverse=True)[:8],
                     span_px=[min(xs), max(xs)])
        return points, stats

    def interp(points, x):
        if not points or x <= points[0][0] or x >= points[-1][0]:
            return None
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if x0 <= x <= x1:
                if x1 == x0:
                    return y0
                return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
        return None

    black_points, black_stats = curve('black')
    blue_points, blue_stats = curve('blue')

    # Case 2: black diamonds sit on the Case-1 curve and thicken it to ~9-13 px.
    # The Case-1 line itself is 6-7 px thick at this scale, so only columns that are
    # thicker than that can be a diamond; the diamond is 10-14 px at its centre.
    diamond_columns = []
    thickness = {}
    for x in range(left + AXIS_BAND, right - AXIS_BAND):
        run = best = 0
        for y in range(top + TITLE_ROWS, bottom - BOTTOM_ROWS):
            if (x, y) in dark and not legend(x, y, margin=2):
                run += 1
                best = max(best, run)
            else:
                run = 0
        thickness[x] = best
        if 8 <= best <= 16:
            diamond_columns.append(x)
    diamonds = []
    for group in clusters(diamond_columns, gap=1):
        if not 4 <= len(group) <= 18:
            continue
        if max(thickness[x] for x in group) < 9:
            continue
        cx = sum(group) / len(group)
        ys = [y for x in group for y in range(top + TITLE_ROWS, bottom - BOTTOM_ROWS)
              if (x, y) in dark and not legend(x, y, margin=2)]
        if not ys:
            continue
        cy = sum(ys) / len(ys)
        if legend(cx, cy):
            continue
        reference = interp(black_points, cx)
        if reference is None or abs(cy - reference) > 8:
            continue
        diamonds.append(dict(phi=round(phi_of(cx), 4), speed_cm_s=round(speed_of(cy), 4),
                             x_pixel=round(cx, 2), y_pixel=round(cy, 2),
                             column_count=len(group), pixel_count=len(ys),
                             peak_thickness_px=max(thickness[x] for x in group),
                             curve_offset_px=round(cy - reference, 2),
                             uncertainty_cm_s=0.03))
    diamonds.sort(key=lambda r: r['phi'])

    def sample_curve(points, label, uncertainty):
        rows = []
        for phi in SAMPLE_PHI:
            y = interp(points, x_of(phi))
            if y is None:
                continue
            rows.append(dict(phi=phi, speed_cm_s=round(speed_of(y), 4),
                             x_pixel=round(x_of(phi), 2), y_pixel=round(y, 2),
                             uncertainty_cm_s=uncertainty))
        if len(rows) < 0.8 * len(SAMPLE_PHI):
            raise ValueError('curve %s covers only %d of %d samples' %
                             (label, len(rows), len(SAMPLE_PHI)))
        return rows

    case1 = sample_curve(black_points, 'Case 1', 0.02)
    case5 = sample_curve(blue_points, 'Case 5', 0.02)

    # Flat stage/speed rows in the reference schema consumed by compare_reference.py.
    paper_rows = []
    for stage, key in ((1, 'case1_curve'), (2, 'case2_markers'), (3, 'case3_markers'),
                       (4, 'case4_markers'), (5, 'case5_curve')):
        for row in dict(case1_curve=case1, case2_markers=diamonds, case3_markers=case3,
                        case4_markers=case4, case5_curve=case5)[key]:
            paper_rows.append(dict(stage=stage, phi=row['phi'], speed_cm_s=row['speed_cm_s'],
                                   x_pixel=row['x_pixel'], y_pixel=row['y_pixel'],
                                   uncertainty_cm_s=row['uncertainty_cm_s']))
    paper_rows.sort(key=lambda r: (r['stage'], r['phi']))

    result = dict(
        paper_sha256=PAPER_SHA,
        raster=dict(path=args.raster, sha256=raw_sha, width=width, height=height),
        raster_origin=dict(kind='campaign library crop of the paper panel',
                           pdf_page_1based=PAGE_INDEX + 1, page_index=PAGE_INDEX,
                           crop_pt=CROP_PT, scale=3,
                           note='raster digitisation of the published panel; not author data'),
        frame=frame,
        calibration=dict(
            x_ticks_px=x_centers, phi_ticks=x_values, phi_from_pixel=xfit,
            x_residuals_px=xres, x_rms_px=xrms,
            y_ticks_px=y_centers, speed_ticks_cm_s=y_values, speed_from_pixel=yfit,
            y_residuals_px=yres, y_rms_px=yrms,
            cm_s_per_pixel=abs(yfit[1]), phi_per_pixel=abs(xfit[1])),
        trace=dict(case1=black_stats, case5=blue_stats),
        paper_rows=paper_rows,
        rows=dict(case1_curve=case1, case2_markers=diamonds,
                  case3_markers=case3, case4_markers=case4, case5_curve=case5),
        counts=dict(case1_curve=len(case1), case2_markers=len(diamonds),
                    case3_markers=len(case3), case4_markers=len(case4),
                    case5_curve=len(case5)),
        limitations=[
            "Raster digitisation of a published panel, not the authors' numerical data",
            'Symbol centres are bounding-box centres; Case-3/Case-4 triangles carry 0.03 cm/s uncertainty',
            'Case-2 diamonds are found from stroke thickness on the traced Case-1 curve and carry 0.03 cm/s uncertainty',
            'Case-1 and Case-5 curves are read from a thinned ridge and carry 0.02 cm/s uncertainty',
            'Symbol rims are removed before tracing; the curves are linearly interpolated across them',
            'No extrapolation outside the digitised equivalence-ratio span (0.95-1.40)',
        ],
    )
    parent = os.path.dirname(os.path.abspath(args.output))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.output, 'w', encoding='utf8') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps(dict(counts=result['counts'], x_rms=xrms, y_rms=yrms,
                          trace=result['trace'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
