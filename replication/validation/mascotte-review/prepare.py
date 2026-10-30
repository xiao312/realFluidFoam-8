"""Extract fixed paper targets; refresh explicit CFD profiles without acceptance."""
import argparse
import csv
import hashlib
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pymupdf


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf8")


def extract_vectors(page, specifications):
    paths = page.get_drawings()
    curves = []
    styles = {"M1": "[ 1.7241 .43101 .86203 .43101 ] 0", "M2": "[ 1.7241 1.7241 ] 0", "M3": "[] 0"}
    for panel in specifications:
        x0, x1 = panel["x_ticks_pt"]
        y0, y1 = panel["y_ticks_pt"]
        v0, v1 = panel["y_values_K"]
        for grid, index in panel["paths"].items():
            path = paths[index]
            if path["dashes"] != styles[grid] or len(path["items"]) < 90:
                raise ValueError(f"Unexpected path {index}: grid/style identity changed")
            if abs(path["rect"].x0 - x0) > .03 or abs(path["rect"].x1 - x1) > .03:
                raise ValueError(f"Unexpected panel extent at path {index}")
            points = []
            for item in path["items"]:
                if item[0] != "l":
                    raise ValueError("New curve primitive needs an explicit extraction policy")
                for point in item[1:]:
                    p = [point.x, point.y]
                    if not points or points[-1] != p:
                        points.append(p)
            points = np.asarray(points)
            radial = (points[:, 0] - x0) / (x1 - x0) * 20
            value = v0 + (points[:, 1] - y0) / (y1 - y0) * (v1 - v0)
            if not np.isfinite(value).all() or np.any(np.diff(radial) < -1e-6):
                raise ValueError(f"Nonfinite or reversed path {index}")
            # PDF clipping extends paths just beyond the axis by about 0.002 mm.
            # Retain those raw vertices in JSON; plots use the paper's 0..20 range.
            curves.append({"station_mm": panel["station_mm"], "statistic": panel["statistic"],
                           "grid": grid, "path_index": index, "radial_mm": radial.tolist(),
                           "temperature_K": value.tolist(), "raw_pdf_points": points.tolist(),
                           "stroke_width_pt": path["width"],
                           "reading_half_stroke_K": path["width"] / 2 * abs((v1 - v0) / (y1 - y0))})
    if len(curves) != 18:
        raise ValueError("Expected all eighteen paper curves")
    return curves


def read_cfd(csv_path, metadata_path):
    if not csv_path:
        return [], None
    if not metadata_path:
        raise ValueError("CFD profiles require --metadata")
    metadata = json.loads(metadata_path.read_text(encoding="utf8"))
    required = ["source_commit", "job_id", "mesh_identity", "statistics_kind", "sampling_start_s",
                "sampling_end_s", "sample_count", "injector_origin_m", "origin_qualified"]
    if any(key not in metadata for key in required):
        raise ValueError(f"Metadata requires {required}")
    kind = metadata["statistics_kind"]
    if kind not in ("instantaneous", "reynolds_time_mean"):
        raise ValueError("Unsupported statistic: do not silently mix Favre and Reynolds means")
    start, end = float(metadata["sampling_start_s"]), float(metadata["sampling_end_s"])
    if not np.isfinite([start, end, float(metadata["injector_origin_m"])]).all() or end < start:
        raise ValueError("Invalid sampling interval or origin")
    if int(metadata["sample_count"]) < 1 or not isinstance(metadata["origin_qualified"], bool):
        raise ValueError("Invalid sample count or origin qualification")
    if kind == "reynolds_time_mean" and (end <= start or int(metadata["sample_count"]) < 2):
        raise ValueError("Time mean requires multiple samples over a positive interval")
    with csv_path.open(newline="", encoding="utf8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in ("station_mm", "radial_mm", "T_mean_K"):
            row[key] = float(row[key])
        row["T_rms_K"] = float(row["T_rms_K"]) if row.get("T_rms_K", "").strip() else None
        if row["station_mm"] not in (15, 45, 70):
            raise ValueError("Only the three paper stations are supported")
        if not np.isfinite([value for value in row.values() if isinstance(value, float)]).all():
            raise ValueError("Nonfinite CFD profile")
        if kind == "instantaneous" and row["T_rms_K"] is not None:
            raise ValueError("An instantaneous profile cannot supply temporal RMS")
    metadata["csv_sha256"] = sha(csv_path)
    metadata["metadata_sha256"] = sha(metadata_path)
    return rows, metadata


def render(curves, rows, metadata, out):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.linewidth": .7})
    fig, axes = plt.subplots(2, 3, figsize=(11.5, 5.7), constrained_layout=True)
    metrics = []
    for column, station in enumerate((15, 45, 70)):
        samples = sorted((r for r in rows if r["station_mm"] == station), key=lambda r: r["radial_mm"])
        if samples and (len(samples) < 2 or any(b["radial_mm"] <= a["radial_mm"] for a, b in zip(samples, samples[1:]))):
            raise ValueError("Each supplied station needs at least two distinct increasing radial locations")
        for row_index, stat in enumerate(("mean", "rms")):
            ax = axes[row_index, column]
            selected = [c for c in curves if c["station_mm"] == station and c["statistic"] == stat]
            for curve in selected:
                grid = curve["grid"]
                ax.plot(curve["radial_mm"], curve["temperature_K"],
                        {"M1": "-.", "M2": "--", "M3": "-"}[grid],
                        color={"M1": ".65", "M2": ".4", "M3": ".05"}[grid], lw=1.25, label=f"Paper {grid}")
            field = "T_mean_K" if stat == "mean" else "T_rms_K"
            measured = [r for r in samples if r[field] is not None]
            if measured:
                x = np.array([r["radial_mm"] for r in measured])
                y = np.array([r[field] for r in measured])
                label = "Our instantaneous T" if metadata["statistics_kind"] == "instantaneous" else "Our time statistic"
                ax.plot(x, y, "o-", color="#c2410c", lw=1.6, ms=4, markevery=max(1, len(x)//18), label=label)
                if metadata["statistics_kind"] == "reynolds_time_mean" and metadata["origin_qualified"]:
                    ref = next(c for c in selected if c["grid"] == "M3")
                    inside = (x >= 0) & (x <= 20)
                    if np.any(inside):
                        error = y[inside] - np.interp(x[inside], ref["radial_mm"], ref["temperature_K"])
                        metrics.append({"station_mm": station, "statistic": stat, "n": int(inside.sum()),
                                        "rms_error_K": float(np.sqrt(np.mean(error**2))),
                                        "status": "descriptive comparison only; no acceptance assigned"})
            ax.set(xlim=(0, 20), ylim=(0, 2050 if stat == "mean" else 1500), xlabel="Radial position (mm)",
                   ylabel="Mean temperature (K)" if stat == "mean" else "Temperature RMS (K)")
            if row_index == 0:
                ax.set_title(f"Axial position {station} mm")
            ax.grid(alpha=.15)
    axes[0, 0].legend(frameon=False, fontsize=9)
    fig.suptitle("Cavalieri Figure 6 | " + ("explicit CFD sampling comparison" if rows else "paper references; CFD profiles pending"), fontsize=13)
    fig.savefig(out / "cavalieri-profiles.png", dpi=180)
    plt.close(fig)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cfd", type=Path)
    parser.add_argument("--metadata", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    specification = Path(__file__).with_name("targets.json")
    spec = json.loads(specification.read_text(encoding="utf8"))
    for target in spec["targets"]:
        path = args.pdf_dir / target["filename"]
        if sha(path) != target["paper"]["pdf_sha256"]:
            raise ValueError(f"Wrong PDF source: {target['filename']}")
    rows, metadata = read_cfd(args.cfd, args.metadata)
    paper = pymupdf.open(args.pdf_dir / spec["targets"][0]["filename"])
    curves = extract_vectors(paper[8], spec["cavalieri_vector_panels"])
    plan = {"targets": [t["id"] for t in spec["targets"]], "vector_curves": len(curves),
            "cfd_rows": len(rows), "out": str(args.out), "mode": "plan" if args.plan else "apply"}
    if args.plan:
        print(json.dumps(plan))
        return
    args.out.mkdir(parents=True, exist_ok=False)
    write_json(args.out / "targets.json", spec)
    write_json(args.out / "cavalieri-curves.json", {"schema": "cavalieri-figure6-vectors/v1", "curves": curves})
    metrics = render(curves, rows, metadata, args.out)
    sections = []
    references = []
    for target in spec["targets"]:
        ident = target["id"]
        doc = pymupdf.open(args.pdf_dir / target["filename"])
        doc[target["page_index"]].get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=pymupdf.Rect(target["crop_pt"]), alpha=False).save(args.out / f"{ident}.png")
        caption = html.escape(target["original_caption"])
        title = html.escape(target["paper"]["short"])
        left = '<img src="cavalieri-profiles.png" alt="Extracted paper profiles and explicit CFD comparison">' if ident.startswith("cavalieri") else '<div class="pending">CFD view pending<br>No fabricated result or optical equivalence.</div>'
        sections.append(f'<section id="{ident}"><h2>{title}: Figure {ident.split("fig")[-1].strip("-")}</h2><div class="pair"><div>{left}</div><div><img src="{ident}.png" alt="Original paper figure"><p>{caption}</p></div></div><p><a href="#ref-{ident}">Reference and rights</a></p><details><summary>Reusable comparison specification</summary><pre>{html.escape(json.dumps(target["plot_spec"],indent=2))}</pre></details></section>')
        references.append(f'<li id="ref-{ident}"><a href="{target["paper"]["url"]}">{html.escape(target["paper"]["title"])}</a>. {html.escape(target["paper"]["rights"])} <a href="#{ident}">Back to figure</a></li>')
    page = '<!doctype html><meta charset="utf-8"><title>G2 paper comparison preparation</title><style>body{font:16px/1.5 system-ui;margin:36px auto;max-width:1500px;padding:0 24px;color:#17212d}h1,h2{font-weight:600}.pair{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:start}img{width:100%;height:auto}section{border-top:1px solid #ddd;padding:28px 0}.pending{padding:80px 25px;background:#f2f4f6;text-align:center;color:#526172}pre{white-space:pre-wrap;font-size:13px}a{color:#145a9e}@media(max-width:850px){.pair{grid-template-columns:1fr}}</style><h1>G2 paper targets</h1><p>Prepared references for existing ladder entries. Short CFD diagnostics and statistical paper comparisons are reported separately. No target is accepted by this preparation tool.</p>'
    if metadata:
        page += '<details open><summary>Actual CFD source and sampling</summary><pre>' + html.escape(json.dumps(metadata, indent=2)) + '</pre></details>'
    page += ''.join(sections) + '<h2>References</h2><ol>' + ''.join(references) + '</ol>'
    (args.out / "index.html").write_text(page, encoding="utf8")
    receipt = {"schema": "g2-paper-preparation/v1", **plan, "source_sha256": sha(__file__),
               "specification_sha256": sha(specification), "cfd_metadata": metadata, "metrics": metrics,
               "scientific_acceptance": False, "artifacts": {p.name: sha(p) for p in sorted(args.out.iterdir()) if p.is_file()}}
    write_json(args.out / "receipt.json", receipt)
    print(json.dumps({"out": str(args.out), "curves": len(curves), "acceptance": False}))


if __name__ == "__main__":
    main()
