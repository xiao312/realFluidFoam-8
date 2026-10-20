"""Render Figures 2–7 at original scale, retaining paper graphics and explicit data legends."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import plot_diagnostics

PAPER_SHA = "24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe"
PANELS = {
    2: (2, (260, 50, 461, 216), "Critical temperature and pressure"),
    3: (3, (28, 50, 232, 225), "Hydrogen/air flame speed, 100 atm"),
    4: (3, (248, 50, 454, 211), "Fresh density and burning flux, 100 atm"),
    5: (4, (47, 50, 236, 215), "Adiabatic flame endpoint temperature"),
    6: (4, (47, 258, 239, 424), "Transport ratios along the stoichiometric flame"),
    7: (4, (260, 50, 459, 204), "Stoichiometric flame structure"),
}
# Measured source caption blocks, padded by one point to preserve glyph edges.
CAPTIONS = {
    2: (262.29, 218.98, 459.10, 237.92),
    3: (30.98, 233.99, 227.83, 252.92),
    4: (246.17, 213.98, 443.00, 232.92),
    5: (47.09, 222.98, 243.90, 241.92),
    6: (47.09, 432.56, 243.91, 451.50),
    7: (262.29, 213.98, 458.35, 232.92),
}
COLORS = [(0, .48, .27), (.1, .36, .8), (.8, .35, .05),
          (.55, .15, .65), (.15, .6, .65), (.7, .15, .3)]
CASES = ["1", "2", "3star", "3", "4", "5"]
CALIBRATION_PATH = Path(__file__).with_name("figure2-6-calibration.json")
AXES = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))["axes"]
FIGURE7 = {
    "x_points_per_cm": 37015.746343701074,
    "x_intercept_points": -35905.778840562176,
    "temperature_intercept_points": 192.3287139892578,
    "temperature_points_per_K": -0.05093020629882814,
    "log_species_intercept_points": 60.47498357863653,
    "log_species_points_per_decade": -22.38328486851282,
    "paper_1500K_x_cm": 0.980127068315757,
}

def axis(name, value):
    slope, intercept = AXES[name]["forward_map"]
    return slope*value+intercept

def figure7_coordinates(x_m, temperature_K):
    """Translate a monotonic temperature front; keep metres-to-cm scale exact."""
    import numpy as np
    if np.any(np.diff(temperature_K) < -1e-3):
        raise ValueError("Figure 7 alignment requires a monotonic temperature front")
    xref = np.interp(1500, temperature_K, x_m)
    aligned_cm = 100*(x_m-xref)+FIGURE7["paper_1500K_x_cm"]
    return (FIGURE7["x_points_per_cm"]*aligned_cm
            +FIGURE7["x_intercept_points"])


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
    if page.insert_textbox(fitz.Rect(rect), value, fontsize=size, fontname="helv", color=color, lineheight=1) < 0:
        raise ValueError("Text overflow: "+value)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["plan", "apply"])
    for field in ("paper", "manifest", "critical", "species", "output"):
        p.add_argument(field, type=Path)
    p.add_argument("--transport", choices=["lj", "pairs"], default="lj")
    p.add_argument("--diagnostics", type=Path)
    a = p.parse_args()
    if hashlib.sha256(a.paper.read_bytes()).hexdigest() != PAPER_SHA:
        raise ValueError("Uncalibrated source PDF")
    runs = [r for r in load_runs(a.manifest) if r["transport"] == a.transport]
    diagnostics = plot_diagnostics.load(a.diagnostics)
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
        extra_legends = plot_diagnostics.legends(diagnostics, number)
        extra_height = 14*math.ceil(len(extra_legends)/2)
        page = report.new_page(width=500, height=420+extra_height)
        crop = fitz.Rect(box)
        text(page, (18, 9, 482, 35), f"Liang Figure {number}: {caption}", 11)
        for x, title in [(18, "Original paper"), (270, "Paper + our calculation (open symbols)")]:
            text(page, (x, 37, x+212, 51), title, 8)
            target = fitz.Rect(x, 56, x+crop.width, 56+crop.height)
            page.show_pdf_page(target, source, page_index, clip=crop)
        original_caption = fitz.Rect(CAPTIONS[number])
        caption_target = fitz.Rect(
            18+original_caption.x0-crop.x0, 56+original_caption.y0-crop.y0,
            18+original_caption.x1-crop.x0, 56+original_caption.y1-crop.y0)
        page.show_pdf_page(caption_target, source, page_index, clip=original_caption)
        legend_y = 277
        legends = []
        omitted = 0

        def line(points, color, label, bounds, every=1):
            nonlocal omitted
            # Coordinates are in original page points, so all paper dimensions,
            # tick locations and relative line/marker sizes remain unchanged.
            good = []
            segments = [[]]
            for xp, yp in points:
                # Vector ticks differ from frame positions by up to 0.014 pt.
                # Retain that finite calibration tolerance without changing data.
                if bounds[0]-.02 <= xp <= bounds[2]+.02 and bounds[1]-.02 <= yp <= bounds[3]+.02:
                    pt = fitz.Point(270+xp-crop.x0, 56+yp-crop.y0)
                    good.append(pt)
                    segments[-1].append(pt)
                else:
                    omitted += 1
                    if segments[-1]:
                        segments.append([])
            for segment in segments:
                if len(segment) > 1:
                    page.draw_polyline(segment, color=color, width=.65, dashes="[2 2] 0")
            for pt in good[::every]:
                page.draw_circle(pt, 1.35, color=color, fill=(1, 1, 1), width=.65)
            legends.append((color, label))

        if number == 2:
            raw = read_csv(a.critical)
            for fuel, color in zip(["H2", "CH4"], COLORS):
                rows = [r for r in raw if r["fuel"] == fuel][::10]
                line([(axis("2_x", float(r["phi"])), axis("2_Tc_K", float(r["Tc_K"]))) for r in rows],
                     color, fuel+" Tc (existing SRK audit)", (282.737, 56.036, 434.058, 194.121))
                line([(axis("2_x", float(r["phi"])), axis("2_Pc_atm", float(r["Pc_atm"]))) for r in rows],
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
                    points = [(axis("3_x", r["phi"]), axis("3_speed_cm_s", r["speed_cm_s"]))
                              for r in selected if 1 <= r["phi"] <= 2.1]
                    bounds = (52.709, 55.026, 220.09, 207.764)
                elif number == 5:
                    points = [(axis("5_x", r["phi"]), axis("5_Tb_K", r["Tb_K"]))
                              for r in selected if .85 <= r["phi"] <= 1.35]
                    bounds = (73.946, 54.434, 230.882, 197.642)
                else:
                    bounds = (272.693, 56.879, 418.153, 189.616)
                    line([(axis("4_x", r["phi"]), axis("4_density_g_cm3", r["rhou_kg_m3"]/1000))
                          for r in selected],
                         color, "Case "+case+" density", bounds)
                    points = [(axis("4_x", r["phi"]), axis("4_massflux_g_cm2_s", r["massflux_kg_m2s"]/10))
                              for r in selected]
                    color = COLORS[int(case)+2]
                label = "Case "+case.replace("star", "*")+(" burning flux" if number == 4 else "")
                if case == "3star":
                    label = "Partial-T control (paper 3* unresolved)"
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
                        line([(axis("6_T_K", float(r["T_K"])), axis("6_ratio", float(r[key])))
                              for r in rows],
                             color, label, (72.3, 262.3, 230.8, 406.7), max(1, len(rows)//15))
                else:
                    xx = np.array([float(r["x_m"]) for r in raw])
                    temp = np.array([float(r["T_K"]) for r in raw])
                    # Original vector ticks: 0.0005 cm spans 18.5067 PDF points.
                    # Preserve physical width; apply only a front translation.
                    xp = figure7_coordinates(xx, temp)
                    bounds = (288.22, 54.725, 435.757, 189.356)
                    yp = (FIGURE7["temperature_intercept_points"]
                          +FIGURE7["temperature_points_per_K"]*temp)
                    line(list(zip(xp, yp)), COLORS[0], "T; align at 1500 K", bounds, max(1, len(raw)//30))
                    ys = np.array([[float(r["Y_"+n]) for n in names] for r in raw])
                    mole = ys/molecular_weights
                    mole /= mole.sum(axis=1)[:, None]
                    for name, color in zip(["H2", "O2", "HO2", "H2O2"], COLORS[1:]):
                        values = mole[:, names.index(name)]
                        points = [(float(x), FIGURE7["log_species_intercept_points"]
                                   +math.log10(v)*FIGURE7["log_species_points_per_decade"])
                                  for x, v in zip(xp, values) if v > 0]
                        line(points, color, name+" mole fraction", bounds, max(1, len(points)//30))
            else:
                text(page, (270, 224, 480, 240), "Case 5 stoichiometric profile pending", 8)
        if extra_legends:
            diagnostic_colors = dict(zip(CASES, COLORS))
            diagnostic_colors.update({
                ("massflux_g_cm2_s", "1"): COLORS[3],
                ("massflux_g_cm2_s", "2"): COLORS[4],
            })
            omitted += plot_diagnostics.draw(page, diagnostics, number,
                                               diagnostic_colors, axis, crop)
        for i, (color, label) in enumerate(legends):
            x = 18+(i % 2)*242
            y = legend_y+(i//2)*14
            page.draw_line((x, y+4), (x+17, y+4), color=color, width=.65, dashes="[2 2] 0")
            page.draw_circle((x+8.5, y+4), 1.35, color=color, fill=(1, 1, 1), width=.65)
            text(page, (x+22, y, x+237, y+13), label, 7)
        for i, (label, style) in enumerate(extra_legends, start=len(legends)):
            x, y = 18+(i % 2)*242, legend_y+(i//2)*14
            plot_diagnostics.marker(page, (x+8.5, y+4), style, (0, 0, 0))
            text(page, (x+22, y, x+237, y+13), label+" (case colors)", 7)
        notes = [
            "Computed: Burke 2012 N2 bath-gas kinetics; 100 atm; Tu=298 K assumed; "+a.transport+" transport.",
            "3*: partial-T control, not verified paper 3*. Cases 3-5: total-H equation; partial-molar diffusion enthalpies.",
            "Conductivity remains provisional.",
            "Grid refinement is recorded; agreement with the paper is not yet accepted.",
        ]
        if number == 2:
            notes = ["Existing critical-property audit, independent of hydrogen kinetics.",
                     "The known critical-pressure discrepancy remains unresolved. No parameters fitted."]
        if number == 6:
            notes.append("Paper's D definition is unspecified; three named quantities shown. Raster calibration approximate.")
        if number == 7:
            notes.append("Case 5 shown; x translated to the paper's 1500 K crossing; vector tick scale verified.")
        if omitted:
            notes.append(f"{omitted} samples outside the original axes are omitted, never clipped to the boundary.")
        if extra_legends:
            notes.append("Additional symbols are sensitivity controls; archived qualification limits still apply.")
        text(page, (18, 332+extra_height, 482, 396+extra_height), "\n".join(notes), 7)
        text(page, (18, 405+extra_height, 482, 420+extra_height), "Source: Liang et al., Proc. Combust. Inst. 37 (2019) 1733-1739, Fig. "+str(number), 7)
        page.get_pixmap(matrix=fitz.Matrix(3, 3)).save(a.output/f"figure-{number}.png")
        clipped[str(number)] = omitted
    report.save(a.output/"liang-hydrogen-figures-2-7.pdf")
    record = {"paper_sha256": PAPER_SHA, "runs": runs, "samples_outside_axes": clipped,
              "transport_variant": a.transport,
              "figure_7_alignment": "T=1500 K; translation only; finite paper window",
              "figure_7_calibration": FIGURE7,
              "original_caption_rectangles_points": CAPTIONS,
              "input_sha256": {name: hashlib.sha256(getattr(a, name).read_bytes()).hexdigest()
                               for name in ["manifest", "critical", "species"]},
              "input_paths": {name: str(getattr(a, name)) for name in ["manifest", "critical", "species"]},
              "axes_2_6_calibration_sha256": hashlib.sha256(CALIBRATION_PATH.read_bytes()).hexdigest(),
              "frame_tolerance_points": .02,
              "plot_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if a.diagnostics:
        record["diagnostics"] = diagnostics
        record["diagnostics_sha256"] = hashlib.sha256(a.diagnostics.read_bytes()).hexdigest()
        record["diagnostic_renderer_sha256"] = hashlib.sha256(
            Path(plot_diagnostics.__file__).read_bytes()).hexdigest()
    (a.output/"evidence.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
