"""Audit native conservative flame balances; do not fit or alter a solution."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import cantera as ct
import numpy as np

from profile_diagnostics import profile_diagnostics
from ledger import identity


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_table(path):
    data = np.genfromtxt(path, delimiter=",", names=True)
    require(data.ndim == 1 and len(data) >= 3, "Incomplete native table")
    require(all(np.isfinite(data[name]).all() for name in data.dtype.names),
            "Nonfinite native table")
    return data


def columns(data, prefix, names):
    return np.column_stack([data[prefix+name] for name in names])


def maximum(value):
    return float(np.max(np.abs(value)))


def evaluate(row, mechanism):
    result = Path(row["result"])
    require((result/"completed.txt").is_file(), "Flame has not completed")
    config = dict(line.split(maxsplit=1) for line in
                  (result/"configuration.txt").read_text().splitlines() if line.strip())
    require(config["model_variant"] == row["variant"] == "conservative",
            "Expected the named conservative control")
    require(config["species_discretization"] == "conservative-face" and
            config["energy"] == "conservative-total-enthalpy" and config["Soret"] == "off",
            "Unexpected residual or transport option")
    require(config["case"] == str(row["case"]) and
            abs(float(config["phi"])-row["phi"]) < 1e-12, "Case identity mismatch")
    for key in ("width_m", "Tu_K", "grid_factor"):
        require(abs(float(config[key])-row[key]) < 1e-12, "Declared configuration differs: "+key)
    for key in ("steady_rtol", "steady_atol"):
        if key in row:
            require(abs(float(config[key])-row[key]) <= 1e-12*row[key],
                    "Declared tolerance differs: "+key)
    require(abs(float(config["pressure_Pa"])-row["pressure_atm"]*ct.one_atm) < 1e-6,
            "Pressure declaration mismatch")
    require(config["collider_concentration"] == "pressure-based", "Unexpected chemistry")
    source = (result.parent/"source-revision.txt").read_text().strip()
    build = identity(result, row, source)
    recorded = [line.split()[0] for line in
                (result.parent/"input-sha256.txt").read_text().splitlines()
                if line.split()[-1].endswith("/ideal.yaml")]
    require(recorded == [digest(mechanism)], "Mechanism does not match the run inputs")
    gas = ct.Solution(str(mechanism))
    names = gas.species_names
    element_weights = np.array([
        [gas.n_atoms(k, e)*gas.atomic_weights[e]/gas.molecular_weights[k]
         for e in range(gas.n_elements)] for k in range(gas.n_species)])
    nodes = read_table(result/"balance-nodes.csv")
    faces = read_table(result/"balance-faces.csv")
    profile = read_table(result/"profile.csv")
    require(len(faces)+1 == len(nodes) == len(profile), "Node/face dimensions differ")
    require(np.all(nodes["interior"][1:-1] == 1) and
            np.all(nodes["interior"][[0, -1]] == 0), "Invalid residual mask")
    require(maximum(nodes["x_m"]-profile["x_m"]) < 1e-14 and
            maximum(nodes["T_K"]-profile["T_K"]) < 1e-9, "Profile/native mismatch")
    require(maximum(faces["x_left_m"]-nodes["x_m"][:-1]) < 1e-14 and
            maximum(faces["x_right_m"]-nodes["x_m"][1:]) < 1e-14, "Face grid mismatch")
    dx = np.diff(nodes["x_m"])
    require(np.all(dx > 0) and np.all(nodes["rho_kg_m3"] > 0) and
            np.all(nodes["cp_J_kgK"] > 0), "Invalid grid or thermodynamic state")
    require(np.all(nodes["massflow_kg_m2s"] > 0), "Outlet/inlet pair requires positive flow")
    require(abs(nodes["x_m"][-1]-nodes["x_m"][0]-float(config["width_m"])) < 1e-12,
            "Domain length mismatch")
    width = .5*(dx[:-1]+dx[1:])
    y, rates, residual = [columns(nodes, prefix, names) for prefix in ("Y_", "source_", "R_")]
    diffusion, flux, partial_h = [columns(faces, prefix, names) for prefix in ("J_", "G_", "h_")]
    require(maximum(y-columns(profile, "Y_", names)) < 1e-14, "Saved species changed")
    mass = faces["massflow_kg_m2s"]
    mass_scale = maximum(mass)
    production_scale = max(1e-100, maximum(rates))
    species_rhs = rates[1:-1]-np.diff(flux, axis=0)/width[:, None]
    energy_rhs = -np.diff(faces["H_total_W_m2"])/width
    energy_scale = max(1., maximum(faces["H_adv_W_m2"]),
                       maximum(faces["H_cond_W_m2"]), maximum(faces["H_species_W_m2"]))
    gas.TP = float(config["Tu_K"]), float(config["pressure_Pa"])
    gas.set_equivalence_ratio(row["phi"], "H2", "O2:0.21,N2:0.79")
    feed_y = gas.Y.copy()
    element_flux = flux@element_weights
    active = feed_y@element_weights > 1e-12
    elemental_span = np.ptp(element_flux, axis=0)
    element_relative = elemental_span[active]/np.abs(element_flux[0, active])
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
        "energy_integral_identity": abs(float(np.sum(
            width*rho*cp*nodes["R_T_K_s"][1:-1]))+
            float(faces["H_total_W_m2"][-1]-faces["H_total_W_m2"][0]))/energy_scale,
        "chemical_mass_balance": maximum(rates.sum(axis=1))/production_scale,
        "chemical_element_balance": maximum(rates@element_weights)/production_scale,
    }
    metrics = {
        "elemental_face_span_relative": dict(zip(
            np.array(gas.element_names)[active], map(float, element_relative))),
        "inactive_element_face_span_over_massflow": maximum(elemental_span[~active])/mass_scale
            if np.any(~active) else 0.,
        "maximum_diffusion_mass_sum_over_massflow": maximum(diffusion.sum(axis=1))/mass_scale,
        "feed_to_first_face_over_massflow": maximum(
            flux[0]-nodes["massflow_kg_m2s"][0]*feed_y)/mass_scale,
        "outlet_state_to_last_face_over_massflow": maximum(
            flux[-1]-nodes["massflow_kg_m2s"][-1]*y[-1])/mass_scale,
        "energy_flux_span_equivalent_K": float(np.ptp(faces["H_total_W_m2"])/
            (mass[0]*nodes["cp_J_kgK"][-1])),
        "maximum_species_residual_s_1": maximum(residual[1:-1]),
        "maximum_energy_residual_K_s": maximum(nodes["R_T_K_s"][1:-1]),
    }
    diagnostics = profile_diagnostics(result)
    thermo = read_table(result/"property-checks.csv")
    diagnostics["maximum_cp_identity_error"] = maximum(thermo["relative_cp_fd_error"])
    diagnostics["maximum_enthalpy_euler_error"] = maximum(thermo["relative_enthalpy_euler_error"])
    with (result/"refinement.csv").open() as stream:
        levels = list(csv.DictReader(stream))
    require(len(levels) >= 2, "No refinement comparison")
    speed = float(levels[-1]["speed_cm_s"])
    grid_change = abs(speed/float(levels[-2]["speed_cm_s"])-1)
    require(abs(speed-100*profile["U_m_s"][0]) < 1e-10, "Refinement/profile speed mismatch")
    checks = {name: value < 1e-10 for name, value in errors.items()}
    checks.update(
        species_sum=diagnostics["max_species_sum_error"] < 1e-7,
        minimum_species=diagnostics["minimum_mass_fraction"] >= -1e-9,
        massflow=diagnostics["max_relative_massflux_change"] < .001,
        cp_identity=diagnostics["maximum_cp_identity_error"] < 1e-5,
        enthalpy_euler=diagnostics["maximum_enthalpy_euler_error"] < 1e-9,
        final_refinement=grid_change < .005,
        elemental_flux=maximum(element_relative) < 1e-6,
        inactive_elements=metrics["inactive_element_face_span_over_massflow"] < 1e-7,
        diffusion_mass=metrics["maximum_diffusion_mass_sum_over_massflow"] < 1e-7,
        inlet_flux=metrics["feed_to_first_face_over_massflow"] < 1e-7,
        outlet_flux=metrics["outlet_state_to_last_face_over_massflow"] < 1e-7,
        energy_flux=metrics["energy_flux_span_equivalent_K"] < .05)
    return dict(job=row["job"], case=row["case"], phi=row["phi"], source=source,
                build_identity=build, configuration=config, speed_cm_s=speed,
                Tb_K=float(nodes["T_K"][-1]), grid_change=grid_change,
                diagnostics=diagnostics, identity_errors=errors, balance_metrics=metrics,
                checks={name: bool(value) for name, value in checks.items()},
                failed_checks=[name for name, value in checks.items() if not value],
                output_sha256={name: digest(result/name) for name in
                    ("balance-nodes.csv", "balance-faces.csv", "profile.csv",
                     "refinement.csv", "configuration.txt", "property-checks.csv")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("manifest", "mechanism", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "Choose a new output file")
    rows = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    require(rows and len({r["job"] for r in rows}) == len(rows), "Empty or duplicate jobs")
    runs = [evaluate(row, args.mechanism) for row in rows]
    report = dict(
        inputs_sha256={name: digest(getattr(args, name)) for name in ("manifest", "mechanism")},
        script_sha256=digest(Path(__file__)), runs=runs,
        conservation_qualified=all(not run["failed_checks"] for run in runs),
        scientific_acceptance=False,
        limits=["Steady numerical conservation control, not recovered PREMIX code",
                "Boundary residual placeholders are excluded from all residual identities",
                "Paper comparison and genuine mesh refinement are separate requirements"])
    print(json.dumps(report, indent=2))
    if args.action == "apply":
        args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
