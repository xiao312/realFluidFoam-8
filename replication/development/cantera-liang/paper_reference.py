"""Digitize the pinned raster Liang Fig.8(a), retaining calibration and limits."""
import argparse
import hashlib
import json
from pathlib import Path

PAPER_SHA = '24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe'


def components(mask):
    import numpy as np
    remaining = set(zip(*np.nonzero(mask)))
    while remaining:
        seed = remaining.pop(); points = [seed]; stack = [seed]
        while stack:
            y, x = stack.pop()
            for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                node = y+dy, x+dx
                if node in remaining:
                    remaining.remove(node); stack.append(node); points.append(node)
        if len(points) >= 35:
            yield points


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['plan', 'apply'])
    p.add_argument('paper', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args()
    if hashlib.sha256(a.paper.read_bytes()).hexdigest() != PAPER_SHA or a.output.exists():
        raise ValueError('Expected pinned paper and a new output')
    print(json.dumps(dict(page_index=5, clip_pt=[28, 50, 232, 225], scale=6,
                         output=str(a.output.resolve()), reference_type='digitized, not author data')))
    if a.action == 'plan': return
    import pymupdf as fitz
    import numpy as np
    page = fitz.open(a.paper)[5]
    pix = page.get_pixmap(matrix=fitz.Matrix(6, 6), clip=fitz.Rect(28, 50, 232, 225))
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    # Tick centers measured from the rendered axis strokes; use all major ticks.
    xticks = [314., 506.5, 699.5, 892., 1084.5]
    phiticks = [1., 1.1, 1.2, 1.3, 1.4]
    yticks = [186.5, 333.5, 481., 629., 776.5, 923.5]
    speedticks = [7.5, 7., 6.5, 6., 5.5, 5.]
    xfit = np.polyfit(xticks, phiticks, 1); yfit = np.polyfit(yticks, speedticks, 1)
    def point(x, y, stage, uncertainty):
        return dict(stage=stage, phi=float(np.polyval(xfit, x)),
                    speed_cm_s=float(np.polyval(yfit, y)), x_pixel=float(x), y_pixel=float(y),
                    uncertainty_cm_s=uncertainty)
    rows = []; curves = []
    for stage, mask in [(3, (rgb[:, :, 0] > 160) & (rgb[:, :, 1] < 130) & (rgb[:, :, 2] < 130)),
                        (4, (rgb[:, :, 2] > 150) & (rgb[:, :, 0] < 130) & (rgb[:, :, 1] < 130))]:
        for cluster in components(mask):
            yy, xx = np.array(cluster).T
            x, y = .5*(xx.min()+xx.max()), .5*(yy.min()+yy.max())
            width, height = int(xx.max()-xx.min()), int(yy.max()-yy.min())
            if stage == 4 and len(cluster) > 5000:
                curves = cluster
            if 10 <= width <= 22 and 9 <= height <= 22 and 300 <= x <= 1100 and y < 725:
                # Exclude the red legend symbol; actual phi~1.04 data is near y=350.
                if x < 500 and y > 550: continue
                row = point(x, y, stage, .03)
                row.update(marker_pixel_count=len(cluster), bounds_px=[int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())])
                rows.append(row)
    for stage in [3, 4]:
        if sum(r['stage'] == stage for r in rows) != 10:
            raise ValueError('Unexpected triangle count; review raster segmentation')
    if not curves: raise ValueError('Blue curve not found')
    yy, xx = np.array(curves).T
    for x in range(170, 1150, 4):
        ys = yy[xx == x]
        if len(ys): rows.append(point(x, float(np.median(ys)), 5, .015))
    black = rgb.max(axis=2) < 100
    for x in range(182, 1150, 4):
        ys = np.where(black[170:680, x])[0]+170
        if not len(ys): continue
        # The top stroke below the title is the curve; later strokes are legend text.
        end = np.where(np.diff(ys) > 1)[0]
        ys = ys[:end[0]+1] if len(end) else ys
        rows.append(point(x, float(np.median(ys)), 1, .04))
    for marker in sorted([r for r in rows if r['stage'] == 3], key=lambda r: r['phi']):
        x = int(round(marker['x_pixel']))
        ys, xs = np.nonzero(black[170:650, x-5:x+6]); ys += 170
        if not len(ys): raise ValueError('Missing black marker')
        top = int(ys.min()); selected = ys[ys <= top+30]
        rows.append(point(x, .5*(selected.min()+selected.max()), 2, .04))
    rows.sort(key=lambda r: (r['stage'], r['phi']))
    result = dict(paper_sha256=PAPER_SHA, page_index=5, clip_pt=[28, 50, 232, 225], scale=6,
                  calibration=dict(x_ticks_px=xticks, phi_ticks=phiticks, y_ticks_px=yticks,
                                   speed_ticks_cm_s=speedticks, phi_from_pixel=xfit.tolist(), speed_from_pixel=yfit.tolist()),
                  rows=rows, limitations=['Raster digitization, not original numerical data',
                    'Triangle bounding-box centers carry 0.03 cm/s uncertainty',
                    'Black diamonds overlap the black line; Cases 1/2 carry 0.04 cm/s uncertainty',
                    'No extrapolation outside plotted curve coordinates'])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')


if __name__ == '__main__': main()
