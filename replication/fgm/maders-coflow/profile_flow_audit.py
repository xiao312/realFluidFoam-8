"""Read retained flow evidence; never alter a CFD field or declare acceptance."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile(path, columns):
    values = np.genfromtxt(path, delimiter=",", names=True)
    if values.ndim != 1 or len(values) < 3:
        raise ValueError(f"Expected a radial profile: {path}")
    for column in columns:
        if column not in values.dtype.names or not np.isfinite(values[column]).all():
            raise ValueError(f"Missing/nonfinite {column}: {path}")
    if not (np.diff(values["y"]) > 0).all() or values["y"][0] < 0:
        raise ValueError(f"Radial coordinates must increase from nonnegative r: {path}")
    return values


def evaluate(samples, collection_path, mass_log):
    collection = json.loads(collection_path.read_text())
    log_receipt = collection.get("massLog", {})
    if (log_receipt.get("sha256") != digest(mass_log)
            or log_receipt.get("job") != collection["job"]
            or not log_receipt.get("nativePath")):
        raise ValueError("Mass-log excerpt requires a matching hash and exact-job receipt")
    files = {str(collection_path): digest(collection_path), str(mass_log): digest(mass_log)}
    patch_flux = {}
    patch_times = []
    for name in ("fuel", "air", "outlet"):
        entries = [x for x in collection["files"] if x["file"] == name + ".dat"]
        if len(entries) != 1:
            raise ValueError(f"Expected one {name} flux receipt")
        entry = entries[0]
        path = collection_path.parent / entry["file"]
        if digest(path) != entry["sha256"]:
            raise ValueError(f"Patch flux hash mismatch: {name}")
        values = np.loadtxt(path, comments="#", ndmin=2)
        if values.shape[1] != 2 or not np.isfinite(values).all():
            raise ValueError(f"Invalid patch flux values: {name}")
        if not (np.diff(values[:, 0]) > 0).all():
            raise ValueError(f"Patch times must strictly increase: {name}")
        patch_times.append(float(values[-1, 0]))
        patch_flux[name] = float(values[-1, 1])
        files[str(path)] = digest(path)

    states = []
    for line in mass_log.read_text().splitlines():
        if line.startswith("energyState "):
            fields = dict(re.findall(r"(\w+)=([^ ]+)", line))
            states.append((float(fields["t"]), float(fields["mass"])))
    if len(states) < 2 or states[-1][0] <= states[-2][0]:
        raise ValueError("Need two distinct final completed energyState records")
    time = float(samples.name)
    if any(abs(t - time) > 1e-11 for t in patch_times + [states[-1][0]]):
        raise ValueError("Final profile, patch flux and mass-log times do not match")
    if not np.isfinite(np.asarray(states)).all():
        raise ValueError("Nonfinite mass history")
    dt = states[-1][0] - states[-2][0]
    mass_rate = (states[-1][1] - states[-2][1]) / dt
    outward_flux = sum(patch_flux.values())
    mass_balance = {
        "time_s": time, "previousTime_s": states[-2][0], "EulerDeltaTime_s": dt,
        "massRate_kg_s": mass_rate, "patchOutwardFlux_kg_s": patch_flux,
        "sumOutwardFlux_kg_s": outward_flux,
        "EulerMassResidual_kg_s": mass_rate + outward_flux,
        "residualRelativeToInflow": (mass_rate + outward_flux)
        / max(abs(patch_flux["fuel"] + patch_flux["air"]), 1e-300),
    }
    rows = []
    for height in (10, 40):
        paths = list(samples.glob(f"h{height}_T_*.csv"))
        if len(paths) != 1:
            raise ValueError(f"Expected one scalar profile at H={height}mm")
        scalar_path, velocity_path = paths[0], samples / f"h{height}_U.csv"
        scalar = profile(scalar_path, ("y", "rho", "Z"))
        velocity = profile(velocity_path, ("y", "U_0", "U_1", "U_2"))
        if not np.array_equal(scalar["y"], velocity["y"]):
            raise ValueError("Velocity/scalar radial coordinates differ")
        radius = scalar["y"]
        mass_flux = scalar["rho"] * velocity["U_0"]
        area_weight = 2 * np.pi * radius
        integrate = lambda value: float(np.trapezoid(value * area_weight, radius))
        z_flux = integrate(mass_flux * scalar["Z"])
        rows.append({
            "height_mm": height,
            "sampledRadiusRange_m": [float(radius[0]), float(radius[-1])],
            "axisymmetricAdvectiveMassFlux_kg_s": integrate(mass_flux),
            "axisymmetricAdvectiveZFlux_kg_s": z_flux,
            "axisymmetricAxialMomentumFlux_N": integrate(mass_flux * velocity["U_0"]),
            "axisSampleAxialVelocity_m_s": float(velocity["U_0"][0]),
            "maximumAxialVelocity_m_s": float(max(velocity["U_0"])),
            "radialVelocityRange_m_s": [float(min(velocity["U_1"])), float(max(velocity["U_1"]))],
        })
        for path in (scalar_path, velocity_path):
            files[str(path)] = digest(path)
    return {
        "schema": "maders-retained-flow-audit/v1", "job": collection["job"],
        "case": collection["case"], "massBalance": mass_balance, "radialProfiles": rows,
        "inputs": files, "scientificAcceptance": False,
        "limitations": [
            "Axisymmetric profile quadrature excludes unsampled radial end caps.",
            "Advective Z flux excludes axial diffusion and transient storage; it is not a Z budget.",
            "Mass balance uses final Euler step and exact wedge patch fluxes, not full-annulus estimates.",
            "A small mass residual does not imply steady state or a correct momentum/transport model.",
            "Native log excerpt identity requires an external exact-job/source collection receipt.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("samples", "flux-collection", "mass-log", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = evaluate(args.samples, args.flux_collection, args.mass_log)
    if args.out.exists():
        raise ValueError("Refusing existing output directory")
    if not args.apply:
        print(json.dumps({"mode": "plan", "output": str(args.out), "audit": result}, indent=2))
        return
    args.out.mkdir(parents=True)
    (args.out / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["massBalance"], indent=2))


if __name__ == "__main__":
    main()
