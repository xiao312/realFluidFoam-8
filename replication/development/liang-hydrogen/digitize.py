"""Extract calibrated Liang Figures 3/4/5 vectors; never use simulation results."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pymupdf as fitz

PAPER_SHA = "24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe"
COLORS = {"black": (0, 0, 0), "red": (.81961, 0, 0),
          "blue": (.17647, .17647, 1), "magenta": (1, 0, 1)}
FIGURES = {
    "3": {
        "page": 3, "clip": [28, 50, 232, 225],
        "xticks": (list(range(123, 129)), np.arange(1, 2.01, .2).tolist()),
        "yticks": {"speed_cm_s": (list(range(144, 148)), [50, 60, 70, 80])},
        "series": [
            ("1", "speed_cm_s", "line", "red", list(range(0, 4))),
            ("2", "speed_cm_s", "line", "blue", list(range(4, 9))),
            ("3star", "speed_cm_s", "marker", "red", list(range(9, 23))),
            ("3", "speed_cm_s", "marker", "blue", list(range(23, 36))),
            ("4", "speed_cm_s", "dashed", "black", list(range(36, 70))),
            ("5", "speed_cm_s", "dashed", "magenta", list(range(70, 105))),
        ],
    },
    "4": {
        "page": 3, "clip": [248, 50, 454, 211],
        "xticks": (list(range(284, 289)), [1, 1.5, 2, 2.5, 3]),
        "yticks": {
            "density_g_cm3": (list(range(330, 341)), np.linspace(.05, .1, 11).tolist()),
            "massflux_g_cm2_s": (list(range(370, 378)), list(range(8))),
        },
        "series": [
            ("1", "density_g_cm3", "line", "black", list(range(202, 210))),
            ("1", "massflux_g_cm2_s", "line", "red", list(range(210, 223))),
            ("2", "density_g_cm3", "marker", "black", list(range(223, 241))),
            ("2", "massflux_g_cm2_s", "marker", "red", list(range(241, 263))),
        ],
    },
    "5": {
        "page": 4, "clip": [47, 50, 239, 215],
        "xticks": (list(range(159, 170)), np.arange(.85, 1.351, .05).tolist()),
        "yticks": {"Tb_K": (list(range(198, 204)), list(range(2250, 2501, 50)))},
        "series": [
            ("1", "Tb_K", "marker", "black", list(range(10))),
            ("2", "Tb_K", "line", "black", list(range(10, 16))),
            ("3star", "Tb_K", "dashed", "blue", list(range(16, 84))),
            ("3", "Tb_K", "dashed", "red", list(range(84, 118))),
        ],
    },
}


def calibration(drawings, tick_spec, coordinate):
    ids, values = tick_spec
    points = []
    for index in ids:
        d = drawings[index]
        if len(d["items"]) != 1 or d["items"][0][0] != "l":
            raise ValueError("Expected one tick line")
        ends = d["items"][0][1:]
        if abs(ends[0][coordinate] - ends[1][coordinate]) > .002:
            raise ValueError("Tick orientation changed")
        points.append(float(ends[0][coordinate]))
    coefficients = np.polyfit(points, values, 1)
    residual = max(abs(np.polyval(coefficients, points)-values))
    if residual / abs(coefficients[0]) > .025:
        raise ValueError("Axis ticks are not linear within 0.025 PDF points")
    return {"drawing_ids": ids, "tick_points": points, "tick_values": values,
            "coefficients": coefficients.tolist(), "max_residual": float(residual)}


def extract_series(drawings, spec, xaxis, yaxis):
    case, quantity, kind, color, ids = spec
    xfit, yfit = xaxis["coefficients"], yaxis["coefficients"]
    rows, segments = [], []
    for index in ids:
        d = drawings[index]
        observed = d["fill"] if kind == "marker" else d["color"]
        if observed is None or max(abs(a-b) for a, b in zip(observed, COLORS[color])) > 1e-5:
            raise ValueError("Selected path color changed")
        if any(item[0] != "l" for item in d["items"]):
            raise ValueError("Selected path contains non-line elements")
        if kind == "marker":
            vertices = sorted(set(tuple(point) for item in d["items"] for point in item[1:]))
            if len(vertices) != 3:
                raise ValueError("Expected a filled triangle")
            r = d["rect"]
            xp, yp = (r.x0+r.x1)/2, (r.y0+r.y1)/2
            rows.append({
                "drawing_id": index, "x_pt": xp, "y_pt": yp,
                "phi": float(np.polyval(xfit, xp)), "value": float(np.polyval(yfit, yp)),
                "uncertainty": (r.height/2+.025)*abs(yfit[0]),
                "marker_bounds_pt": list(r),
                "centroid_pt": np.mean(vertices, axis=0).tolist(),
                "marker_vertices_pt": vertices, "origin": "bounding-box midpoint",
            })
        else:
            uncertainty = (d["width"]/2+.025)*abs(yfit[0])
            for item in d["items"]:
                p, q = [tuple(point) for point in item[1:]]
                segments.append({"drawing_id": index, "p_pt": p, "q_pt": q})
                for xp, yp in (p, q):
                    rows.append({"drawing_id": index, "x_pt": xp, "y_pt": yp,
                                 "phi": float(np.polyval(xfit, xp)),
                                 "value": float(np.polyval(yfit, yp)),
                                 "uncertainty": uncertainty, "origin": "path vertex"})
    rows.sort(key=lambda row: row["phi"])
    return {"case": case, "quantity": quantity, "kind": kind, "color": color,
            "drawing_ids": ids, "rows": rows, "segments": segments,
            "phi_range": [rows[0]["phi"], rows[-1]["phi"]]}


def sample(series, phi, marker_tolerance=.0003):
    """Return native marker or labelled line interpolation; never extrapolate."""
    rows = series["rows"]
    if series["kind"] == "marker":
        row = min(rows, key=lambda value: abs(value["phi"]-phi))
        if abs(row["phi"]-phi) > marker_tolerance:
            return None
        return {"phi": phi, "reference_phi": row["phi"], "value": row["value"],
                "uncertainty": row["uncertainty"], "method": "native marker",
                "drawing_ids": [row["drawing_id"]]}
    if phi < rows[0]["phi"] or phi > rows[-1]["phi"]:
        return None
    for lo, hi in zip(rows, rows[1:]):
        if lo["phi"] <= phi <= hi["phi"] and hi["phi"] > lo["phi"]:
            fraction = (phi-lo["phi"])/(hi["phi"]-lo["phi"])
            value = lo["value"]+fraction*(hi["value"]-lo["value"])
            same_path = lo["drawing_id"] == hi["drawing_id"]
            tiny_gap = hi["x_pt"]-lo["x_pt"] < .003
            bridge = not same_path and not tiny_gap
            extra = max(abs(value-lo["value"]), abs(value-hi["value"])) if bridge else 0
            return {"phi": phi, "value": value,
                    "uncertainty": max(lo["uncertainty"], hi["uncertainty"])+extra,
                    "method": "linear dash-gap bridge" if bridge else "linear path interpolation",
                    "bracket_phi": [lo["phi"], hi["phi"]],
                    "drawing_ids": [lo["drawing_id"], hi["drawing_id"]]}
    return None


def render_overlay(document, figure, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    clip = fitz.Rect(figure["clip_pt"])
    pix = document[figure["page_index"]].get_pixmap(matrix=fitz.Matrix(5, 5), clip=clip)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    count = len(figure["series"])
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    for axis, series in zip(axes.flat, figure["series"]):
        axis.imshow(image[:, :, :3], extent=(clip.x0, clip.x1, clip.y1, clip.y0))
        rows = series["rows"]
        selected = rows if series["kind"] == "marker" else rows[::max(1, len(rows)//55)]
        axis.scatter([r["x_pt"] for r in selected], [r["y_pt"] for r in selected],
                     s=22, facecolors="none", edgecolors="#00945b", linewidths=.7)
        axis.set_xlim(clip.x0, clip.x1); axis.set_ylim(clip.y1, clip.y0)
        axis.set_title(f"Case {series['case']}: {series['quantity']}", fontsize=11)
        axis.axis("off")
    for axis in list(axes.flat)[count:]:
        axis.axis("off")
    fig.suptitle("Original PDF with extracted positions (green rings); no simulation inputs", fontsize=14)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("paper", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.paper.read_bytes()).hexdigest() != PAPER_SHA:
        raise ValueError("Expected hash-pinned Liang paper")
    if args.output.exists():
        raise ValueError("Output exists; choose a new directory")
    document = fitz.open(args.paper)
    figures = {}
    for number, config in FIGURES.items():
        drawings = document[config["page"]].get_drawings()
        xaxis = calibration(drawings, config["xticks"], 0)
        yaxes = {key: calibration(drawings, ticks, 1) for key, ticks in config["yticks"].items()}
        series = [extract_series(drawings, spec, xaxis, yaxes[spec[1]]) for spec in config["series"]]
        figures[number] = {"page_index": config["page"], "clip_pt": config["clip"],
                           "xaxis": xaxis, "yaxes": yaxes, "series": series}
    print(json.dumps({"figures": list(figures), "series": sum(len(f["series"]) for f in figures.values()),
                      "output": str(args.output), "reference": "Published vector geometry; not author numerical data"}))
    if args.action == "plan":
        return
    args.output.mkdir(parents=True)
    samples = []
    for number, figure in figures.items():
        for series in figure["series"]:
            native = [row["phi"] for row in series["rows"]]
            phis = sorted(set(round(x, 4) for x in native)) if series["kind"] == "marker" else np.arange(.6, 3.001, .05)
            for phi in phis:
                row = sample(series, float(phi))
                if row:
                    samples.append({"figure": number, "case": series["case"],
                                    "quantity": series["quantity"], **row})
        render_overlay(document, figure, args.output/f"figure-{number}-overlay.png")
    evidence = {
        "paper_sha256": PAPER_SHA, "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "figures": figures, "samples": samples,
        "limitations": [
            "Values describe published vector geometry, not author numerical data.",
            "Triangle symbol origin is not documented; midpoint values carry the full half-height uncertainty.",
            "Line uncertainty is half stroke width plus 0.025 PDF points; no statistical confidence level is implied.",
            "Dash-gap interpolation is explicitly flagged and adds the endpoint-spread allowance.",
            "Marker series are not interpolated. No extrapolation beyond any printed series.",
            "PDF axes clip low Figure 3 speeds; phi=1 is not available and must not be inferred.",
        ],
    }
    (args.output/"reference.json").write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8", newline="\n")
    with (args.output/"samples.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = ["figure", "case", "quantity", "phi", "value", "uncertainty", "method"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader(); writer.writerows(samples)


if __name__ == "__main__":
    main()
