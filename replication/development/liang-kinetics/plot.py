"""Overlay completed ideal methane controls on the original Figure 8(b)."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

PAPER_SHA = "24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe"
CLIP = (28, 240, 229, 416)
CAPTION = (31, 424, 228, 452)
COLORS = [(0, .48, .27), (.75, .35, .02), (.55, .15, .65),
          (.1, .36, .8), (.15, .6, .65), (.7, .15, .3)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def reference_key(name):
    for prefix in ["GRI", "USC", "HP"]:
        if name.startswith(prefix):
            return prefix+"-Case1"
    raise ValueError(f"Unknown comparison mechanism: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("paper", "manifest", "reference", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--gri-sweep", type=Path)
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    if digest(args.paper) != PAPER_SHA or reference["paper_sha256"] != PAPER_SHA:
        parser.error("The source PDF must match the measured reference.")
    if args.output.exists():
        parser.error("Use a new output directory.")
    rows = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    plotted, pending, seen = [], [], set()
    for row in rows:
        result = Path(row["result"])
        if not (result/"completed.txt").exists():
            pending.append(row["job"])
            continue
        levels = read(result/"refinement.csv")
        if len(levels) < 2 or levels[-1]["case"] != "1":
            raise ValueError("Expected at least two converged ideal levels.")
        last = levels[-1]
        key = (row["mechanism"], row["transport"], float(last["phi"]))
        if key in seen:
            raise ValueError(f"Select one run for duplicate display point {key}.")
        seen.add(key)
        plotted.append(dict(job=row["job"], mechanism=key[0], transport=key[1],
                            phi=key[2], speed_cm_s=float(last["speed_cm_s"]),
                            grid_change=abs(float(last["speed_cm_s"])/
                                            float(levels[-2]["speed_cm_s"])-1),
                            result_sha256=digest(result/"refinement.csv")))
    if args.gri_sweep:
        for row in json.loads(args.gri_sweep.read_text())["results"]:
            if row["stage"] == 1 and row["screen_passed"]:
                plotted.append(dict(job=row["job"], mechanism="GRI sweep",
                                    transport="lj", phi=float(row["phi"]),
                                    speed_cm_s=row["speed_cm_s"],
                                    grid_change=row["last_refinement_relative_change"]))
    print(json.dumps(dict(completed=len(plotted), pending=pending,
                          output=str(args.output), remote_writes=False)))
    if args.action == "plan":
        return
    import pymupdf as fitz
    args.output.mkdir(parents=True)
    source = fitz.open(args.paper)
    image_rect = source[5].get_image_rects(reference["image_xref"])[0]
    image = source.extract_image(reference["image_xref"])
    if hashlib.sha256(image["image"]).hexdigest() != reference["image_sha256"]:
        raise ValueError("Unexpected original figure bytes.")
    xfit = reference["calibration"]["x_fit"]
    yfit = reference["calibration"]["y_fit"]
    def point(phi, speed):
        pixel_x, pixel_y = (phi-xfit[1])/xfit[0], (speed-yfit[1])/yfit[0]
        return fitz.Point(270+image_rect.x0-CLIP[0]+pixel_x*image_rect.width/image["width"],
                          60+image_rect.y0-CLIP[1]+pixel_y*image_rect.height/image["height"])
    document = fitz.open()
    page = document.new_page(width=500, height=410)
    def text(rect, value, size=8):
        if page.insert_textbox(fitz.Rect(rect), value, fontsize=size,
                              fontname="helv", lineheight=1.05) < 0:
            raise ValueError("Text overflow: "+value)
    text((18, 12, 482, 35), "Liang Figure 8(b): methane kinetic mechanisms", 12)
    text((18, 40, 230, 56), "Original paper")
    text((270, 40, 482, 56), "Paper + ideal controls (open symbols)")
    for left in [18, 270]:
        page.show_pdf_page(fitz.Rect(left, 60, left+201, 236), source, 5,
                           clip=fitz.Rect(CLIP))
    groups = defaultdict(list)
    comparison = []
    for row in plotted:
        groups[row["mechanism"]+"; "+row["transport"]].append(row)
        samples = reference["series"][reference_key(row["mechanism"])]["samples"]
        matches = [s for s in samples if abs(s["phi"]-row["phi"]) < 1e-8]
        if matches:
            sample = matches[0]
            error = row["speed_cm_s"]-sample["speed_cm_s"]
            allowance = max(.05, .01*abs(sample["speed_cm_s"]))+sample["uncertainty_cm_s"]
            comparison.append(dict(job=row["job"], series=row["mechanism"],
                transport=row["transport"], phi=row["phi"],
                computed_cm_s=row["speed_cm_s"], reference_cm_s=sample["speed_cm_s"],
                reading_allowance_cm_s=sample["uncertainty_cm_s"], error_cm_s=error,
                comparison_screen=abs(error) <= allowance))
    for i, (label, values) in enumerate(sorted(groups.items())):
        color = COLORS[i % len(COLORS)]
        values.sort(key=lambda r: r["phi"])
        points = [point(r["phi"], r["speed_cm_s"]) for r in values]
        if any(not (.8 <= r["phi"] <= 1.45 and 2 <= r["speed_cm_s"] <= 8) for r in values):
            raise ValueError("Out-of-panel data; inspect before rendering.")
        if len(points) > 1:
            page.draw_polyline(points, color=color, width=.65, dashes="[2 2] 0")
        for dot in points:
            page.draw_circle(dot, 1.35, color=color, fill=(1, 1, 1), width=.65)
        x, y = 18+(i % 2)*242, 279+(i//2)*14
        page.draw_line((x, y+4), (x+17, y+4), color=color, width=.65)
        page.draw_circle((x+8, y+4), 1.35, color=color, fill=(1, 1, 1), width=.65)
        text((x+22, y, x+239, y+13), label, 6.7)
    page.show_pdf_page(fitz.Rect(18, 244, 215, 272), source, 5,
                       clip=fitz.Rect(CAPTION))
    text((18, 332, 482, 386),
         "100 atm, 298 K; full author USC II / HP 2017 releases. Liang's methane subsets are unprovided.\n"
         "Only Case 1 is computed here. Hashemi is blocked by a negative published rate.\n"
         "Steady numerical guesses are distinct from transient CFD restarts. Comparison is not accepted.", 7)
    text((18, 392, 482, 406), "Source: Liang et al., PCI 37 (2019) 1733-1739, Figure 8(b).", 7)
    page.get_pixmap(matrix=fitz.Matrix(3, 3)).save(args.output/"figure-8b.png")
    document.save(args.output/"liang-figure-8b.pdf")
    if comparison:
        with (args.output/"comparison.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(comparison[0]))
            writer.writeheader()
            writer.writerows(comparison)
    record = dict(paper_sha256=PAPER_SHA, plotted=plotted, pending_jobs=pending,
                  comparison=comparison, scientific_acceptance=False,
                  input_sha256={k: digest(getattr(args, k)) for k in
                                ["manifest", "reference", "gri_sweep"] if getattr(args, k)})
    record["plot_script_sha256"] = digest(Path(__file__))
    (args.output/"evidence.json").write_text(json.dumps(record, indent=2)+"\n",
                                            encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
