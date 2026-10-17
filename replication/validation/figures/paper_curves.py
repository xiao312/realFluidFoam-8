"""Extract approximate 2022 Fig. 6 vector curves; preserve clipped segments."""
import csv
import json
import sys
from pathlib import Path
import numpy as np
import pymupdf

pdf, output = Path(sys.argv[1]), Path(sys.argv[2])
page = pymupdf.open(pdf)[9]
# Calibration uses inspected major ticks, not the outer axis box (which has margins).
panels = {
    "rho_kg_m3": (120.372, 64.409, 183.03, 127.898, 278.370, 180.120, 64.409, 0, 400),
    "Cp_J_kg_K": (332.246, 64.409, 183.03, 339.772, 490.244, 180.346, 73.309, 2000, 8000),
    "mu_Pa_s": (120.372, 210.855, 329.475, 127.898, 278.370, 329.475, 219.9821, 0, 6e-5),
    "kappa_W_m_K": (332.246, 210.855, 329.475, 339.772, 490.244, 329.475, 214.669, 0, .15),
}
rows = []
for number, drawing in enumerate(page.get_drawings()):
    color = drawing.get("color")
    if not color or color[0] < .8 or color[1] > .05 or color[2] > .05:
        continue
    rect = drawing["rect"]
    for name, (left, top, bottom, x200, x600, ylow, yhigh, low, high) in panels.items():
        if not (left-.05 <= rect.x0 and rect.x1 <= left+167.5 and top-.05 <= rect.y0 <= rect.y1 <= bottom+.05):
            continue
        if rect.width < 50 and name != "Cp_J_kg_K":
            continue
        dash = drawing["dashes"]
        pressure = 1 if "2.442" in dash else 50 if "1.0539" in dash else 100 if "2.6735" in dash else 200 if "4.0097" in dash else 300
        points = []
        for item in drawing["items"]:
            if item[0] == "l":
                points.extend([tuple(item[1]), tuple(item[2])])
            elif item[0] == "c":
                a, b, c, d = [np.array(tuple(point)) for point in item[1:]]
                for t in np.linspace(0, 1, 101):
                    points.append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
        for x, y in points:
            rows.append(dict(property=name, p_atm=pressure, segment=number,
                T_K=200+(x-x200)*400/(x600-x200),
                value=low+(ylow-y)*(high-low)/(ylow-yhigh)))
output.mkdir(parents=True, exist_ok=True)
with (output/"paper-2022-figure6-curves.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(output/"digitization-notes.json").write_text(json.dumps(dict(
    source="Owner-supplied 2022 PDF, page 10, Figure 6",
    method="Vector paths with major-tick calibration; cubic Bezier paths sampled at 101 points",
    limitations="Approximate published drawing, not author tables. Clipped Cp segments remain disconnected. No interpolation across hidden peaks.",
    panels=panels, rows=len(rows)), indent=2)+"\n")
print("Extracted", len(rows), "vector samples with separate clipped segments")
