#!/usr/bin/env python3
"""Production sweep of the pure-O2 PR / PR-VTA model at p = 5.61 MPa.

Writes, into the output directory:
  oxygen-properties.csv   raw samples (one row per temperature)
  deviations.json         comparison with the published Fig. 1 curves and the
                          published NIST markers, plus internal consistency checks
  environment.txt         exact interpreter, versions, inputs and sha256 digests

The published reference series are READ-ONLY inputs extracted from the paper
(/references/central-payload/assets). No reference point is interpolated: the
comparison is evaluated curve-to-curve on our own samples, and the NIST markers
are compared only at their own published temperatures.

Usage: run_properties.py --out DIR [--reference-dir DIR] [--p 5.61e6]
"""

import argparse
import hashlib
import json
import math
import os
import platform
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxygen_properties as op  # noqa: E402

CSV_HEADER = ("T_K,p_Pa,rho_PR_kg_m3,rho_VTA_kg_m3,cp_PR_J_kgK,Z_PR,Z_VTA,"
              "d_m,c_m_m3_mol,dc_m_m3_mol,cp_ideal_J_kgK,h_res_PR_J_mol,"
              "cp_PR_fd_J_kgK,cp_fd_rel_diff,n_PR_roots")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def temperature_grid():
    """Fine grid in the pseudo-critical region, coarse elsewhere, plus the exact
    published marker temperatures (never interpolated onto our grid)."""
    T = set()
    T.add(85.0)
    T.add(300.0)
    t = 85.0
    while t < 150.0 - 1e-12:
        T.add(round(t, 6)); t += 0.25
    t = 150.0
    while t <= 165.0 + 1e-12:
        T.add(round(t, 6)); t += 0.05
    t = 165.25
    while t < 300.0 - 1e-12:
        T.add(round(t, 6)); t += 0.25
    for Tk in (85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145,
               150, 153, 155, 155.5, 156, 156.5, 157, 158, 158.5, 159, 159.5,
               160, 162.5, 164.5, 169.5, 174.5, 179.5, 184.5, 189.5, 194.5,
               199.5, 204.5, 209.5, 214.5, 219.5, 224.5, 229.5, 234.5, 239.5,
               244.5, 249.5, 254.5, 259.5, 264.5, 269.5, 274.5, 279.5, 284.5,
               289.5, 294.5, 299.5):
        T.add(float(Tk))
    return sorted(T)


def sample(p):
    rows = []
    for T in temperature_grid():
        s = op.state(T, p)
        cp_fd = op.cp_pr_fd(T, p) / op.M_O2
        rows.append(dict(
            T_K=T, p_Pa=p, rho_PR_kg_m3=s["rho_PR"], rho_VTA_kg_m3=s["rho_VTA"],
            cp_PR_J_kgK=s["cp_PR_J_kgK"], Z_PR=s["Z_PR"], Z_VTA=s["Z_VTA"],
            d_m=s["d_m"], c_m_m3_mol=s["c_m"], dc_m_m3_mol=s["dc_m"],
            cp_ideal_J_kgK=s["cp_ideal_J_kgK"], h_res_PR_J_mol=s["h_residual_J_mol"],
            cp_PR_fd_J_kgK=cp_fd,
            cp_fd_rel_diff=(cp_fd - s["cp_PR_J_kgK"]) / s["cp_PR_J_kgK"],
            n_PR_roots=s["n_roots"]))
    return rows


def interp_points(points, x):
    """Linear interpolation of a retained reference series onto x (for curve
    comparison only; never used to create reference markers)."""
    xs = [q["x"] for q in points]
    ys = [q["y"] for q in points]
    if x <= xs[0] or x >= xs[-1]:
        return None
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return None


def compare(rows, refdir, PRESSURE):
    out = {"reference_dir": refdir, "series": {}}
    files = {
        "density": "muller2015-fig1a-density-props-r2-series.json",
        "cp": "muller2015-fig1b-cp-props-r2-series.json",
    }
    for key, name in files.items():
        path = os.path.join(refdir, name)
        if not os.path.exists(path):
            out["series"][key] = {"status": "reference_series_missing", "path": path}
            continue
        ref = json.load(open(path))
        ser = {s["id"]: s for s in ref["series"]}
        field = "rho" if key == "density" else "cp"
        ours = {("rho_PR" if field == "rho" else "cp_PR"): []}
        if field == "rho":
            ours["rho_VTA"] = []
        for r in rows:
            for k in ours:
                v = r["rho_PR_kg_m3"] if k == "rho_PR" else (
                    r["rho_VTA_kg_m3"] if k == "rho_VTA" else r["cp_PR_J_kgK"])
                ours[k].append((r["T_K"], v))
        entry = {"units": ref.get("units"), "reference_sha256": sha256_file(path),
                 "curve_comparison": {}, "marker_comparison": {}}
        # curve-to-curve: our fine samples vs the published vector curve
        pairs = [("paper-vta", "rho_VTA"), ("paper-pr", "rho_PR")] if field == "rho" \
            else [("paper-pr", "cp_PR")]
        for sid, okey in pairs:
            if sid not in ser:
                continue
            diffs = []
            for T, v in ours[okey]:
                if T < 85.0 or T > 299.5:
                    continue
                rv = interp_points(ser[sid]["points"], T)
                if rv is None:
                    continue
                diffs.append((T, v - rv, 100.0 * (v - rv) / rv))
            if not diffs:
                continue
            worst = max(diffs, key=lambda d: abs(d[2]))

            def band(lo, hi):
                sel = [d for d in diffs if lo <= d[0] < hi] or diffs
                w = max(sel, key=lambda d: abs(d[2]))
                return {"n_points": len(sel),
                        "max_abs_rel_deviation_percent": abs(w[2]),
                        "at_T_K": w[0],
                        "rms_rel_deviation_percent":
                            math.sqrt(sum(d[2] ** 2 for d in sel) / len(sel))}

            entry["curve_comparison"][sid] = {
                "series_compared": okey,
                "reference_provenance": ser[sid].get("provenance"),
                "n_points": len(diffs),
                "max_abs_rel_deviation_percent": abs(worst[2]),
                "at_T_K": worst[0],
                "signed_deviation_at_that_T": worst[1],
                "rms_rel_deviation_percent": math.sqrt(sum(d[2] ** 2 for d in diffs) / len(diffs)),
                # The pseudo-critical region (150-165 K) has d(rho)/dT of order
                # -100 kg/m3/K, so a 0.05 K abscissa difference already produces
                # ~1 % apparent deviation; the bands keep that separate.
                "band_T_85_150": band(85.0, 150.0),
                "band_T_150_165_pseudocritical": band(150.0, 165.0),
                "band_T_165_300": band(165.0, 299.6),
            }
        # Marker comparison: EVERY published marker is compared at its own
        # abscissa. The model is evaluated at the marker temperature; that is not
        # interpolation of reference data, because the reference ordinates stay
        # exactly as extracted and no marker is moved, dropped or synthesised.
        mk = ser.get("paper-nist")
        if mk:
            cmp_rows = []
            for q in mk["points"]:
                T = q["x"]
                st = op.state(T, PRESSURE)
                if field == "rho":
                    vals = {"rho_PR": st["rho_PR"], "rho_VTA": st["rho_VTA"]}
                else:
                    vals = {"cp_PR": st["cp_PR_J_kgK"]}
                item = {"T_K": T, "reference": q["y"]}
                for k, v in vals.items():
                    item[k] = v
                    item[k + "_rel_dev_percent"] = 100.0 * (v - q["y"]) / q["y"]
                cmp_rows.append(item)
            summary = {}
            for k in (["rho_PR", "rho_VTA"] if field == "rho" else ["cp_PR"]):
                devs = [c[k + "_rel_dev_percent"] for c in cmp_rows]
                summary[k] = {
                    "n_markers": len(devs),
                    "max_abs_rel_deviation_percent": max(abs(d) for d in devs),
                    "at_T_K": cmp_rows[max(range(len(devs)), key=lambda i: abs(devs[i]))]["T_K"],
                    "rms_rel_deviation_percent": math.sqrt(sum(d * d for d in devs) / len(devs)),
                    "rel_deviation_percent_at_85K":
                        next(c[k + "_rel_dev_percent"] for c in cmp_rows if abs(c["T_K"] - 85.0) < 1e-9),
                }
            entry["marker_comparison"] = {
                "reference_provenance": mk.get("provenance"),
                "n_markers_total": len(mk["points"]),
                "n_markers_compared": len(cmp_rows),
                "model_value_source": "state(T_marker, p) evaluated at each published marker abscissa",
                "summary": summary,
                "per_marker": cmp_rows,
            }
        out["series"][key] = entry
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--reference-dir",
                    default="/references/central-payload/assets")
    ap.add_argument("--p", type=float, default=op.P_FIG1)
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    rows = sample(args.p)
    csv_path = os.path.join(args.out, "oxygen-properties.csv")
    with open(csv_path, "w") as f:
        f.write(CSV_HEADER + "\n")
        for r in rows:
            f.write(",".join(
                ("%.10g" % r[k]) if isinstance(r[k], float) else str(r[k])
                for k in CSV_HEADER.split(",")) + "\n")

    dev = compare(rows, args.reference_dir, args.p)
    dev["schema"] = "oxygen-properties-deviations-v1"
    dev["pressure_Pa"] = args.p
    dev["n_samples"] = len(rows)
    dev["model"] = {
        "Tc_K": op.TC, "pc_Pa": op.PC, "omega": op.OMEGA, "Zc_PR": op.ZC_PR,
        "Zc_exp": op.ZC_EXP, "kappa": op.KAPPA, "b_PR_m3_mol": op.B_PR,
        "c1_exp": 0.4266 * op.ZC_EXP - 0.1101,
        "dc_m3_mol": (op.R * op.TC / op.PC) * (op.ZC_EXP - op.ZC_PR),
        "M_kg_mol": op.M_O2, "R_J_molK": op.R,
        "ideal_cp_source": "NIST Shomate O2 100-700 K (JANAF/NIST WebBook)",
    }
    dev_path = os.path.join(args.out, "deviations.json")
    with open(dev_path, "w") as f:
        json.dump(dev, f, indent=2, sort_keys=True)
        f.write("\n")

    env_path = os.path.join(args.out, "environment.txt")
    with open(env_path, "w") as f:
        f.write("python: %s\n" % sys.version.replace("\n", " "))
        f.write("platform: %s %s\n" % (platform.platform(), platform.machine()))
        f.write("module: %s\n" % os.path.abspath(op.__file__))
        f.write("module_sha256: %s\n" % sha256_file(op.__file__))
        f.write("script_sha256: %s\n" % sha256_file(os.path.abspath(__file__)))
        f.write("pressure_Pa: %r\n" % args.p)
        f.write("OMP_NUM_THREADS: %s\n" % os.environ.get("OMP_NUM_THREADS"))
        f.write("OPENBLAS_NUM_THREADS: %s\n" % os.environ.get("OPENBLAS_NUM_THREADS"))
        f.write("csv_sha256: %s\n" % sha256_file(csv_path))
        f.write("deviations_sha256: %s\n" % sha256_file(dev_path))

    print("wrote %s (%d samples)" % (csv_path, len(rows)))
    for key, e in dev["series"].items():
        if "curve_comparison" in e:
            for sid, c in e["curve_comparison"].items():
                print("  %-9s vs %-9s max|dev|=%.4f%% at T=%.2f K rms=%.4f%%"
                      " | 85-150K %.4f%% | 150-165K %.4f%% | 165-300K %.4f%%"
                      % (key, sid, c["max_abs_rel_deviation_percent"], c["at_T_K"],
                         c["rms_rel_deviation_percent"],
                         c["band_T_85_150"]["max_abs_rel_deviation_percent"],
                         c["band_T_150_165_pseudocritical"]["max_abs_rel_deviation_percent"],
                         c["band_T_165_300"]["max_abs_rel_deviation_percent"]))
        if e.get("marker_comparison"):
            for k, s in e["marker_comparison"]["summary"].items():
                print("  %-9s vs NIST %-8s max|dev|=%.3f%% at T=%.2f K, at 85 K %.4f%%"
                      % (key, k, s["max_abs_rel_deviation_percent"], s["at_T_K"],
                         s["rel_deviation_percent_at_85K"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
