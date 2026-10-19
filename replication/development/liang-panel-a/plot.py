"""Overlay only computed ideal-gas speeds on Liang's original Fig. 8(a)."""
import argparse
import hashlib
import json
from pathlib import Path

PAPER_SHA = '24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe'
GREEN = (0, .48, .27)
PANEL = (28, 50, 232, 225)  # PDF page 6, points; 204 x 175 at publication scale.
CAPTION = (28, 424, 232, 453)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs(paper, results):
    if digest(paper) != PAPER_SHA:
        raise ValueError('PDF differs from the calibrated owner-supplied Liang paper')
    rows = sorted(json.loads(results.read_text()), key=lambda row: row['phi'])
    if not rows or len({row['phi'] for row in rows}) != len(rows):
        raise ValueError('Need unique, nonempty solved operating points')
    for row in rows:
        if abs(row.get('pressure_Pa', 10132500) - 10132500) > 1:
            raise ValueError('Expected 100 atm')
        if abs(row.get('Tu_K', 298) - 298) > .001:
            raise ValueError('Expected 298 K')
        if not 0 < row['speed_cm_s'] < 100:
            raise ValueError('Invalid flame speed')
    return rows


def text(page, rect, content, size=8, color=(0, 0, 0)):
    import pymupdf as fitz
    remaining = page.insert_textbox(fitz.Rect(rect), content, fontsize=size,
                                    fontname='helv', color=color)
    if remaining < 0:
        raise ValueError('Text does not fit: ' + content)


def overlay(page, origin, rows):
    """Use the same pixel calibration as the existing Case-1 digitization."""
    import pymupdf as fitz
    x0, y0 = origin
    points = [fitz.Point(x0 + (157.5 + (row['phi']-1)*385/.4)/3,
                        y0 + (94.5 + (7.5-row['speed_cm_s'])*367/2.5)/3)
              for row in rows if .916 <= row['phi'] <= 1.437]
    if len(points) < 2:
        raise ValueError('Need at least two computed points within the panel axes')
    # The original line is about one point wide; open symbols keep it visible.
    page.draw_polyline(points, color=GREEN, width=.7, dashes='[2 2] 0')
    for point in points:
        page.draw_circle(point, 1.3, color=GREEN, fill=(1, 1, 1), width=.65)
    return len(points)


def legend(page, x, y):
    import pymupdf as fitz
    page.draw_line(fitz.Point(x, y+4), fitz.Point(x+17, y+4),
                   color=GREEN, width=.7, dashes='[2 2] 0')
    page.draw_circle(fitz.Point(x+8.5, y+4), 1.3, color=GREEN,
                     fill=(1, 1, 1), width=.65)
    text(page, (x+22, y, x+204, y+13), 'Cantera 3.2: ideal gas (computed)', 7, GREEN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply'])
    parser.add_argument('paper', type=Path)
    parser.add_argument('results', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows = load_inputs(args.paper, args.results)
    plan = {'computed_case': 'Case 1 ideal gas only', 'points': len(rows),
            'phi_range': [rows[0]['phi'], rows[-1]['phi']],
            'panel_size_pt': [204, 175], 'output': str(args.output.resolve())}
    print(json.dumps(plan))
    if args.output.exists():
        raise ValueError('Use a new output directory')
    if args.action == 'plan':
        return
    import pymupdf as fitz
    args.output.mkdir(parents=True)
    source = fitz.open(args.paper)
    doc = fitz.open()
    page = doc.new_page(width=468, height=350)
    text(page, (18, 12, 450, 36), 'Liang Fig. 8(a): methane/air at 100 atm', 11)
    text(page, (18, 36, 222, 52), 'Original paper - all five assumptions', 8)
    text(page, (246, 36, 450, 52), 'Same panel + our ideal-gas calculation', 8)
    for x in [18, 246]:
        page.show_pdf_page(fitz.Rect(x, 52, x+204, 227), source, 5,
                           clip=fitz.Rect(PANEL))
    nvisible = overlay(page, (246, 52), rows)
    legend(page, 246, 234)
    page.show_pdf_page(fitz.Rect(18, 235, 222, 264), source, 5,
                       clip=fitz.Rect(CAPTION))
    text(page, (246, 251, 450, 278),
         'Original black/red/blue curves: Liang results.\nOnly Case 1 is newly calculated in Cantera.', 7.5)
    text(page, (18, 283, 450, 329),
         f"{len(rows)} solved conditions; author GRI30 reactions/NASA7, Cantera species transport.\n"
         'Steady FreeFlame; 100 atm; unburnt gas 298 K; mixture-averaged transport; Soret off.\n'
         '298 K is our stated assumption: Liang does not give a numeric inlet temperature in the main PDF.\n'
         'Both panels retain the original 204 x 175 pt size, typography, line widths and markers.', 7.5)
    text(page, (18, 332, 450, 345),
         'Source: Liang, Li & Law, Proc. Combust. Inst. 37 (2019), 1733-1739; doi:10.1016/j.proci.2018.06.070', 6.6)
    doc.save(args.output/'liang-panel-a-comparison.pdf', garbage=4, deflate=True)
    page.get_pixmap(matrix=fitz.Matrix(3, 3)).save(args.output/'liang-panel-a-comparison.png')
    single = fitz.open()
    standalone = single.new_page(width=204, height=211)
    standalone.show_pdf_page(fitz.Rect(0, 0, 204, 175), source, 5, clip=fitz.Rect(PANEL))
    overlay(standalone, (0, 0), rows)
    legend(standalone, 2, 181)
    text(standalone, (2, 195, 202, 209), 'Other curves: original paper results (Cases 2-5).', 7)
    standalone.get_pixmap(matrix=fitz.Matrix(4, 4)).save(args.output/'liang-panel-a-overlay.png')
    manifest = dict(plan, source_pdf_sha256=PAPER_SHA, results_sha256=digest(args.results),
                    plotter_sha256=digest(Path(__file__)), visible_computed_points=nvisible,
                    rows=rows, pdf_page_index=5, panel_clip_pt=PANEL,
                    calibration={'raster_scale': 3, 'phi_1_x': 157.5, 'phi_1_4_x': 542.5,
                                 'speed_7_5_y': 94.5, 'speed_5_y': 461.5},
                    other_curves='Unmodified source paper; no new Cases 2-5 calculations')
    manifest['outputs'] = {path.name: digest(path) for path in args.output.iterdir()}
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
