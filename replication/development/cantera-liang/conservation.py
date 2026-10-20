"""Check native methane conservative balances without changing saved fields."""
import argparse
import csv
import json
from pathlib import Path

import cantera as ct
import numpy as np

from analyze_soret import digest, read_profile, require
from element_balance import element_weights


def maximum(values):
    return float(np.max(np.abs(values)))


def table(path):
    values = np.genfromtxt(path, delimiter=",", names=True)
    with path.open(newline="") as stream:
        names = next(csv.reader(stream))
    require(values.ndim == 1 and len(values) > 10, "Incomplete native table")
    require(len(set(names)) == len(names) == len(values.dtype.names), "Ambiguous table schema")
    require(all(np.isfinite(values[name]).all() for name in values.dtype.names), "Nonfinite table")
    # Retain exact mechanism names such as CH2(S), despite NumPy sanitization.
    return {raw: values[field] for raw, field in zip(names, values.dtype.names)}


def columns(data, prefix, names):
    return np.column_stack([data[prefix+name] for name in names])


def evaluate(row, snapshot, balances, mechanism):
    require(row["screen_passed"] and row["scheduler"][0] == "COMPLETED", "Unscreened solve")
    options = set(row["variant"].split(","))
    require({"conservative-species", "total-enthalpy"} <= options and
            not options & {"soret", "manual-soret", "pure-species-flux"}, "Wrong residual variant")
    directory = snapshot/"jobs"/str(row["job"])
    result = directory/"result"
    native = balances/"jobs"/str(row["job"])/"result"
    for name, key in (("source-revision.txt", "source"),):
        require((directory/name).read_text().strip() == row[key], "Source mismatch")
    require((directory/"build-path.txt").read_text().strip().endswith("/"+str(row["build"])),
            "Build mismatch")
    require((directory/"executable.sha256").read_text().split()[0] == row["executable_sha256"],
            "Executable mismatch")
    require((result/"model-variant.txt").read_text().strip() == row["variant"], "Variant mismatch")
    for name, expected in row["output_sha256"].items():
        require(digest(result/name) == expected, "Observed output changed: "+name)
    require(digest(native/"profile.csv") == row["output_sha256"]["profile.csv"],
            "Balance snapshot profile mismatch")
    recorded = [line.split()[0] for line in (directory/"input-sha256.txt").read_text().splitlines()
                if line.split()[-1].endswith("/ideal.yaml")]
    require(recorded == [digest(mechanism)], "Mechanism mismatch")
    gas = ct.Solution(str(mechanism))
    _, names = read_profile(result/"profile.csv")
    require(names == gas.species_names, "Species order mismatch")
    weights = element_weights(gas)
    nodes, faces, profile = [table(path) for path in
        (native/"balance-nodes.csv", native/"balance-faces.csv", result/"profile.csv")]
    require(len(faces["x_left_m"])+1 == len(nodes["x_m"]) == len(profile["x_m"]), "Grid size mismatch")
    require(np.all(nodes["interior"][1:-1] == 1) and
            np.all(nodes["interior"][[0, -1]] == 0), "Invalid interior mask")
    require(maximum(nodes["x_m"]-profile["x_m"]) < 1e-14 and
            maximum(nodes["T_K"]-profile["T_K"]) < 1e-9, "Native/profile state mismatch")
    require(maximum(faces["x_left_m"]-nodes["x_m"][:-1]) < 1e-14 and
            maximum(faces["x_right_m"]-nodes["x_m"][1:]) < 1e-14, "Face grid mismatch")
    dx = np.diff(nodes["x_m"])
    require(np.all(dx > 0) and np.all(nodes["rho_kg_m3"] > 0) and
            np.all(nodes["cp_J_kgK"] > 0), "Invalid state")
    require(np.all(nodes["massflow_kg_m2s"] > 0), "Expected positive mass flow")
    width = .5*(dx[:-1]+dx[1:])
    y, rates, residual = [columns(nodes, p, names) for p in ("Y_", "source_", "R_")]
    diffusion, flux, partial_h = [columns(faces, p, names) for p in ("J_", "G_", "h_")]
    require(maximum(y-columns(profile, "Y_", names)) < 1e-14, "Species changed")
    mass = faces["massflow_kg_m2s"]
    mass_scale, production_scale = maximum(mass), max(1e-100, maximum(rates))
    species_rhs = rates[1:-1]-np.diff(flux, axis=0)/width[:, None]
    energy_rhs = -np.diff(faces["H_total_W_m2"])/width
    energy_scale = max(1., maximum(faces["H_adv_W_m2"]),
                       maximum(faces["H_cond_W_m2"]), maximum(faces["H_species_W_m2"]))
    gas.TP = float(profile["T_K"][0]), row["pressure_atm"]*ct.one_atm
    gas.set_equivalence_ratio(row["phi"], "CH4", "O2:0.21,N2:0.79")
    feed_y = gas.Y.copy()
    element_flux = flux@weights
    active = feed_y@weights > 1e-12
    spans = np.ptp(element_flux, axis=0)
    relative = spans[active]/np.abs(element_flux[0, active])
    rho, cp = nodes["rho_kg_m3"][1:-1], nodes["cp_J_kgK"][1:-1]
    errors = {
        "face_mass_average": maximum(mass-.5*(nodes["massflow_kg_m2s"][:-1]+
                                              nodes["massflow_kg_m2s"][1:]))/mass_scale,
        "species_flux_definition": maximum(flux-mass[:, None]*y[:-1]-diffusion)/mass_scale,
        "species_residual_identity": maximum(residual[1:-1]*rho[:, None]-species_rhs)/
                                    max(production_scale, maximum(species_rhs)),
        "species_integral_identity": maximum(
            np.sum(width[:, None]*(rho[:, None]*residual[1:-1]-rates[1:-1]), axis=0)
            +flux[-1]-flux[0])/mass_scale,
        "energy_advective_definition": maximum(faces["H_adv_W_m2"]-
                                               mass*nodes["h_J_kg"][:-1])/energy_scale,
        "energy_conductive_definition": maximum(faces["H_cond_W_m2"]+
            faces["lambda_W_mK"]*np.diff(nodes["T_K"])/dx)/energy_scale,
        "energy_species_definition": maximum(faces["H_species_W_m2"]-
                                             np.sum(diffusion*partial_h, axis=1))/energy_scale,
        "energy_decomposition": maximum(faces["H_total_W_m2"]-faces["H_adv_W_m2"]-
                                        faces["H_cond_W_m2"]-faces["H_species_W_m2"])/energy_scale,
        "energy_residual_identity": maximum(nodes["R_T_K_s"][1:-1]*rho*cp-energy_rhs)/
                                   max(1., energy_scale/float(np.min(width))),
        "energy_integral_identity": abs(float(np.sum(width*rho*cp*nodes["R_T_K_s"][1:-1]))+
            float(faces["H_total_W_m2"][-1]-faces["H_total_W_m2"][0]))/energy_scale,
        "chemical_mass_balance": maximum(rates.sum(axis=1))/production_scale,
        "chemical_element_balance": maximum(rates@weights)/production_scale,
    }
    metrics = dict(
        elemental_face_span_relative=dict(zip(np.array(gas.element_names)[active], map(float, relative))),
        inactive_element_face_span_over_massflow=maximum(spans[~active])/mass_scale
            if np.any(~active) else 0.,
        maximum_diffusion_mass_sum_over_massflow=maximum(diffusion.sum(axis=1))/mass_scale,
        feed_to_first_face_over_massflow=maximum(flux[0]-nodes["massflow_kg_m2s"][0]*feed_y)/mass_scale,
        outlet_state_to_last_face_over_massflow=maximum(
            flux[-1]-nodes["massflow_kg_m2s"][-1]*y[-1])/mass_scale,
        energy_flux_span_equivalent_K=float(np.ptp(faces["H_total_W_m2"])/
                                            (mass[0]*nodes["cp_J_kgK"][-1])),
        maximum_species_residual_s_1=maximum(residual[1:-1]),
        maximum_energy_residual_K_s=maximum(nodes["R_T_K_s"][1:-1]))
    checks = {name: value < 1e-10 for name, value in errors.items()}
    checks.update(
        numerical_screen=row["screen_passed"],
        elemental_flux=maximum(relative) < 1e-6,
        inactive_elements=metrics["inactive_element_face_span_over_massflow"] < 1e-7,
        diffusion_mass=metrics["maximum_diffusion_mass_sum_over_massflow"] < 1e-7,
        inlet_flux=metrics["feed_to_first_face_over_massflow"] < 1e-7,
        outlet_flux=metrics["outlet_state_to_last_face_over_massflow"] < 1e-7,
        energy_flux=metrics["energy_flux_span_equivalent_K"] < .05)
    return dict(job=row["job"], stage=row["stage"], phi=row["phi"], source=row["source"],
                build=row["build"], executable_sha256=row["executable_sha256"],
                speed_cm_s=row["screen"]["speed_cm_s"], Tb_K=float(nodes["T_K"][-1]),
                identity_errors=errors, balance_metrics=metrics,
                checks={name: bool(value) for name, value in checks.items()},
                failed_checks=[name for name, value in checks.items() if not value],
                output_sha256={name: digest(native/name) for name in
                               ("balance-nodes.csv", "balance-faces.csv", "profile.csv")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("observation", "balances", "mechanism", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "Use a new output file")
    observation = json.loads(args.observation.read_text())
    require(observation["jobs"] and len({r["job"] for r in observation["jobs"]}) ==
            len(observation["jobs"]), "Empty or duplicate jobs")
    runs = [evaluate(row, Path(observation["snapshot"]), args.balances, args.mechanism)
            for row in observation["jobs"]]
    report = dict(
        observation_sha256=digest(args.observation), mechanism_sha256=digest(args.mechanism),
        script_sha256=digest(Path(__file__)), runs=runs,
        conservation_qualified=all(not r["failed_checks"] for r in runs), scientific_acceptance=False,
        limits=["Boundary residual placeholders are excluded",
                "Native field identities and conservation do not identify Liang's implementation",
                "No saved field is normalized or altered",
                "Numerical thresholds are retained from the hydrogen audit"])
    print(json.dumps(report, indent=2))
    if args.action == "apply":
        args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
