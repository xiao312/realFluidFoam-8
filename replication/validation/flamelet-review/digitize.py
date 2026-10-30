"""Visible-color extraction with explicit pixel calibration and retained gaps."""
import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from inputs import digest


def remove_speckles(mask, minimum_pixels):
    """Discard isolated antialiasing fragments; never infer a replacement pixel."""
    remaining = mask.copy(); kept = np.zeros_like(mask); rejected = 0
    height, width = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if not remaining[y, x]:
            continue
        stack = [(y, x)]; remaining[y, x] = False; component = []
        while stack:
            row, column = stack.pop(); component.append((row, column))
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    r, c = row + dy, column + dx
                    if 0 <= r < height and 0 <= c < width and remaining[r, c]:
                        remaining[r, c] = False; stack.append((r, c))
        if len(component) >= minimum_pixels:
            for row, column in component:
                kept[row, column] = True
        else:
            rejected += len(component)
    return kept, rejected


def extract_panel(path, panel, config):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    if rgb.shape[:2] != (panel["height"], panel["width"]):
        raise ValueError(f"Reference crop dimensions changed: {path}")
    colors = np.asarray([c["rgb"] for c in config["curves"]])
    from matplotlib.colors import rgb_to_hsv
    hue = rgb_to_hsv(rgb / 255)[:, :, 0] * 360
    color_hues = rgb_to_hsv(colors / 255)[:, 0] * 360
    distance = np.sqrt(np.sum((rgb[:, :, None, :] - colors[None, None, :, :]) ** 2, axis=-1))
    nearest = np.argmin(distance, axis=-1)
    saturation = (rgb.max(axis=-1) - rgb.min(axis=-1)) / np.maximum(rgb.max(axis=-1), 1)
    left, top, right, bottom = panel["plot"]
    yy, xx = np.indices(rgb.shape[:2])
    eligible = (xx > left) & (xx < right) & (yy > top) & (yy < bottom)
    legend = config["legend_exclusion"]
    eligible &= ~((xx < legend["x_below"]) & (yy < legend["y_below"]))
    eligible &= (distance.min(axis=-1) <= config["color_distance_max"]) & (saturation >= config["saturation_min"])
    curves = []
    for color_index, description in enumerate(config["curves"]):
        rows = []; ambiguous = []
        hue_distance = abs((hue - color_hues[color_index] + 180) % 360 - 180)
        color_mask = eligible & (nearest == color_index) & (hue_distance <= config["hue_tolerance_degrees"])
        color_mask, rejected_pixels = remove_speckles(color_mask, config["minimum_component_pixels"])
        for x in range(left + 1, right):
            pixels = np.flatnonzero(color_mask[:, x])
            # Missing columns remain missing. No regression or gap interpolation.
            if len(pixels):
                if np.ptp(pixels) > config["maximum_column_span_pixels"]:
                    ambiguous.append({"pixel_x": x, "candidate_y": pixels.tolist()})
                    continue
                y = float(np.median(pixels))
                rows.append({"pixel_x": x, "pixel_y": y, "pixel_span_y": int(np.ptp(pixels)),
                             "pixel_count": len(pixels),
                             "c": panel["x_range"][0] + (x - left) / (right - left) * np.ptp(panel["x_range"]),
                             "value": panel["y_range"][1] - (y - top) / (bottom - top) * np.ptp(panel["y_range"])})
        if len(rows) < 20:
            raise ValueError(f"Insufficient colored pixels for {panel['id']}/{description['name']}")
        curves.append({**description, "points": rows, "rejected_speckle_pixels": rejected_pixels,
                       "ambiguous_columns": ambiguous})
    return {"panel": panel, "image_sha256": digest(path), "curves": curves,
            "method": "nearest RGB plus hue window; reject tiny components and ambiguous columns; median y per observed column; no gap bridging",
            "uncertainty": "pixel calibration and antialiasing; median center is not experimental uncertainty"}


def with_gaps(points):
    x, y = [], []
    for i, row in enumerate(points):
        if i and row["pixel_x"] > points[i - 1]["pixel_x"] + 1:
            x.append(float("nan")); y.append(float("nan"))
        x.append(row["c"]); y.append(row["value"])
    return x, y


def write_extraction(result, image_path, out):
    panel_id = result["panel"]["id"]
    (out / f"digitized-{panel_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    with (out / f"digitized-{panel_id}.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["z", "pixel_x", "pixel_y", "pixel_span_y", "pixel_count", "c", "value"])
        writer.writeheader()
        for curve in result["curves"]:
            writer.writerows({"z": curve["z"], **row} for row in curve["points"])
    fig, ax = plt.subplots(figsize=(result["panel"]["width"] / 100, result["panel"]["height"] / 100), dpi=160)
    ax.imshow(Image.open(image_path))
    for curve in result["curves"]:
        selected = curve["points"][::5]
        ax.scatter([p["pixel_x"] for p in selected], [p["pixel_y"] for p in selected],
                   s=8, marker="x", c="black", linewidths=.5)
    ax.axis("off"); fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(out / f"digitization-{panel_id}-overlay.png", dpi=160)
    plt.close(fig)
