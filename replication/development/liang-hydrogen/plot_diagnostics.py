"""Discrete control overlays in calibrated paper coordinates; no model fitting."""
import json
import math
import re


def load(path):
    if path is None:
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))["diagnostics"]
    seen, styles = set(), {}
    for row in rows:
        expected = {3: "speed_cm_s", 5: "Tb_K"}
        if row["figure"] not in expected or row["quantity"] != expected[row["figure"]]:
            raise ValueError("Diagnostics support only declared Figure 3/5 quantities")
        key = (row["figure"], row["case"], row["phi"], row["label"])
        if key in seen or row["numerical_screen_passed"] is not True:
            raise ValueError("Duplicate or numerically unscreened diagnostic point")
        if row["case"] not in ("1", "2", "3", "3star", "4", "5"):
            raise ValueError("Unknown diagnostic case")
        if not all(math.isfinite(row[name]) for name in ("phi", "value")):
            raise ValueError("Nonfinite diagnostic point")
        if row["marker"] not in ("square", "diamond", "triangle"):
            raise ValueError("Use a distinct diagnostic marker")
        if not (re.fullmatch(r"[0-9a-f]{40}", row["source"]) and
                re.fullmatch(r"[0-9a-f]{64}", row["profile_sha256"]) and int(row["job"]) > 0):
            raise ValueError("Missing diagnostic source/profile identity")
        if row["label"] in styles and styles[row["label"]] != row["marker"]:
            raise ValueError("One diagnostic label must use one marker")
        styles[row["label"]] = row["marker"]
        seen.add(key)
    return rows


def legends(rows, figure):
    return list(dict.fromkeys((r["label"], r["marker"])
                             for r in rows if r["figure"] == figure))


def marker(page, point, style, color):
    import pymupdf as fitz
    x, y = point
    radius = 1.65
    if style == "square":
        page.draw_rect(fitz.Rect(x-radius, y-radius, x+radius, y+radius),
                       color=color, fill=(1, 1, 1), width=.65)
    else:
        corners = ([(x, y-radius), (x+radius, y), (x, y+radius), (x-radius, y)]
                   if style == "diamond" else
                   [(x, y-radius), (x+radius, y+radius), (x-radius, y+radius)])
        page.draw_polyline(corners, closePath=True, color=color, fill=(1, 1, 1), width=.65)


def draw(page, rows, figure, colors, axis, crop):
    bounds = {3: (52.709, 55.026, 220.09, 207.764),
              5: (73.946, 54.434, 230.882, 197.642)}
    outside = 0
    for row in (r for r in rows if r["figure"] == figure):
        x = axis(f"{figure}_x", row["phi"])
        y = axis("3_speed_cm_s" if figure == 3 else "5_Tb_K", row["value"])
        left, top, right, bottom = bounds[figure]
        if not (left-.02 <= x <= right+.02 and top-.02 <= y <= bottom+.02):
            outside += 1
            continue
        marker(page, (270+x-crop.x0, 56+y-crop.y0), row["marker"], colors[row["case"]])
    return outside
