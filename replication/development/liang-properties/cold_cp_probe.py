"""Frozen-volume O2 Cp-only conductivity diagnostic; plan never writes.

Uses the NIST WebBook 100–700 K Shomate gas-Cp fit and the unchanged
author-property run. No EOS, density mapping, reference correlation or solver
coefficient is adjusted. Run with the project analysis virtual environment.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import conductivity_math as cm
import critical_math

MODULE = Path(__file__).resolve().parent
SOURCE = {
    "url": "https://webbook.nist.gov/cgi/cbook.cgi?ID=C7782447&Mask=1",
    "reference": "Chase 1998 NIST-JANAF, Monograph 9",
    "fit_comment": "Data last reviewed March 1977; new parameter fit January 2009",
    "temperature_range_K": [100, 700],
    "formula": "Cp[J/mol/K]=A+B*t+C*t^2+D*t^3+E/t^2, t=T/1000",
    "coefficients": dict(A=31.32234, B=-20.23531, C=57.86644, D=-36.50624, E=-0.007374),
    "retrieved": "2026-10-21; official WebBook page via web tool",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, data):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--species", type=Path, required=True)
    parser.add_argument("--readings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if target.exists():
        raise ValueError("Choose a new evidence directory")
    params = critical_math.read_species(args.species)["O2"]
    if digest(args.species) != "a4d9a128cb77c69de64102f6a437000937f75182f7468cc0549880da40332e12":
        raise ValueError("Use the original property-run species dictionary")
    block = args.species.read_text().split("\nO2\n", 1)[1].split("\n}\n", 1)[0]
    nasa = np.array([float(x) for x in re.search(r"lowCpCoeffs\s+\(([^)]+)\)", block)[1].split()])
    par = np.array([[params["Tc"], params["Pc"], params["Vc"]*1e-3,
                     params["molWeight"], params["omega"], 1.]])
    w = params["molWeight"]
    reference = cm.REFERENCES["current"]
    result = []
    for original in rows(args.native):
        t = float(original["T_K"])
        if not 100 <= t <= 200:
            continue
        cp_r = float(original["cp0_R"])
        assert abs(np.polynomial.polynomial.polyval(t, nasa[:5])-cp_r) < 1e-13
        v = w/float(original["rho_kg_m3"])
        f, h = cm.shape(t/par[:, 0], v/par[:, 2], par, reference, .5)
        mu = float(cm.reference_viscosity(t/f[0])*np.sqrt(f[0]*w/reference["W"])*h[0]**(-2/3))
        u = t/1000
        c = SOURCE["coefficients"]
        cp_new = c["A"]+c["B"]*u+c["C"]*u*u+c["D"]*u**3+c["E"]/u**2
        cp_old = cp_r*cm.R/1000
        sensitivity = 1.32*mu/w*1000
        delta = sensitivity*(cp_new-cp_old)
        old_internal = 1.32*mu/w*cm.R*(cp_r-2.5)
        assert min(cp_r, cp_new/(cm.R/1000)) > 2.5
        direct = cm.conductivity(t, v, np.array([1.]), par, np.array([cp_r]))
        revised = cm.conductivity(t, v, np.array([1.]), par, np.array([cp_new/(cm.R/1000)]))
        old = float(original["kappa_W_m_K"])
        shortcut = float(original["kappa_mass_mapping_W_m_K"])
        assert abs(direct["lambda_W_mK"]/old-1) < 1e-10
        assert abs((revised["lambda_W_mK"]-direct["lambda_W_mK"])-delta) < 2e-16
        result.append(dict(
            T_K=t, cp_NASA_J_molK=cp_old, cp_Shomate_J_molK=cp_new,
            cp_change_pct=100*(cp_new/cp_old-1), mapped_viscosity_Pa_s=mu,
            internal_NASA_W_mK=old_internal, internal_Shomate_W_mK=old_internal+delta,
            delta_lambda_W_mK=delta, lambda_native_W_mK=old,
            lambda_Shomate_W_mK=old+delta, lambda_change_pct=100*delta/old,
            lambda_shortcut_W_mK=shortcut, lambda_shortcut_Shomate_W_mK=shortcut+delta,
            shortcut_change_pct=100*delta/shortcut,
            direct_native_relative_error=direct["lambda_W_mK"]/old-1))
    if [r["T_K"] for r in result] != list(range(100, 201)):
        raise ValueError("Expected the complete native 1 K grid from 100 to 200 K")
    grid = np.array([r["T_K"] for r in result])
    markers = []
    for point in rows(args.readings):
        if point["kind"] != "triangle_center" or point["panel"] != "conductivity":
            continue
        t = float(point["temperature_K"])
        if not 100 <= t <= 200:
            continue
        delta = float(np.interp(t, grid, [r["delta_lambda_W_mK"] for r in result]))
        old = float(np.interp(t, grid, [r["lambda_native_W_mK"] for r in result]))
        markers.append(dict(id=point["id"], T_K=t, paper_W_mK=float(point["value"]),
                            paper_low=float(point["value_low"]), paper_high=float(point["value_high"]),
                            old_W_mK=old, revised_W_mK=old+delta, delta_W_mK=delta))
    assert len(markers) == 4
    summary = dict(
        inputs={str(p.resolve()): digest(p) for p in
                [args.native, args.species, args.readings, MODULE/"conductivity_math.py",
                 MODULE/"critical_math.py", MODULE/"ElyHanley.H"]},
        script_sha256=digest(Path(__file__)), source=SOURCE, states=len(result),
        max_abs_cp_change_pct=max(abs(r["cp_change_pct"]) for r in result),
        max_abs_delta_lambda_W_mK=max(abs(r["delta_lambda_W_mK"]) for r in result),
        max_abs_lambda_change_pct=max(abs(r["lambda_change_pct"]) for r in result),
        max_abs_shortcut_change_pct=max(abs(r["shortcut_change_pct"]) for r in result),
        max_native_replay_relative_error=max(abs(r["direct_native_relative_error"]) for r in result),
        sample=[r for r in result if r["T_K"] in [100, 125, 150, 175, 200]], markers=markers)
    print(json.dumps(summary, indent=2))
    if args.action == "apply":
        target.mkdir()
        write_csv(target/"oxygen-cp-conductivity.csv", result)
        if markers:
            write_csv(target/"cold-marker-diagnostic.csv", markers)
        (target/"summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
