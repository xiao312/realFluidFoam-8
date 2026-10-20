"""Render Figures 2–7 at original scale, retaining paper graphics and explicit data legends."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

PAPER_SHA = "24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe"
PANELS = {
    2: (2, (260, 50, 461, 216), "Critical temperature and pressure"),
    3: (3, (28, 50, 232, 225), "Hydrogen/air flame speed, 100 atm"),
    4: (3, (248, 50, 454, 211), "Fresh density and burning flux, 100 atm"),
    5: (4, (47, 50, 236, 215), "Adiabatic flame endpoint temperature"),
    6: (4, (47, 258, 239, 424), "Transport ratios along the stoichiometric flame"),
    7: (4, (260, 50, 459, 204), "Stoichiometric flame structure"),
}
COLORS = [(0, .48, .27), (.1, .36, .8), (.8, .35, .05),
          (.55, .15, .65), (.15, .6, .65), (.7, .15, .3)]
CASES = ["1", "2", "3star", "3", "4", "5"]


def read_csv(path):
    with Path(path).open() as stream:
        return list(csv.DictReader(stream))


def load_runs(manifest):
    runs = json.loads(manifest.read_text(encoding="utf-8-sig"))
    out = []
    for row in runs:
        result = Path(row["result"])
        if not (result/"completed.txt").exists():
            continue
        levels = read_csv(result/"refinement.csv")
        if len(levels) < 2:
            continue
        last = levels[-1]
        change = abs(float(last["speed_cm_s"])/float(levels[-2]["speed_cm_s"])-1)
        out.append({**row, **{k: float(v) for k, v in last.items() if k != "case"},
                    "case": str(last["case"]), "grid_change": change})
    return out


def text(page, rect, value, size=8, color=(0, 0, 0)):
    import pymupdf as fitz
    if page.insert_textbox(fitz.Rect(rect), value, fontsize=size, fontname="helv", color=color) < 0:
        raise ValueError("Text overflow: "+value)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["plan", "apply"])
    for field in ("paper", "manifest", "critical", "species", "output"):
        p.add_argument(field, type=Path)
    p.add_argument("--transport", choices=["lj", "pairs"], default="lj")
    a = p.parse_args()
    if hashlib.sha256(a.paper.read_bytes()).hexdigest() != PAPER_SHA:
        raise ValueError("Uncalibrated source PDF")
    runs = [r for r in load_runs(a.manifest) if r["transport"] == a.transport]
    if a.output.exists():
        raise ValueError("Choose a new artifact directory")
    print(json.dumps({"figures": list(PANELS), "completed_runs": len(runs), "output": str(a.output)}))
    if a.action == "plan":
        return
    import numpy as np
    import pymupdf as fitz
    a.output.mkdir(parents=True)
    source = fitz.open(a.paper)
    report = fitz.open()
    species_rows = [line.split() for line in a.species.read_text().splitlines()]
    names = [row[0] for row in species_rows]
    molecular_weights = np.array([float(row[4]) for row in species_rows])
    clipped = {}
    for number, (page_index, box, caption) in PANELS.items():
        page = report.new_page(width=500, height=390)
        crop = fitz.Rect(box)
        text(page, (18, 12, 482, 29), f"Liang Figure {number}: {caption}", 11)
        for x, title in [(18, "Original paper"), (270, "Paper + our calculation (open symbols)")]:
            text(page, (x, 37, x+212, 51), title, 8)
            target = fitz.Rect(x, 56, x+crop.width, 56+crop.height)
            page.show_pdf_page(target, source, page_index, clip=crop)
        legend_y = 245
        legends = []
        omitted = 0

        def line(points, color, label, bounds, every=1):
            nonlocal omitted
            # Coordinates are in original page points, so all paper dimensions,
            # tick locations and relative line/marker sizes remain unchanged.
            good = []
            for xp, yp in points:
                if bounds[0] <= xp <= bounds[2] and bounds[1] <= yp <= bounds[3]:
                    good.append(fitz.Point(270+xp-crop.x0, 56+yp-crop.y0))
                else:
                    omitted += 1
            if len(good) > 1:
                page.draw_polyline(good, color=color, width=.65, dashes="[2 2] 0")
            for pt in good[::every]:
                page.draw_circle(pt, 1.35, color=color, fill=(1, 1, 1), width=.65)
            legends.append((color, label))

        if number == 2:
            raw = read_csv(a.critical)
            for fuel, color in zip(["H2", "CH4"], COLORS):
                rows = [r for r in raw if r["fuel"] == fuel][::10]
                line([(282.737+(float(r["phi"])-.6)/1.4*151.321,
                       194.121-(float(r["Tc_K"])-60)/100*138.085) for r in rows],
                     color, fuel+" Tc (existing SRK audit)", (282.737, 56.036, 434.058, 194.121))
                line([(282.737+(float(r["phi"])-.6)/1.4*151.321,
                       188.808-(float(r["Pc_atm"])-10)/50*132.771) for r in rows],
                     COLORS[len(legends)+1], fuel+" Pc (existing SRK audit)",
                     (282.737, 56.036, 434.058, 194.121))
        elif number in [3, 4, 5]:
            for case, color in zip(CASES, COLORS):
                selected = sorted([r for r in runs if r["case"] == case], key=lambda r: r["phi"])
                if not selected or (number == 4 and case not in ["1", "2"]):
                    continue
                if number == 5 and case not in ["1", "2", "3", "3star"]:
                    continue
                if number == 3:
                    points = [(52.709+(r["phi"]-1)*152.171,
                               194.703-(r["speed_cm_s"]-50)*4.352) for r in selected if 1 <= r["phi"] <= 2.1]
                    bounds = (52.709, 55.026, 220.09, 207.764)
                elif number == 5:
                    points = [(74.147+(r["phi"]-.85)/.5*(230.881-74.147),
                               179.739-(r["Tb_K"]-2250)/250*(179.739-67.851))
                              for r in selected if .85 <= r["phi"] <= 1.35]
                    bounds = (73.946, 54.434, 230.882, 197.642)
                else:
                    bounds = (272.693, 56.879, 418.153, 189.616)
                    line([(296.925+(r["phi"]-1)*60.614,
                           189.616-(r["rhou_kg_m3"]/1000-.05)/.05*132.738) for r in selected],
                         color, "Case "+case+" density", bounds)
                    points = [(296.925+(r["phi"]-1)*60.614,
                               189.616-r["massflux_kg_m2s"]/10/7*132.738) for r in selected]
                    color = COLORS[int(case)+2]
                label = "Case "+case.replace("star", "*")+(" burning flux" if number == 4 else "")
                line(points, color, label, bounds)
        else:
            candidates = [r for r in runs if r["case"] == "5" and r["phi"] == 1.]
            if candidates:
                run = candidates[-1]
                raw = read_csv(Path(run["result"])/("transport.csv" if number == 6 else "profile.csv"))
                if number == 6:
                    for key, color, label in [
                        ("lambda_ideal_over_real", COLORS[0], "lambda ideal/real"),
                        ("Dmix_H2_real_over_ideal", COLORS[1], "H2 mixture D real/ideal"),
                        ("Dbin_H2_N2_real_over_ideal", COLORS[2], "H2-N2 binary D real/ideal")]:
                        rows = [r for r in raw if 300 <= float(r["T_K"]) <= 2000]
                        line([(72.3+(float(r["T_K"])-200)/1800*(230.8-72.3),
                               406.7-(float(r[key])-.9)/.15*(406.7-286.1)) for r in rows],
                             color, label, (72.3, 262.3, 230.8, 406.7), max(1, len(rows)//15))
                else:
                    xx = np.array([float(r["x_m"]) for r in raw])
                    temp = np.array([float(r["T_K"]) for r in raw])
                    # Paper T=1500 K crossing is near x=0.98018 cm; translation only.
                    xref = np.interp(1500, temp, xx)
                    xp = 369.648+(100*(xx-xref)+.98018-.9800)/.00025*18.51
                    bounds = (288.22, 54.725, 435.757, 189.356)
                    line(list(zip(xp, 166.864-(temp-500)/500*25.47)), COLORS[0], "T; align at 1500 K", bounds, max(1, len(raw)//30))
                    ys = np.array([[float(r["Y_"+n]) for n in names] for r in raw])
                    mole = ys/molecular_weights
                    mole /= mole.sum(axis=1)[:, None]
                    for name, color in zip(["H2", "O2", "HO2", "H2O2"], COLORS[1:]):
                        values = mole[:, names.index(name)]
                        points = [(float(x), 59.85-math.log10(v)*22.45) for x, v in zip(xp, values) if v > 0]
                        line(points, color, name+" mole fraction", bounds, max(1, len(points)//30))
            else:
                text(page, (270, 224, 480, 240), "Case 5 stoichiometric profile pending", 8)
        for i, (color, label) in enumerate(legends):
            x = 18+(i % 2)*242
            y = legend_y+(i//2)*14
            page.draw_line((x, y+4), (x+17, y+4), color=color, width=.65, dashes="[2 2] 0")
            page.draw_circle((x+8.5, y+4), 1.35, color=color, fill=(1, 1, 1), width=.65)
            text(page, (x+22, y, x+237, y+13), label, 7)
        notes = [
            "Computed: Burke 2012 N2 bath-gas kinetics; 100 atm; Tu=298 K assumed; "+a.transport+" transport.",
            "Case 3*: temperature equation. Cases 3-5: total enthalpy. Cases 4/5 conductivity provisional.",
            "Grid refinement is recorded; agreement with the paper is not yet accepted.",
        ]
        if number == 2:
            notes = ["Existing critical-property audit, independent of hydrogen kinetics.",
                     "The known critical-pressure discrepancy remains unresolved. No parameters fitted."]
        if number == 6:
            notes.append("Paper's D definition is unspecified; three named quantities shown. Raster calibration approximate.")
        if number == 7:
            notes.append("x translated to the paper's approximate 1500 K crossing; physical width unchanged.")
        if omitted:
            notes.append(f"{omitted} samples outside the original axes are omitted, never clipped to the boundary.")
        text(page, (18, 300, 482, 366), "\n".join(notes), 7)
        text(page, (18, 371, 482, 386), "Source: Liang et al., Proc. Combust. Inst. 37 (2019) 1733-1739, Fig. "+str(number), 7)
        page.get_pixmap(matrix=fitz.Matrix(3, 3)).save(a.output/f"figure-{number}.png")
        clipped[str(number)] = omitted
    report.save(a.output/"liang-hydrogen-figures-2-7.pdf")
    record = {"paper_sha256": PAPER_SHA, "runs": runs, "samples_outside_axes": clipped,
              "transport_variant": a.transport, "figure_7_alignment": "T=1500 K to paper x~0.98018 cm; translation only"}
    (a.output/"evidence.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
