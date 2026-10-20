"""Bound saved-coordinate roundoff; never waive a failed strict native-flux check."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from analyze_soret import shared_audit


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal_half_step(values, digits=16):
    """Half a declared decimal output unit, plus binary parsing."""
    values = np.asarray(values)
    result = np.zeros_like(values)
    nonzero = values != 0
    result[nonzero] = .5*10.**(np.floor(np.log10(np.abs(values[nonzero])))-(digits-1))
    return result+np.finfo(float).eps*np.abs(values)


def inspect(row, native):
    result = Path(row["result"])
    if not (result/"completed.txt").is_file():
        raise ValueError("Incomplete run")
    config_path = result/"configuration.txt"
    config = (dict(line.split(maxsplit=1) for line in config_path.read_text().splitlines()
                   if line.strip()) if config_path.exists() else {})
    digits = int(config.get("output_significant_digits", 16))
    if digits not in (16, 17):
        raise ValueError("Unsupported native export precision")
    profile, species = native.read_profile(result/"profile.csv")
    path = result/"soret-flux.csv"
    # Shared reader verifies row order, finite numbers, coordinates and all lengths.
    strict_errors, _, _ = native.inspect_native_fluxes(path, profile, species)
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    count = len(species)
    coefficient = np.array([float(r["DT_kg_m_s"]) for r in rows]).reshape(-1, count)
    thermal = np.array([float(r["soret_kg_m2_s"]) for r in rows]).reshape(-1, count)
    x, temperature = profile["x_m"], profile["T_K"]
    dx, delta = np.diff(x), np.diff(temperature)
    total = temperature[1:]+temperature[:-1]
    x_error, t_error = decimal_half_step(x, digits), decimal_half_step(temperature, digits)
    dx_error = x_error[1:]+x_error[:-1]
    delta_error = t_error[1:]+t_error[:-1]
    if np.any(dx <= dx_error) or np.any(total <= delta_error):
        raise ValueError("Saved grid/temperature cannot bound the gradient")
    # Exact extrema of the interval quotient; denominator is strictly positive.
    denominator_low = (total-delta_error)*(dx-dx_error)
    denominator_high = (total+delta_error)*(dx+dx_error)
    corners = np.stack([2*(delta+sign*delta_error)/denominator
                        for sign in (-1, 1)
                        for denominator in (denominator_low, denominator_high)])
    lower, upper = corners.min(axis=0), corners.max(axis=0)
    gradient = 2*delta/(total*dx)
    gradient_error = np.maximum(abs(lower-gradient), abs(upper-gradient))
    error_bound = (
        abs(coefficient)*gradient_error[:, None]
        +decimal_half_step(coefficient, digits)*(abs(gradient)+gradient_error)[:, None]
        +decimal_half_step(thermal, digits)
        # A small binary-operation allowance covers the native multiply/divide.
        +16*np.finfo(float).eps*(abs(thermal)+abs(coefficient*gradient[:, None]))
        +16*np.nextafter(0., 1.))
    residual = abs(thermal+coefficient*gradient[:, None])
    y_names = [name for name in profile.dtype.names if name.startswith("Y_")]
    fractions = np.array([profile[name] for name in y_names]).T
    face_y_sum = .5*(fractions[:-1].sum(axis=1)+fractions[1:].sum(axis=1))
    coefficient_sum = coefficient.sum(axis=1)
    peak = int(np.argmax(abs(coefficient_sum)))
    return dict(
        job=row["job"], case=row["case"], phi=row["phi"], variant=row["variant"],
        decimal_significant_digits=digits,
        strict_native_residuals=strict_errors,
        maximum_thermal_reconstruction_error_kg_m2_s=float(residual.max()),
        maximum_decimal_bound_kg_m2_s=float(error_bound.max()),
        maximum_error_to_local_bound=float(np.max(residual/np.maximum(error_bound, 1e-300))),
        entries_outside_decimal_bound=int(np.count_nonzero(residual > error_bound)),
        maximum_face_species_sum_error=float(np.max(abs(face_y_sum-1))),
        coefficient_peak_face=peak,
        coefficient_sum_at_peak_kg_m_s=float(coefficient_sum[peak]),
        species_sum_error_at_coefficient_peak=float(face_y_sum[peak]-1),
        profile_sha256=digest(result/"profile.csv"), flux_sha256=digest(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output")
    rows = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    native, _ = shared_audit()
    records = [inspect(row, native) for row in rows if row["variant"] != "baseline"]
    if not records:
        parser.error("No completed Soret runs")
    report = dict(
        manifest_sha256=digest(args.manifest), script_sha256=digest(Path(__file__)),
        export_precisions=sorted({r["decimal_significant_digits"] for r in records}),
        runs=records, scientific_acceptance=False,
        limits=["Arithmetic output bound only; no strict audit tolerance is changed",
                "Cantera Flow1D supplies unnormalized face mass fractions",
                "The native projection subtracts Y_k times the unprojected coefficient sum",
                "Composition correlation alone does not independently reconstruct that sum"])
    print(json.dumps(records, indent=2))
    if args.action == "apply":
        args.output.write_text(json.dumps(report, indent=2)+"\n",
                               encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
