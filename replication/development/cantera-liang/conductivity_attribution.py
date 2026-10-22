#!/usr/bin/env python3
"""Attribute the stage-4 flame-speed shift to the conductivity model, from retained output.

Stage 4 of the Liang 8(a) chain replaces the mixture-averaged `thermalConductivity()`
with the full `rfElyHanley::conductivity` call while adding the same residual h/s/cp
terms stage 3 already had. Stages 2 and 3 differ from stage 1 only by the equation of
state and the residual caloric terms. The solver prints `lambda_W_mK`, `rho`, `cp` and
`T` on every grid point of every saved profile, so the conductivity change can be
measured from the retained profiles instead of argued from the source.

The comparison is deliberately one-sided: it asks whether the measured conductivity
ratio can account for the measured speed ratio through S_L ~ sqrt(alpha), not whether
the reconstruction is right. Nothing here selects a model.
"""
import bisect
import csv
import json
import os
import sys

ROOT = os.environ.get("FP_CASES", "/workspace/forge-out/runs/liang8a-coarse-a/cases")
RESULTS = os.environ.get("FP_RESULTS", "/workspace/forge-out/runs/liang8a-out/results.json")
OUTPUT = os.environ.get("FP_OUTPUT", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "conductivity-attribution.json"))
PHI = os.environ.get("FP_PHI", "0.95")
STAGES = [1, 2, 3, 4]
OK = RESULTS


def load(stage):
    path = os.path.join(ROOT, "stage-%d-phi-%s" % (stage, PHI), "result", "profile.csv")
    if not os.path.exists(path):
        return None
    rows = []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            rows.append({k: float(v) for k, v in row.items()})
    return rows


def front(rows):
    """Grid point of maximum temperature gradient and the thermal thickness."""
    best, dbest = None, 0.0
    for a, b in zip(rows, rows[1:]):
        dx = b["x_m"] - a["x_m"]
        if dx <= 0:
            continue
        g = (b["T_K"] - a["T_K"]) / dx
        if g > dbest:
            dbest, best = g, a
    t_ad = max(r["T_K"] for r in rows)
    t_u = rows[0]["T_K"]
    return {"x": best["x_m"], "T": best["T_K"], "lam": best["lambda_W_mK"],
            "rho": best["rho_kg_m3"], "cp": best["cp_J_kgK"],
            "alpha": best["lambda_W_mK"] / (best["rho_kg_m3"] * best["cp_J_kgK"]),
            "dTdx": dbest, "delta_th": (t_ad - t_u) / dbest,
            "T_ad": t_ad, "T_u": t_u}


def speed(stage):
    if not os.path.exists(OK):
        return None
    data = json.load(open(OK))
    key = "stage-%d" % stage
    rows = data["results"] if isinstance(data, dict) else data
    for row in rows:
        if row.get("status") and not str(row["status"]).startswith("CASE"):
            continue
        try:
            p = float(row.get("phi"))
            sid = int(row.get("stage"))
        except (TypeError, ValueError):
            continue
        if sid == stage and abs(p - float(PHI)) < 1e-9 and row.get("speed_cm_s"):
            return float(row["speed_cm_s"])
    return None


def main():
    profiles = {}
    for s in STAGES:
        rows = load(s)
        if rows:
            profiles[s] = (rows, front(rows))
    if 1 not in profiles:
        print("no stage-1 profile; cannot normalise", file=sys.stderr)
        return 2
    base_rows, base = profiles[1]
    out = {"phi": float(PHI), "stages": {}, "notes": []}
    for s, (rows, f) in profiles.items():
        rec = {k: f[k] for k in ("x", "T", "lam", "rho", "cp", "alpha", "delta_th", "T_ad")}
        rec["lambda_ratio"] = f["lam"] / base["lam"]
        rec["alpha_ratio"] = f["alpha"] / base["alpha"]
        rec["delta_ratio"] = f["delta_th"] / base["delta_th"]
        rec["T_ad_shift_K"] = f["T_ad"] - base["T_ad"]
        v = speed(s)
        if v is not None:
            rec["speed_cm_s"] = v
        out["stages"][str(s)] = rec
    if "1" in out["stages"] and "speed_cm_s" in out["stages"]["1"]:
        v1 = out["stages"]["1"]["speed_cm_s"]
        for s in out["stages"]:
            if "speed_cm_s" in out["stages"][s]:
                r = out["stages"][s]["speed_cm_s"] / v1
                out["stages"][s]["speed_ratio"] = r
                out["stages"][s]["alpha_ratio_for_that_speed"] = r * r
    # pointwise conductivity difference along the whole profile, interpolated on stage 1
    def pointwise(other):
        """Relative conductivity change and alpha ratio of `other` evaluated at base x.

        Kept as a function so the same code can also be run against a profile compared
        with itself: that self-comparison is the control for this measurement. If the
        interpolation or the arithmetic could manufacture a shift, it would also show up
        there.
        """
        xs = [r["x_m"] for r in other]
        diffs, phys = [], []
        for r in base_rows:
            x = r["x_m"]
            if x < xs[0] or x > xs[-1]:
                continue
            i = bisect.bisect_left(xs, x)
            if i == 0:
                lam4, rho4, cp4 = other[0]["lambda_W_mK"], other[0]["rho_kg_m3"], other[0]["cp_J_kgK"]
            elif i >= len(xs):
                lam4, rho4, cp4 = other[-1]["lambda_W_mK"], other[-1]["rho_kg_m3"], other[-1]["cp_J_kgK"]
            else:
                a, b = other[i - 1], other[i]
                w = 0.0 if b["x_m"] == a["x_m"] else (x - a["x_m"]) / (b["x_m"] - a["x_m"])
                lam4 = a["lambda_W_mK"] + w * (b["lambda_W_mK"] - a["lambda_W_mK"])
                rho4 = a["rho_kg_m3"] + w * (b["rho_kg_m3"] - a["rho_kg_m3"])
                cp4 = a["cp_J_kgK"] + w * (b["cp_J_kgK"] - a["cp_J_kgK"])
            if r["lambda_W_mK"] <= 0:
                continue
            diffs.append((lam4 - r["lambda_W_mK"]) / r["lambda_W_mK"])
            a1 = r["lambda_W_mK"] / (r["rho_kg_m3"] * r["cp_J_kgK"])
            a4 = lam4 / (rho4 * cp4)
            if a1 > 0:
                phys.append(a4 / a1)
        if not diffs:
            return None
        n = len(diffs)
        diffs_sorted = sorted(diffs)
        phys_sorted = sorted(phys)
        return {
            "points": n,
            "mean_relative_conductivity_change": sum(diffs) / n,
            "median_relative_conductivity_change": diffs_sorted[n // 2],
            "max_relative_conductivity_change": diffs_sorted[-1],
            "min_relative_conductivity_change": diffs_sorted[0],
            "mean_alpha_ratio": sum(phys) / n,
            "median_alpha_ratio": phys_sorted[len(phys) // 2],
        }

    if 4 in profiles:
        four = profiles[4][0]
        got = pointwise(four)
        if got:
            out["pointwise"] = got
        # Control: the identical measurement applied to a profile and itself must return
        # exactly zero change and a unit alpha ratio at every shared point.
        control = pointwise(base_rows)
        if control:
            control["max_abs_relative_conductivity_change"] = max(
                abs(control["max_relative_conductivity_change"]),
                abs(control["min_relative_conductivity_change"]))
            control["passes"] = (control["max_abs_relative_conductivity_change"] == 0.0
                                 and control["median_alpha_ratio"] == 1.0)
            out["self_comparison_control"] = control
    out["inputs"] = {"cases": ROOT, "results": RESULTS, "phi": float(PHI)}
    json.dump(out, open(OUTPUT, "w"), indent=1)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
