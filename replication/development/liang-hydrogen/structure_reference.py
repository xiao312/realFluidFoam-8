"""Calibrated Figure 7 vectors and profile metrics; no fitted spatial scaling."""
import hashlib
import json
from pathlib import Path

import numpy as np

CALIBRATION = Path(__file__).with_name("figure7-calibration.json")
RANGES = {"T": (276, 305), "H2": (306, 352), "O2": (353, 388),
          "HO2": (389, 410), "H2O2": (411, 433)}


def crossing(x, y, level, last=False):
    """Interpolate an actual bracket, without endpoint extrapolation."""
    candidates = np.flatnonzero((y[:-1]-level)*(y[1:]-level) <= 0)
    if not len(candidates):
        raise ValueError(f"No crossing of {level}")
    index = candidates[-1] if last else candidates[0]
    if y[index+1] == y[index]:
        return float(x[index])
    return float(x[index] + (level-y[index]) *
                 (x[index+1]-x[index]) / (y[index+1]-y[index]))


def metrics(data):
    x, temperature = data["x_T_um"], data["T"]
    if np.any(np.diff(x) <= 0) or np.min(np.diff(temperature)) < -1e-3:
        raise ValueError("Expected an ordered, monotonic temperature front")
    anchor = crossing(x, temperature, 1500)
    result = dict(T_left_K=float(temperature[0]), T_right_K=float(temperature[-1]),
                  x1500_absolute_um=anchor,
                  width_T500_T2000_um=crossing(x, temperature, 2000)-
                                      crossing(x, temperature, 500))
    for target in (500, 1000, 2000, 2300):
        result[f"x_T{target}_relative_um"] = crossing(x, temperature, target)-anchor
    for species in ("HO2", "H2O2"):
        sx, values = data[f"x_{species}_um"], data[species]
        peak = int(np.argmax(values))
        if peak == 0 or peak+1 == len(values):
            raise ValueError("Minor-species peak lies on a boundary")
        half = values[peak]/2
        left = crossing(sx[:peak+1], values[:peak+1], half, last=True)
        right = crossing(sx[peak:], values[peak:], half)
        result[f"{species}_peak_X"] = float(values[peak])
        result[f"{species}_peak_relative_um"] = float(sx[peak]-anchor)
        result[f"{species}_peak_T_K"] = float(np.interp(sx[peak], x, temperature))
        result[f"{species}_FWHM_um"] = right-left
    return result


def extract(path):
    import pymupdf
    calibration = json.loads(CALIBRATION.read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != calibration["paper_sha256"]:
        raise ValueError("Expected the calibrated Liang PDF")
    with pymupdf.open(path) as document:
        drawings = document[calibration["page_index"]].get_drawings()
    maps = calibration["affine_maps"]
    ax, bx = maps["x_cm"]
    at, bt = maps["T_K"]
    al, bl = maps["log10_X"]
    for group, coordinate in (("x_ticks", "center_x_pt"),
                               ("T_ticks", "center_y_pt"),
                               ("X_ticks", "center_y_pt")):
        for tick in calibration[group]:
            rect = drawings[tick["drawing_index"]]["rect"]
            observed = rect.x0 if coordinate == "center_x_pt" else rect.y0
            if abs(observed-tick[coordinate]) > 1e-6:
                raise ValueError("Source tick no longer matches its calibration")
    paper, raw = {}, []
    for series, (first, last) in RANGES.items():
        grouped = {}
        for index in range(first, last+1):
            drawing = drawings[index]
            if abs(drawing["width"]-calibration["stroke_width_pt"]) > .001:
                raise ValueError("Unexpected source curve stroke")
            for item in drawing["items"]:
                if item[0] != "l":
                    raise ValueError("Unexpected source vector primitive")
                for point in item[1:]:
                    grouped.setdefault(round(point.x, 3), []).append(point.y)
                    raw.append(dict(series=series, path=index, x_pt=point.x, y_pt=point.y))
        points = np.array([(x, np.median(y)) for x, y in sorted(grouped.items())])
        paper[f"x_{series}_um"] = (points[:, 0]-bx)/ax*1e4
        paper[series] = ((points[:, 1]-bt)/at if series == "T"
                         else 10**((points[:, 1]-bl)/al))
    result = metrics(paper)
    dx, dt, dl = (calibration[key] for key in
                  ("x_allowance_um", "T_allowance_K", "log10_X_allowance"))
    def temperature_bounds(level):
        x, y = paper["x_T_um"], paper["T"]
        return crossing(x, y, level-dt)-dx, crossing(x, y, level+dt)+dx
    anchor_bounds = temperature_bounds(1500)
    left, right = temperature_bounds(500), temperature_bounds(2000)
    bounds = {"width_T500_T2000_um": [right[0]-left[1], right[1]-left[0]]}
    for species in ("HO2", "H2O2"):
        x, y = paper[f"x_{species}_um"], paper[species]
        peak = int(np.argmax(y))
        bounds[f"{species}_peak_X"] = [float(y[peak]/10**dl), float(y[peak]*10**dl)]
        peak_region = x[y >= y[peak]/10**dl]
        bounds[f"{species}_peak_relative_um"] = [
            float(min(peak_region)-dx-anchor_bounds[1]),
            float(max(peak_region)+dx-anchor_bounds[0])]
        widths = []
        for multiplier in (10**(-2*dl), 10**(2*dl)):
            level = y[peak]/2*multiplier
            widths.append(crossing(x[peak:], y[peak:], level) -
                          crossing(x[:peak+1], y[:peak+1], level, last=True))
        bounds[f"{species}_FWHM_um"] = [min(widths)-2*dx, max(widths)+2*dx]
    result["T_at_paper_right_K"] = result["T_right_K"]
    return paper, result, bounds, raw, calibration
