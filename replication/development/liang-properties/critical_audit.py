"""Audit Liang Figure 2 against native data and an independent molar-SI SRK calculation."""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pymupdf as fitz

from critical_math import R, OMEGA_B, analytical, coefficients, composition
from critical_math import numerical_inflection, read_species

PAPER_SHA = "24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paper_curves(path):
    """Read vector lines, rejecting axes/ticks by position AND nonzero height.

    All 11 pressure ticks are checked against the independently read red scale.
    Do not extrapolate across the missing final methane dash.
    """
    if digest(path) != PAPER_SHA:
        raise ValueError("Uncalibrated paper PDF")
    curves = {(f, q): [] for f in ("H2", "CH4") for q in ("Tc", "Pc")}
    ticks = []
    with fitz.open(path) as document:
        for drawing in document[2].get_drawings():
            rect, color = drawing["rect"], drawing["color"]
            if drawing["fill"] is not None or color is None:
                continue
            red = color[0] > .5 and color[1] < .1
            if red and abs(rect.x0 - 430.475) < .02 and rect.height < .01:
                ticks.append(rect.y0)
            if rect.x0 < 282.7 or rect.x1 > 434.1 or rect.width < 3 or rect.height < .1:
                continue
            quantity = "Pc" if red else "Tc"
            hydrogen = ((quantity == "Tc" and 126 < rect.y0 and rect.y1 < 167)
                        or (quantity == "Pc" and 146 < rect.y0 and rect.y1 < 180))
            methane = ((quantity == "Tc" and 77 < rect.y0 and rect.y1 < 91)
                       or (quantity == "Pc" and 97 < rect.y0 and rect.y1 < 113))
            if not (hydrogen or methane):
                continue
            fuel = "H2" if hydrogen else "CH4"
            for item in drawing["items"]:
                if item[0] == "l":
                    curves[fuel, quantity].extend((point.x, point.y) for point in item[1:])
    measured = np.array(sorted(ticks, reverse=True))
    expected = np.linspace(188.808, 56.037, 11)
    if len(measured) != 11 or max(abs(measured - expected)) > .025:
        raise ValueError("Pressure-axis calibration changed")
    result = []
    for fuel in ("H2", "CH4"):
        for phi in np.linspace(.6, 1.9, 14):
            point = dict(fuel=fuel, phi=float(phi))
            pixel_x = 282.737 + (phi - .6) * (434.058 - 282.737) / 1.4
            for quantity in ("Tc", "Pc"):
                xy = np.array(sorted(set(curves[fuel, quantity])))
                if pixel_x < xy[0, 0] - .002 or pixel_x > xy[-1, 0] + .002:
                    raise ValueError("Requested point outside extracted curve")
                y = np.interp(pixel_x, xy[:, 0], xy[:, 1])
                value = (60 + (194.121 - y) * 100 / (194.121 - 56.036)
                         if quantity == "Tc" else 10 + (188.808 - y) * 50 / (188.808 - 56.037))
                point[quantity + ("_K" if quantity == "Tc" else "_atm")] = float(value)
            point["implied_b_cm3_mol"] = OMEGA_B * R * point["Tc_K"] / (point["Pc_atm"] * 101325) * 1e6
            result.append(point)
    return result


def sensitivity(species, fuel):
    x = composition(fuel, 1)
    weights = np.array([species[n]["molWeight"] for n in (fuel, "O2", "N2")])
    rounded = copy.deepcopy(species)
    for name, temperature, pressure in (("H2", 33, 12), ("CH4", 190, 46),
                                        ("N2", 126, 33), ("O2", 154, 50)):
        rounded[name].update(Tc=temperature, Pc=pressure * 101325)
    variants = [
        ("baseline", species, x, "fork", "critical-pressure"),
        ("rounded_paper_constants", rounded, x, "fork", "critical-pressure"),
        ("air_N2_O2_3.76", species, composition(fuel, 1, 3.76), "fork", "critical-pressure"),
        ("mass_fractions_used_as_mole", species, x*weights/sum(x*weights), "fork", "critical-pressure"),
        ("mole_fractions_converted_again", species, x/weights/sum(x/weights), "fork", "critical-pressure"),
        ("original_soave_alpha", species, x, "original-soave", "critical-pressure"),
        ("constant_attraction_alpha_1", species, x, "constant", "critical-pressure"),
        ("b_from_measured_Vc", species, x, "fork", "measured-volume"),
    ]
    return [dict(variant=name, fuel=fuel, **analytical(coefficients(data, fuel, fractions, alpha, volume)))
            for name, data, fractions, alpha, volume in variants]


def run(args):
    species = read_species(args.species)
    reference = paper_curves(args.paper)
    with args.native.open() as stream:
        native = list(csv.DictReader(stream))
    if args.output.exists():
        raise ValueError("Output exists; use a new audit directory")
    print(json.dumps(dict(action=args.action, output=str(args.output), native_states=len(native),
                          paper_points=len(reference))))
    if args.action == "plan":
        return
    errors = []
    for row in native:
        model = coefficients(species, row["fuel"], composition(row["fuel"], float(row["phi"])))
        result = analytical(model)
        errors.append(max(abs(result[key] - float(row[key])) for key in ("Tc_K", "Pc_atm")))
    if max(errors) > 1e-8:
        raise ValueError("Independent coefficients disagree with native probe")
    numeric_checks = []
    for fuel in ("H2", "CH4"):
        for phi in (.6, 1., 1.9):
            model = coefficients(species, fuel, composition(fuel, phi))
            exact = analytical(model)
            for step in (.02, .01, .005):
                numerical = numerical_inflection(model, step)
                error = max(abs(numerical[key] - exact[key]) for key in ("Tc_K", "Pc_atm"))
                if error > 2e-5:
                    raise ValueError("Finite-difference inflection disagrees with analytical solution")
                numeric_checks.append(dict(fuel=fuel, phi=phi, step=step, error=error, **numerical))
    comparison = []
    for row in reference:
        model = coefficients(species, row["fuel"], composition(row["fuel"], row["phi"]))
        result = analytical(model)
        comparison.append(dict(**row, computed_Tc_K=result["Tc_K"], computed_Pc_atm=result["Pc_atm"],
                               computed_b_cm3_mol=result["b_cm3_mol"],
                               minimum_species_b_cm3_mol=float(min(model["bi"]) * 1e6),
                               maximum_species_b_cm3_mol=float(max(model["bi"]) * 1e6)))
    # A fixed fuel/air blend must give b = Xfuel*bfuel + (1-Xfuel)*bair.
    # This inverse fit is a compatibility diagnostic, never replacement input data.
    inverse = {}
    for fuel in ("H2", "CH4"):
        rows = [r for r in reference if r["fuel"] == fuel]
        xf = np.array([composition(fuel, r["phi"])[0] for r in rows])
        matrix = np.column_stack((xf, 1 - xf))
        values = np.array([r["implied_b_cm3_mol"] for r in rows])
        inferred, *_ = np.linalg.lstsq(matrix, values, rcond=None)
        inverse[fuel] = dict(inferred_fuel_b=float(inferred[0]), inferred_air_b=float(inferred[1]),
                             max_residual_cm3_mol=float(max(abs(values - matrix @ inferred))))
    variants = [row for fuel in ("H2", "CH4") for row in sensitivity(species, fuel)]
    record = dict(input_sha256={name: digest(getattr(args, name)) for name in ("species", "native", "paper")},
                  code_sha256={name: digest(Path(__file__).with_name(name))
                               for name in ("critical_audit.py", "critical_math.py")},
                  species_inputs=species, max_native_difference=max(errors), numerical_checks=numeric_checks,
                  inverse_b_fit_diagnostic_only=inverse, comparison=comparison, sensitivity=variants,
                  paper_reading_tolerance=dict(Tc_K=.1, Pc_atm=.05), scientific_acceptance=False)
    args.output.mkdir(parents=True)
    (args.output / "audit.json").write_text(json.dumps(record, indent=2) + "\n")
    for name, rows in (("comparison.csv", comparison), ("sensitivity.csv", variants)):
        with (args.output / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(dict(max_native_difference=max(errors), inverse_b_fit=inverse), indent=2))
    if args.require_paper_match and any(abs(r["computed_Pc_atm"] - r["Pc_atm"]) > .1 for r in comparison):
        raise SystemExit("FAIL: Figure 2 pressure mismatch exceeds figure-reading tolerance; audit saved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "apply"))
    for name in ("species", "native", "paper", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--require-paper-match", action="store_true")
    run(parser.parse_args())
