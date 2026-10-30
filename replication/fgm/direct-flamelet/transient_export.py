"""Export actual transient flamelet frames, never interpolated reaction rates."""
import csv
import copy
import numpy as np
from common import sha256, write_json
from metadata import phase_metadata


def check_rate_interface(gas, mechanism, streams, config):
    """Three finite-rate chemical states qualify the imported kernel, not a flame."""
    rows = []
    for mixture in (.1, .2, .6):
        unburnt = mixture * streams["fuel"]["Y"] + (1 - mixture) * streams["oxidizer"]["Y"]
        enthalpy = mixture * streams["fuel"]["h"] + (1 - mixture) * streams["oxidizer"]["h"]
        gas.HPY = enthalpy, config["pressure_pa"], unburnt
        gas.equilibrate("HP")
        gas.HPY = enthalpy, config["pressure_pa"], .5 * gas.Y + .5 * unburnt
        cantera_source = gas.net_production_rates * gas.molecular_weights
        griffon_source = np.zeros(gas.n_species)
        mechanism.griffon.production_rates(gas.T, gas.density, gas.Y, griffon_source)
        error = float(np.max(np.abs(griffon_source - cantera_source)) / max(np.max(np.abs(cantera_source)), 1.0))
        rows.append({"mixture_fraction": mixture, "T_K": gas.T, "peak_scaled_rate_error": error})
    return {"kind": "chemical-kernel-interface-check; not flame validation", "points": rows,
            "max_peak_scaled_error": max(row["peak_scaled_rate_error"] for row in rows), "limit": 1e-8}


def export_frames(ct, gas, mechanism, streams, config, settings, receipt, args, z, times, temperatures, fractions):
    gas.TP = 298.15, 101325.0
    formation_enthalpies = gas.partial_molar_enthalpies / gas.molecular_weights
    progress_indices = [gas.species_index(name) for name in ("CO2", "CO")]
    progress = fractions[:, :, progress_indices].sum(axis=2)
    zst = 1 / (1 + gas.stoich_air_fuel_ratio(config["fuel"]["mole_fractions"], config["oxidizer"]["mole_fractions"], basis="mole"))
    progress_st = np.array([np.interp(zst, z, row) for row in progress])
    targets = np.linspace(float(np.min(progress_st)), float(np.max(progress_st)), settings["max_export_frames"])
    selected = sorted({0, len(times) - 1, *[int(np.argmin(np.abs(progress_st - value))) for value in targets]})
    metadata = phase_metadata(ct, gas, args.mechanism, args.mechanism_sha256, args.source_commit, args.environment_sha256)
    write_json(args.out / "phase-metadata.json", metadata)
    members, frame_metrics = [], []
    species_names = gas.species_names
    for index in selected:
        destination = args.out / f"frame-{index:06d}"
        destination.mkdir()
        rows, energy_errors, element_errors, rate_errors = [], [], [], []
        for j, mixture in enumerate(z):
            raw_y = fractions[index, j]
            gas.TPY = temperatures[index, j], config["pressure_pa"], raw_y
            source = gas.net_production_rates * gas.molecular_weights
            griffon_source = np.zeros(gas.n_species)
            # Upstream Cython parameter names are misleading; C++ and tests take T,rho.
            mechanism.griffon.production_rates(gas.T, gas.density, gas.Y, griffon_source)
            rate_errors.append(float(np.max(np.abs(source - griffon_source) / (np.abs(source) + 1.0))))
            bilger = gas.mixture_fraction(config["fuel"]["mole_fractions"], config["oxidizer"]["mole_fractions"], basis="mole", element="Bilger")
            mixed_h = mixture * streams["fuel"]["h"] + (1 - mixture) * streams["oxidizer"]["h"]
            energy_errors.append(float(gas.enthalpy_mass - mixed_h))
            mixed_y = mixture * streams["fuel"]["Y"] + (1 - mixture) * streams["oxidizer"]["Y"]
            # Element mass fractions are linear in Y, so evaluate exact atom balances.
            local_error = []
            for element in gas.element_names:
                coefficients = np.array([gas.n_atoms(k, element) * gas.atomic_weight(element) / gas.molecular_weights[k]
                                         for k in range(gas.n_species)])
                local_error.append(abs(float(np.dot(coefficients, raw_y - mixed_y))))
            element_errors.append(max(local_error))
            rows.append([mixture, bilger, gas.T, gas.density, gas.enthalpy_mass,
                         -float(np.dot(gas.partial_molar_enthalpies, gas.net_production_rates)),
                         -float(np.dot(formation_enthalpies, source)), float(progress[index, j]),
                         float(np.sum(source[progress_indices])), *raw_y, *source])
        with (destination / "profile.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Z_coordinate", "Z_Bilger", "T_K", "rho_kg_m3", "h_J_kg", "Qdot_W_m3",
                             "Qdot_formation_298K_W_m3", "Y_CO2_plus_CO", "omega_CO2_plus_CO_kg_m3_s"] +
                            ["Y_" + name for name in species_names] + ["omega_Y_" + name + "_kg_m3_s" for name in species_names])
            writer.writerows(rows)
        metrics = {"physical_time_s": float(times[index]), "peak_temperature_k": float(np.max(temperatures[index])),
                   "C_at_stoichiometry": float(progress_st[index]),
                   "enthalpy_mixing_max_error_J_kg": max(abs(value) for value in energy_errors),
                   "element_mass_fraction_max_error": max(element_errors),
                   "griffon_cantera_max_regularized_rate_error": max(rate_errors),
                   "rate_error_denominator": "abs(Cantera mass rate) + 1 kg/(m3 s), per species",
                   "species_sum_max_error": float(np.max(abs(fractions[index].sum(axis=1) - 1))),
                   "minimum_species_mass_fraction": float(np.min(fractions[index]))}
        qualified = metrics["species_sum_max_error"] <= 1e-8 and metrics["minimum_species_mass_fraction"] >= -1e-8
        write_json(destination / "diagnostics.json", metrics)
        snapshot = copy.deepcopy(receipt)
        snapshot.update(status="transient_snapshot", physical_export_qualified=qualified,
                        coordinate="mixture_fraction", physical_time_s=float(times[index]),
                        initialization="fresh HP equilibrium at t=0; actual transient integration thereafter",
                        artifacts={name: sha256(destination / name) for name in ("profile.csv", "diagnostics.json")})
        write_json(destination / "receipt.json", snapshot)
        role = "held-out" if len(members) % 5 == 4 and index != len(times) - 1 else "training"
        members.append({"id": destination.name, "directory": destination.name,
                        "receipt_sha256": sha256(destination / "receipt.json"), "role": role})
        frame_metrics.append(metrics)
    write_json(args.out / "family-manifest.json", {"schema": "direct-flamelet-family/v1",
               "metadata_sha256": sha256(args.out / "phase-metadata.json"), "z_points": settings["table_z_points"],
               "eta_points": settings["table_eta_points"], "members": members,
               "holdout_scope": "entire physical time frames; independent chi trajectory remains required"})
    return {"selected_frames": len(selected), "frame_metrics": frame_metrics,
            "maximum_element_error": max(row["element_mass_fraction_max_error"] for row in frame_metrics),
            "maximum_enthalpy_error_J_kg": max(row["enthalpy_mixing_max_error_J_kg"] for row in frame_metrics),
            "maximum_kinetics_rate_error": max(row["griffon_cantera_max_regularized_rate_error"] for row in frame_metrics),
            "progress_st_start_end": [float(progress_st[0]), float(progress_st[-1])],
            "full_progress_coverage_qualified": False, "scientific_acceptance": False}
