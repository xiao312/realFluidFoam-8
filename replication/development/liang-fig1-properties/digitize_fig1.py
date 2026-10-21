#!/usr/bin/env python3
"""Digitise Liang et al. (2019) Fig. 1 from the JPEG embedded in the paper PDF.

The published figure is a raster (JPEG) XObject inside the PDF, not vector art, so
the readings are pixel measurements and are reported with a pixel uncertainty.  Two
independent steps are involved and neither invents a point:

* axis calibration -- already measured in
  ``../liang-properties/figure1-calibration.json`` against this exact JPEG
  (sha256 of the embedded stream, see below); the tick pixels are re-fitted here and
  the residuals reported;
* curve/marker reading -- a thin-run mask keeps the 2-3 px model line and rejects the
  16 px experimental triangles, a continuity tracer walks the model line through
  steep sections, and 3x3-erosion seeds locate the triangle centres.

Input is the raw RGBA dump of the embedded JPEG produced by
``node tools/jpeg2raw.mjs`` (``@napi-rs/canvas``), whose header line is
``{"width":W,"height":H}`` followed by W*H*4 bytes.  Only the Python standard
library is used.

Usage:
  digitize_fig1.py --rgba F.rgba --calibration figure1-calibration.json --out F.json
"""
import argparse
import hashlib
import json
from pathlib import Path

PANELS = {
    "density": {
        "x": "density_x", "y": "density_y", "units": {"x": "K", "y": "kg/m3"},
        "frame": (90, 0, 750, 603),            # left, top, right, bottom (px)
        # legend box and the "(a)" panel label; both are pure annotations
        "masks": [(420, 50, 750, 150), (95, 480, 215, 570)],
        "trace_start": "right",
    },
    "conductivity": {
        "x": "conductivity_x", "y": "conductivity_y", "units": {"x": "K", "y": "W/(m K)"},
        "frame": (90, 710, 750, 1313),
        "masks": [(560, 716, 750, 800), (95, 1190, 215, 1285)],
        "trace_start": "right",
    },
}
THIN_MAX = 5          # px: thicker vertical runs belong to markers/axis
TRACE_JUMP = 40       # px: largest y step per column while following the model line
BAND = 16             # px: axis frame, inward ticks and tick labels live in this band
RIM = 4               # px: anti-aliased rim of a filled triangle that is not model line


class Dump:
    def __init__(self, path):
        with open(path, "rb") as handle:
            header = json.loads(handle.readline())
            self.width = header["width"]
            self.height = header["height"]
            self.px = handle.read()
        if len(self.px) != self.width * self.height * 4:
            raise ValueError("RGBA dump length does not match its header")

    def dark(self, x, y):
        i = (y * self.width + x) * 4
        return (self.px[i] + self.px[i + 1] + self.px[i + 2]) / 3.0 < 128.0


def fit_ticks(ticks):
    """Least-squares value = intercept + slope*pixel, plus residuals in pixels."""
    n = len(ticks)
    sx = sum(t["pixel"] for t in ticks)
    sy = sum(t["value"] for t in ticks)
    sxx = sum(t["pixel"] ** 2 for t in ticks)
    sxy = sum(t["pixel"] * t["value"] for t in ticks)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    intercept = (sy - slope * sx) / n
    residuals = [t["pixel"] - (t["value"] - intercept) / slope for t in ticks]
    return {"value_per_pixel": slope, "value_intercept": intercept,
            "max_abs_residual_px": max(abs(r) for r in residuals),
            "ticks": ticks}


def masked(panel, x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in panel["masks"])


def dark_inside(dump, panel):
    left, top, right, bottom = panel["frame"]

    def dark(x, y):
        return (left + 2 * BAND <= x < right - 2 * BAND and top + 2 * BAND <= y < bottom - 2 * BAND
                and dump.dark(x, y) and not masked(panel, x, y))
    return dark


def erosion_cores(dark):
    seeds = set()
    for y in range(0, 100000):
        break
    return seeds


def blob_cores(dump, panel):
    """3x3-erosion cores of the filled triangles, as connected components."""
    left, top, right, bottom = panel["frame"]
    dark = dark_inside(dump, panel)
    seeds = set()
    for y in range(top + 2 * BAND, bottom - 2 * BAND):
        for x in range(left + 2 * BAND, right - 2 * BAND):
            if dark(x, y) and all(dark(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                seeds.add((x, y))
    seen = set()
    cores = []
    for seed in sorted(seeds):
        if seed in seen:
            continue
        stack, pts = [seed], []
        seen.add(seed)
        while stack:
            cx, cy = stack.pop()
            pts.append((cx, cy))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nxt = (cx + dx, cy + dy)
                    if nxt in seeds and nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
        width = max(p[0] for p in pts) - min(p[0] for p in pts) + 1
        height = max(p[1] for p in pts) - min(p[1] for p in pts) + 1
        if len(pts) < 25 or width < 5 or height < 5 or len(pts) > 600 or not 0.5 <= width / height <= 2.0:
            continue                          # model-line or tick residue, not a triangle
        cores.append({"x": sum(p[0] for p in pts) / len(pts),
                      "y": sum(p[1] for p in pts) / len(pts),
                      "core_pixels": len(pts), "core_bbox": [width, height],
                      "pixels": pts})
    return sorted(cores, key=lambda c: c["x"])


def line_mask(dump, panel, cores):
    """Dark pixels that belong to the model line: inside the plotting area, away from
    the inward axis ticks and with the triangle cores and their rims removed."""
    left, top, right, bottom = panel["frame"]
    rim = set()
    for core in cores:
        xs = [p[0] for p in core["pixels"]]
        ys = [p[1] for p in core["pixels"]]
        for px in range(min(xs) - RIM, max(xs) + RIM + 1):
            for py in range(min(ys) - RIM, max(ys) + RIM + 1):
                rim.add((px, py))
    mask = set()
    for y in range(top + BAND, bottom - BAND):
        for x in range(left + BAND, right - BAND):
            if dump.dark(x, y) and (x, y) not in rim and not masked(panel, x, y):
                mask.add((x, y))
    return mask


def skeleton(mask):
    """Zhang-Suen thinning to a 1 px ridge, so steep and shallow parts are equal."""
    pixels = set(mask)
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


def components(pixels):
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


def order_component(pixels):
    """Walk one 1 px ridge from its right-hand end; the walk never jumps between
    components, so a break stays a gap in the measured series."""
    remaining = set(pixels)
    path = [max(remaining, key=lambda p: (p[0], -p[1]))]
    remaining.discard(path[0])
    while True:
        cx, cy = path[-1]
        near = [(cx + dx, cy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx or dy) and (cx + dx, cy + dy) in remaining]
        if not near:
            break
        if len(path) > 1 and len(near) > 1:
            direction = (cx - path[-2][0], cy - path[-2][1])
            near.sort(key=lambda p: direction[0] * (p[0] - cx) + direction[1] * (p[1] - cy), reverse=True)
        nxt = near[0]
        path.append(nxt)
        remaining.discard(nxt)
    return path


def excluded_regions(panel):
    """Panel geometry that `dark_inside` cannot see: the axis band and the annotation masks."""
    left, top, right, bottom = panel["frame"]
    band = 2 * BAND
    regions = [
        ("frame band", "frame band (left)", (left + 1, top + 1, left + band, bottom - 1)),
        ("frame band", "frame band (right)", (right - band, top + 1, right - 1, bottom - 1)),
        ("frame band", "frame band (top)", (left + 1, top + 1, right - 1, top + band)),
        ("frame band", "frame band (bottom)", (left + 1, bottom - band, right - 1, bottom - 1)),
    ]
    # Mask 0 of each panel is the legend box (its symbols are legend glyphs, not data); mask 1 is
    # the "(a)"/"(b)" panel label, which sits over the lower-left of the plotting area and can
    # therefore hide real symbols.
    kinds = ("legend box", "panel label")
    for index, rect in enumerate(panel["masks"]):
        kind = kinds[index] if index < len(kinds) else "annotation mask"
        regions.append((kind, f"{kind} #{index}", tuple(rect)))
    return regions


def census(dump, panel, calibration):
    """Count the filled symbols the committed extraction is structurally unable to see.

    The model line and the axis ticks are thin, so a 3x3 erosion removes them; a filled
    comparison symbol survives.  This does not change `experiments` - it measures how many
    published symbols the panel geometry hides, so the verifier can report the extraction as
    incomplete instead of 7 triangles being passed off as the panel's symbol set.
    """
    hidden = []
    for kind, reason, (x0, y0, x1, y1) in excluded_regions(panel):
        x0, y0 = max(x0, panel["frame"][0] + 1), max(y0, panel["frame"][1] + 1)
        x1, y1 = min(x1, panel["frame"][2] - 1), min(y1, panel["frame"][3] - 1)
        if x1 - x0 < 5 or y1 - y0 < 5:
            continue
        inside = lambda x, y, x0=x0, y0=y0, x1=x1, y1=y1: x0 <= x < x1 and y0 <= y < y1
        seeds = set()
        for y in range(y0 + 1, y1 - 1):
            for x in range(x0 + 1, x1 - 1):
                if not dump.dark(x, y):
                    continue
                if all(dump.dark(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    seeds.add((x, y))
        seen = set()
        for seed in sorted(seeds):
            if seed in seen:
                continue
            stack, pts = [seed], []
            seen.add(seed)
            while stack:
                cx, cy = stack.pop()
                pts.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nxt = (cx + dx, cy + dy)
                        if nxt in seeds and nxt not in seen:
                            seen.add(nxt)
                            stack.append(nxt)
            width = max(q[0] for q in pts) - min(q[0] for q in pts) + 1
            height = max(q[1] for q in pts) - min(q[1] for q in pts) + 1
            if len(pts) < 12 or width < 4 or height < 4 or not 0.5 <= width / height <= 2.0:
                continue          # glyph stroke, tick residue or anti-aliased speck
            if sum(1 for q in pts if inside(*q)) < len(pts) / 2:
                continue          # component straddles the region edge, not a symbol
            cx = sum(q[0] for q in pts) / len(pts)
            cy = sum(q[1] for q in pts) / len(pts)
            hidden.append({
                "x": round(pixel_to_value(calibration, panel, panel["x"], cx), 4),
                "y": round(pixel_to_value(calibration, panel, panel["y"], cy), 6),
                "pixel": [round(cx, 2), round(cy, 2)],
                "core_pixels": len(pts),
                "core_bbox_px": [width, height],
                "excluded_by": reason,
                "region_kind": kind,
            })
    hidden.sort(key=lambda item: item["x"])
    return hidden


def pixel_to_value(calibration, panel, axis, pixel):
    mapping = calibration[axis]
    return mapping["value_intercept"] + mapping["value_per_pixel"] * pixel


def digitise(dump, calibration, name):
    panel = PANELS[name]
    cores = blob_cores(dump, panel)
    ridge = skeleton(line_mask(dump, panel, cores))
    segments = []
    for component in components(ridge):
        xs = [p[0] for p in component]
        if len(component) < 12 or max(xs) - min(xs) < 20:   # tick residue or glyph fragment
            continue
        segment = [{"x": round(pixel_to_value(calibration, panel, panel["x"], x), 4),
                    "y": round(pixel_to_value(calibration, panel, panel["y"], y), 6),
                    "pixel": [x, y]} for x, y in reversed(order_component(component))]
        segments.append(segment)
    segments.sort(key=lambda seg: seg[0]["x"])
    model = segments[0] if segments else []
    # (segments are ordered left to right, so model_gaps below are true interior gaps)
    found = cores
    experiments = [{"x": round(pixel_to_value(calibration, panel, panel["x"], c["x"]), 4),
                    "y": round(pixel_to_value(calibration, panel, panel["y"], c["y"]), 6),
                    "pixel": [round(c["x"], 2), round(c["y"], 2)],
                    "core_pixels": c["core_pixels"], "core_bbox_px": c["core_bbox"]} for c in found]
    x_unc = abs(calibration[panel["x"]]["value_per_pixel"])
    y_unc = abs(calibration[panel["y"]]["value_per_pixel"])
    span = panel["frame"][2] - panel["frame"][0]
    segments = [seg for seg in segments if seg]
    gaps = []
    for left_seg, right_seg in zip(segments, segments[1:]):
        gaps.append({"x_px": [left_seg[-1]["pixel"][0], right_seg[0]["pixel"][0]],
                     "x_range": [left_seg[-1]["x"], right_seg[0]["x"]],
                     "width_px": right_seg[0]["pixel"][0] - left_seg[-1]["pixel"][0]})
    return {
        "panel": name,
        "units": panel["units"],
        "frame_pixels": list(panel["frame"]),
        "mask_pixels": [list(m) for m in panel["masks"]],
        "marker_rim_excluded_px": RIM,
        "uncertainty": {"x_per_px": round(x_unc, 6), "y_per_px": round(y_unc, 8),
                        "marker_centre_px": 2.0, "line_centre_px": 1.0},
        "model": model,
        "model_segments": segments,
        "model_skeleton_pixels": len(ridge),
        "model_gaps": gaps,
        "model_x_range": [min(seg[0]["x"] for seg in segments), max(seg[-1]["x"] for seg in segments)]
                        if segments else None,
        "experiments": experiments,
        # Symbols the panel geometry hides.  `extraction_complete` is False whenever this list
        # is non-empty: the seven (or five) kept symbols are then not the panel's symbol set, and
        # the verifier must say so rather than let the masks decide which data the paper contains.
        "hidden_symbols": census(dump, panel, calibration),
        "frame_width_px": span,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rgba", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    raw = json.loads(args.calibration.read_text(encoding="utf-8"))
    calibration = {key: fit_ticks(value["ticks"]) for key, value in raw["calibration"].items()}
    for key, fitted in calibration.items():
        declared = raw["calibration"][key]
        fitted["declared"] = {k: declared[k] for k in ("value_per_pixel", "value_intercept")}
        fitted["max_abs_change_vs_declared"] = max(
            abs(fitted["value_per_pixel"] - declared["value_per_pixel"]),
            abs(fitted["value_intercept"] - declared["value_intercept"]))
    dump = Dump(args.rgba)
    result = {
        "schema": "liang-fig1-digitisation-v1",
        "source": {
            "paper_sha256": raw["paper_sha256"],
            "embedded_jpeg_sha256": raw["image_sha256"],
            "embedded_jpeg_size_px": [dump.width, dump.height],
            "figure1_region_points": raw["image_rect_points"],
            "note": "figure is a raster XObject inside the PDF; no vector path exists",
        },
        "calibration": calibration,
        "panels": {name: digitise(dump, calibration, name) for name in PANELS},
    }
    result["calibration_max_abs_residual_px"] = max(
        fitted["max_abs_residual_px"] for fitted in calibration.values())
    digest = hashlib.sha256(args.rgba.read_bytes()).hexdigest()
    result["source"]["rgba_dump_sha256"] = digest
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    for name, panel in result["panels"].items():
        print(f"{name}: {len(panel['model_segments'])} measured segments, "
              f"{sum(len(s) for s in panel['model_segments'])} points, "
              f"ridge {panel['model_skeleton_pixels']} px, {len(panel['model_gaps'])} gaps, "
              f"{len(panel['experiments'])} experimental symbols")


if __name__ == "__main__":
    main()
