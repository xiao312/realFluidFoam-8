"""Physical field exports and diagnostics, not a paper-acceptance evaluator."""
import csv
import numpy as np


def export_flame(flame, gas, streams, config, output):
    x = flame.grid.copy()
    temperature = flame.T.copy()
    species = flame.Y.copy()
    density = flame.density.copy()
    velocity = flame.velocity.copy()
    spread_rate = flame.spread_rate.copy()
    mixture = flame.mixture_fraction("Bilger")
    element_names = [name for name in ("C", "H", "O") if name in gas.element_names]
    n = len(x)
    enthalpy = np.zeros(n)
    diffusivity = np.zeros(n)
    heat_release = np.zeros(n)
    formation_heat_release = np.zeros(n)
    species_sources = np.zeros_like(species)
    source = np.zeros(n)
    source_mass_error = np.zeros(n)
    source_scale = np.zeros(n)
    elements = {name: np.zeros(n) for name in element_names}
    progress_indices = [gas.species_index(name) for name in ("CO2", "CO")]
    # Ideal-gas species enthalpy is independent of pressure/composition. Keep the
    # formation-reference source separate from Cantera's temperature-local Qdot.
    gas.TP = 298.15, 101325.0
    reference_enthalpies = gas.partial_molar_enthalpies / gas.molecular_weights
    for j in range(n):
        gas.TPY = temperature[j], config["pressure_pa"], species[:, j]
        enthalpy[j] = gas.enthalpy_mass
        diffusivity[j] = gas.thermal_conductivity / (gas.density * gas.cp_mass)
        production = gas.net_production_rates * gas.molecular_weights
        species_sources[:, j] = production
        source[j] = sum(production[k] for k in progress_indices)
        heat_release[j] = -np.dot(gas.partial_molar_enthalpies, gas.net_production_rates)
        formation_heat_release[j] = -np.dot(reference_enthalpies, production)
        source_mass_error[j] = abs(np.sum(production))
        source_scale[j] = np.sum(np.abs(production))
        for name in element_names:
            elements[name][j] = gas.elemental_mass_fraction(name)
    progress = np.sum(species[progress_indices, :], axis=0)
    chi = 2 * diffusivity * np.gradient(mixture, x) ** 2
    quantities = [x, temperature, density, velocity, spread_rate, mixture, enthalpy,
                  heat_release, formation_heat_release, progress, source, diffusivity, chi,
                  *species, *species_sources]
    finite = all(np.all(np.isfinite(q)) for q in quantities)
    if not finite:
        raise ValueError("Nonfinite physical fields after solver return")
    species_sum_error = float(np.max(np.abs(species.sum(axis=0) - 1)))
    species_min = float(np.min(species))
    if species_sum_error > 1e-5 or species_min < -1e-6:
        raise ValueError(f"Unphysical species after solver return: sum error={species_sum_error}, min={species_min}")
    if np.max(temperature) <= max(s["temperature"] for s in streams.values()) + 10 or np.max(heat_release) <= 0:
        raise ValueError("Solver returned an extinguished or non-exothermic state")
    names = ["x_m", "T_K", "rho_kg_m3", "u_m_s", "spread_rate_s_inverse", "Z_Bilger",
             "h_J_kg", "Qdot_W_m3", "Qdot_formation_298K_W_m3", "Y_CO2_plus_CO", "omega_CO2_plus_CO_kg_m3_s",
             "thermal_diffusivity_m2_s", "chi_s_inverse"] + ["Y_" + name for name in gas.species_names] + [
                 "omega_Y_" + name + "_kg_m3_s" for name in gas.species_names]
    with (output / "profile.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(names)
        writer.writerows(zip(*quantities))

    # Axisymmetric continuity includes radial outflow: d(rho*u)/dx + 2*rho*V=0.
    # Axial mass flux alone is not constant in a counterflow flame.
    radial_sink = 2 * density * spread_rate
    radial_integral = np.r_[0, np.cumsum(0.5 * (radial_sink[1:] + radial_sink[:-1]) * np.diff(x))]
    continuity_error = density * velocity - density[0] * velocity[0] + radial_integral
    mdot_scale = max(config["fuel_mdot_kg_m2_s"], config["oxidizer_mdot_kg_m2_s"])
    reference_enthalpy = mixture * streams["fuel"]["h"] + (1 - mixture) * streams["oxidizer"]["h"]
    enthalpy_error = enthalpy - reference_enthalpy
    element_errors = {}
    for name in element_names:
        inlet_element = {}
        for inlet, state in streams.items():
            gas.TPY = state["temperature"], config["pressure_pa"], state["Y"]
            inlet_element[inlet] = gas.elemental_mass_fraction(name)
        target = mixture * inlet_element["fuel"] + (1 - mixture) * inlet_element["oxidizer"]
        element_errors[name] = float(np.max(np.abs(elements[name] - target)))
    stoich = 1 / (1 + gas.stoich_air_fuel_ratio(config["fuel"]["mole_fractions"],
                                               config["oxidizer"]["mole_fractions"], basis="mole"))
    monotone = bool(np.all(np.diff(mixture) <= 1e-7))
    # Interpolate only when the measured field supports a single stoichiometric crossing.
    chi_st = float(np.interp(stoich, mixture[::-1], chi[::-1])) if monotone else None
    peak = int(np.argmax(temperature))
    half_hot = temperature > (max(s["temperature"] for s in streams.values()) + np.max(temperature)) / 2
    hot_span = float(x[np.where(half_hot)[0][-1]] - x[np.where(half_hot)[0][0]])
    return {"grid_points": n, "finite_fields": finite, "peak_temperature_k": float(np.max(temperature)),
            "temperature_peak_x_m": float(x[peak]), "temperature_peak_Z": float(mixture[peak]),
            "peak_Qdot_W_m3": float(np.max(heat_release)),
            "peak_formation_Qdot_W_m3": float(np.max(formation_heat_release)),
            "heat_release_definitions": {
                "Qdot_W_m3": "-sum(h_i(T)*omega_i), current species total enthalpies",
                "Qdot_formation_298K_W_m3": "-sum(h_i(298.15 K, 101325 Pa)*omega_i), supplied ideal-gas mechanism",
                "OF8_use": "requires matching the OF8 species reference enthalpies and energy equation"},
            "reference_species_enthalpies_298K_J_kg": dict(zip(gas.species_names, reference_enthalpies.tolist())),
            "integrated_Qdot_W_m2": float(np.trapezoid(heat_release, x)),
            "half_temperature_zone_width_fraction": hot_span / config["width_m"],
            "species_sum_max_absolute_error": species_sum_error, "minimum_mass_fraction": species_min,
            "continuity_integral_max_error_kg_m2_s": float(np.max(np.abs(continuity_error))),
            "continuity_integral_max_relative_error": float(np.max(np.abs(continuity_error))) / mdot_scale,
            "elemental_mixing_max_absolute_error": element_errors,
            "enthalpy_mixing_max_error_J_kg": float(np.max(np.abs(enthalpy_error))),
            "enthalpy_mixing_rms_error_J_kg": float(np.sqrt(np.mean(enthalpy_error ** 2))),
            "chemistry_mass_source_max_error_kg_m3_s": float(np.max(source_mass_error)),
            "chemistry_mass_source_error_relative_peak": float(np.max(source_mass_error) / max(np.max(source_scale), 1e-300)),
            "Z_st": float(stoich), "Z_monotone": monotone, "chi_st_s_inverse": chi_st,
            "chi_definition": "2 * lambda/(rho*cp) * (dZ_Bilger/dx)^2; unity-Lewis model",
            "diagnostic_status": "reported; not independently accepted or grid-qualified"}
