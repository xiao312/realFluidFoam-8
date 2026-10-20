"""Render selected Figure 7 controls at paper scale, without selecting a model."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from plot import CAPTIONS, COLORS, FIGURE7, PANELS, PAPER_SHA, text


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def draw_curve(page, rows, color, crop):
    """Keep missing/out-of-range intervals separate; use source-page coordinates."""
    import pymupdf as fitz
    bounds = (288.22, 54.725, 435.757, 189.356)
    segments, visible = [[]], []
    omitted = 0
    for row in rows:
        cm = float(row["x_relative_um"])*1e-4+FIGURE7["paper_1500K_x_cm"]
        x = FIGURE7["x_points_per_cm"]*cm+FIGURE7["x_intercept_points"]
        value = float(row["value"])
        if row["series"] == "T":
            y = FIGURE7["temperature_intercept_points"]+FIGURE7["temperature_points_per_K"]*value
        elif value > 0:
            y = FIGURE7["log_species_intercept_points"]+FIGURE7["log_species_points_per_decade"]*math.log10(value)
        else:
            y = math.inf
        if bounds[0]-.02 <= x <= bounds[2]+.02 and bounds[1]-.02 <= y <= bounds[3]+.02:
            point = fitz.Point(270+x-crop.x0, 56+y-crop.y0)
            segments[-1].append(point)
            visible.append(point)
        else:
            omitted += 1
            if segments[-1]:
                segments.append([])
    for segment in segments:
        if len(segment) > 1:
            page.draw_polyline(segment, color=color, width=.65, dashes="[2 2] 0")
    for point in visible[::max(1, len(visible)//22)]:
        page.draw_circle(point, 1.35, color=color, fill=(1, 1, 1), width=.65)
    return omitted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("paper", "comparison", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--jobs", required=True, help="Explicit comma-separated completed job IDs")
    args = parser.parse_args()
    jobs = [int(value) for value in args.jobs.split(",")]
    report_path = args.comparison/"summary.json"
    aligned_path = args.comparison/"aligned-profiles.csv"
    evidence = json.loads(report_path.read_text(encoding="utf-8"))
    if (digest(args.paper) != PAPER_SHA or
            evidence["inputs_sha256"][args.paper.name] != PAPER_SHA or
            digest(aligned_path) != evidence["outputs_sha256"]["aligned-profiles.csv"]):
        raise ValueError("Source paper or aligned data differs from its comparison record")
    runs = {run["job"]: run for run in evidence["runs"]}
    if not jobs or len(set(jobs)) != len(jobs) or not set(jobs) <= runs.keys():
        raise ValueError("Choose unique jobs present in the comparison")
    if args.output.exists():
        raise ValueError("Choose a new artifact directory")
    print(json.dumps(dict(jobs=jobs, pages=len(jobs), output=str(args.output),
                          scientific_acceptance=False, remote_writes=False)))
    if args.action == "plan":
        return
    import pymupdf as fitz
    with aligned_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    source, document = fitz.open(args.paper), fitz.open()
    page_index, box, _ = PANELS[7]
    crop, caption = fitz.Rect(box), fitz.Rect(CAPTIONS[7])
    args.output.mkdir(parents=True)
    records = []
    variants = {"baseline": "no Soret", "conservative": "conservative residual",
                "soret-baseline": "Cantera 3.2 Soret",
                "manual-soret-baseline": "manual Soret formula"}
    for job in jobs:
        run = runs[job]
        page = document.new_page(width=500, height=440)
        label = variants.get(run["variant"], run["variant"])
        text(page, (18, 9, 482, 35), f"Liang Figure 7: Case {run['case']}, {label}", 11)
        for x, title in ((18, "Original paper (case unspecified)"),
                         (270, "Paper + our calculation (open symbols)")):
            text(page, (x, 37, x+212, 51), title, 8)
            page.show_pdf_page(fitz.Rect(x, 56, x+crop.width, 56+crop.height),
                               source, page_index, clip=crop)
        target = fitz.Rect(18+caption.x0-crop.x0, 56+caption.y0-crop.y0,
                           18+caption.x1-crop.x0, 56+caption.y1-crop.y0)
        page.show_pdf_page(target, source, page_index, clip=caption)
        selected = [row for row in rows if row["profile"] == run["label"]]
        if {row["series"] for row in selected} != {"T", "H2", "O2", "HO2", "H2O2"}:
            raise ValueError("Incomplete selected profile")
        omitted = 0
        for i, (species, color) in enumerate(zip(("T", "H2", "O2", "HO2", "H2O2"), COLORS)):
            omitted += draw_curve(page, [r for r in selected if r["series"] == species], color, crop)
            x, y = 18+(i % 2)*242, 267+(i//2)*14
            page.draw_line((x, y+4), (x+17, y+4), color=color, width=.65, dashes="[2 2] 0")
            page.draw_circle((x+8.5, y+4), 1.35, color=color, fill=(1, 1, 1), width=.65)
            text(page, (x+22, y, x+237, y+13),
                 "Temperature (K)" if species == "T" else species+" mole fraction", 7)
        metric = run["metrics"]
        reference = evidence["paper_metrics"]
        errors = [100*(metric[name+"_peak_X"]/reference[name+"_peak_X"]-1)
                  for name in ("HO2", "H2O2")]
        notes = [
            f"100 atm, Tu=298 K, phi=1; Burke author-pair transport; job {job}.",
            f"Speed {run['speed_cm_s']:.6f} cm/s; T=500-2000 K width {metric['width_T500_T2000_um']:.4f} um.",
            f"HO2/H2O2 peak errors {errors[0]:+.3f}% / {errors[1]:+.3f}%; no species or spatial rescaling.",
            "Only the 1500 K crossing is translated. Paper case and Soret setting remain unidentified.",
            "Native flux/conservation qualification is separate. Graphical agreement is not full validation.",
            f"{omitted} out-of-axis samples omitted; source {run['source'][:12]}.",
        ]
        text(page, (18, 320, 482, 413), "\n".join(notes), 7)
        text(page, (18, 423, 482, 438),
             "Liang et al., Proc. Combust. Inst. 37 (2019) 1733-1739, Figure 7.", 7)
        image = args.output/f"job-{job}.png"
        page.get_pixmap(matrix=fitz.Matrix(3, 3)).save(image)
        records.append(dict(job=job, source=run["source"], profile_sha256=run["sha256"]["profile.csv"],
                            samples_outside_axes=omitted, image_sha256=digest(image)))
    pdf = args.output/"liang-figure7-structure-controls.pdf"
    document.save(pdf)
    manifest = dict(
        jobs=records, paper_sha256=PAPER_SHA, comparison_sha256=digest(report_path),
        aligned_data_sha256=digest(aligned_path), script_sha256=digest(Path(__file__)),
        geometry_script_sha256=digest(Path(__file__).with_name("plot.py")),
        pdf_sha256=digest(pdf), alignment="1500 K translation only",
        scientific_acceptance=False)
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
