"""Audit methane elemental profiles and reconstructed conservative face fluxes."""
import argparse
import csv
import json
from pathlib import Path

import cantera as ct
import numpy as np

from analyze_soret import digest, inspect_native_fluxes, read_profile, require


def element_weights(gas):
    return np.array([
        [gas.n_atoms(k, e)*gas.atomic_weights[e]/gas.molecular_weights[k]
         for e in range(gas.n_elements)] for k in range(gas.n_species)])


def verify_stoichiometry(gas, weights):
    """Use an explicit balanced reaction, then perturb elements while retaining total mass."""
    gas.TPX = 298, ct.one_atm, "CH4:1,O2:2,N2:7.523809523809524"
    reactants = gas.Y.copy()
    gas.TPX = 298, ct.one_atm, "CO2:1,H2O:2,N2:7.523809523809524"
    products = gas.Y.copy()
    error = float(np.max(abs((products-reactants)@weights)))
    require(error < 1e-14, "Stoichiometric element fixture failed")
    products[gas.species_index("CO2")] -= 1e-3
    products[gas.species_index("N2")] += 1e-3
    require(abs(products.sum()-1) < 1e-14, "Perturbation changed total mass")
    perturbed = float(np.max(abs((products-reactants)@weights)))
    require(perturbed > 2e-4, "Element-changing perturbation was not detected")
    return dict(balanced_maximum_element_error=error,
                normalized_perturbation_maximum_element_error=perturbed)


def evaluate(row, snapshot, flux_directory, mechanism, gas, weights):
    require(row["scheduler"][0] == "COMPLETED" and row["screen_passed"],
            "Require a completed, numerically screened observation")
    directory = snapshot/"jobs"/str(row["job"])
    hashes = [line.split()[0] for line in (directory/"input-sha256.txt").read_text().splitlines()
              if line.split()[-1].endswith("/ideal.yaml")]
    require(hashes == [digest(mechanism)], "Mechanism differs from the observed input")
    path = directory/"result/profile.csv"
    require(digest(path) == row["output_sha256"]["profile.csv"], "Profile changed")
    profile, names = read_profile(path)
    require(names == gas.species_names, "Mechanism/profile species order mismatch")
    fields = [name for name in profile.dtype.names if name.startswith("Y_")]
    fractions = np.column_stack([profile[name] for name in fields])
    require(np.max(abs(fractions.sum(axis=1)-1)) < 1e-7, "Species sum screen failed")
    gas.TP = 298, row["pressure_atm"]*ct.one_atm
    gas.set_equivalence_ratio(row["phi"], "CH4", "O2:0.21,N2:0.79")
    feed = gas.Y@weights
    elements = fractions@weights
    active = feed > 1e-12
    mass = profile["rho_kg_m3"]*profile["U_m_s"]
    require(np.all(mass > 0), "Expected positive flame mass flow")
    endpoint = (elements[-1]-feed)[active]/feed[active]
    record = dict(
        job=row["job"], stage=row["stage"], phi=row["phi"], soret=row["soret"],
        source=row["source"], build=row["build"], executable_sha256=row["executable_sha256"],
        speed_cm_s=row["screen"]["speed_cm_s"],
        maximum_species_sum_error=float(np.max(abs(fractions.sum(axis=1)-1))),
        active_elements=list(np.array(gas.element_names)[active]),
        outlet_minus_feed_relative=dict(zip(np.array(gas.element_names)[active], map(float, endpoint))),
        maximum_inactive_element_fraction=float(np.max(abs(elements[:, ~active])))
            if np.any(~active) else 0.,
        profile_sha256=digest(path))
    if not row["soret"]:
        record["face_flux_status"] = "Unavailable: disabled-Soret run has no native face export"
        return record
    path = flux_directory/"jobs"/str(row["job"])/"result/soret-flux.csv"
    require(digest(path) == row["soret_flux_sha256"], "Native flux changed")
    errors, _, _ = inspect_native_fluxes(path, profile, names)
    with path.open(newline="") as stream:
        diffusion = np.array([float(r["total_kg_m2_s"]) for r in csv.DictReader(stream)])
    diffusion = diffusion.reshape(len(profile)-1, len(names))
    face_mass = .5*(mass[:-1]+mass[1:])
    flux = face_mass[:, None]*elements[:-1]+diffusion@weights
    reference = face_mass[0]*feed
    relative = np.ptp(flux[:, active], axis=0)/abs(reference[active])
    record.update(
        face_flux_status="Reconstructed positive-upwind advection plus native species diffusion",
        conservative_element_face_span_relative=dict(zip(
            np.array(gas.element_names)[active], map(float, relative))),
        first_face_minus_feed_over_massflow=float(np.max(abs(flux[0]-reference))/face_mass[0]),
        last_face_minus_outlet_over_massflow=float(
            np.max(abs(flux[-1]-face_mass[-1]*elements[-1]))/face_mass[-1]),
        native_flux_residuals=errors, native_flux_sha256=digest(path))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ("observation", "flux_directory", "mechanism", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "Choose a new output file")
    observation = json.loads(args.observation.read_text(encoding="utf-8"))
    rows = observation["jobs"]
    require(rows and len({row["job"] for row in rows}) == len(rows), "Empty or duplicate jobs")
    gas = ct.Solution(str(args.mechanism))
    weights = element_weights(gas)
    fixtures = verify_stoichiometry(gas, weights)
    runs = [evaluate(row, Path(observation["snapshot"]), args.flux_directory,
                     args.mechanism, gas, weights) for row in rows]
    report = dict(
        observation_sha256=digest(args.observation), mechanism_sha256=digest(args.mechanism),
        script_sha256=digest(Path(__file__)), cantera_version=ct.__version__,
        fixtures=fixtures, runs=runs, scientific_acceptance=False,
        limits=["Upwind advective face flux is reconstructed, not the stock species residual",
                "No composition normalization or solution adjustment is applied",
                "Profile density is the saved thermodynamic value; tiny species-sum errors remain explicit",
                "Element-flux spans are diagnostics, not a flame-speed error estimate",
                "This audit does not reconstruct heat conduction or assign energy conservation"])
    print(json.dumps(report, indent=2))
    if args.action == "apply":
        args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
