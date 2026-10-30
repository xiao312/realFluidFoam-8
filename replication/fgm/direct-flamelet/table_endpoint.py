"""Close only declared numerical Cmin tails, preserving mass and reporting actual chemistry changes."""
import numpy as np

POLICY = "zero-progress-numerical-tail/v1"
LIMITS = {"Cmin": 1e-24, "species_change": 1e-24, "enthalpy_change_J_kg": 1e-8,
          "Sc_change_kg_m3_s": 1e-12, "Q_change_W_m3": 1e-6, "mass_sum_error": 1e-12,
          "progress_mapping_error": 1e-12}


def close(ct, gas, model, pressure):
    names = gas.species_names
    columns = [model["columns"].index("Y_" + name) for name in names]
    progress = [names.index("CO2"), names.index("CO")]
    other = [i for i in range(len(names)) if i not in progress]
    original_y = model["values"][:, :, columns].copy()
    original_min = model["c_min"].copy()
    if np.any(original_min < 0):
        raise ValueError("Negative Cmin is not an eligible numerical zero-endpoint tail")
    updated = original_y.copy()
    affected = np.flatnonzero((original_min > 0) & (original_min <= LIMITS["Cmin"]))
    records = []
    for i in affected:
        for j, eta in enumerate(model["eta"]):
            remaining = float((1 - eta) * original_min[i])
            before = updated[i, j, progress].copy()
            if j == 0:
                updated[i, j, progress] = 0.0
            else:
                for k in progress:
                    removed = min(float(updated[i, j, k]), remaining)
                    updated[i, j, k] -= removed
                    remaining -= removed
            actual_removed = float(np.sum(before - updated[i, j, progress]))
            major = other[int(np.argmax(updated[i, j, other]))]
            updated[i, j, major] += actual_removed
        records.append({"Z": float(model["z"][i]), "original_Cmin": float(original_min[i]),
            "original_CO2_eta0": float(original_y[i, 0, progress[0]]),
            "original_CO_eta0": float(original_y[i, 0, progress[1]]), "new_Cmin": 0.0})
        model["c_min"][i] = 0.0
    model["values"][:, :, columns] = updated
    model["values"][:, :, 2] = updated[:, :, progress].sum(axis=2)
    delta = updated - original_y
    changed_nodes = np.argwhere(np.any(delta != 0, axis=2))
    # Evaluate every altered composition, including any representable interior-row change.
    # One unchanged endpoint provides the exact zero audit when this policy changes no node.
    evaluated = changed_nodes if len(changed_nodes) else np.array([[0, 0]])
    zi, ci = evaluated[:, 0], evaluated[:, 1]
    temperature = model["values"][zi, ci, model["columns"].index("T_K")]
    before = ct.SolutionArray(gas, len(evaluated))
    after = ct.SolutionArray(gas, len(evaluated))
    before.TPY = temperature, pressure, original_y[zi, ci]
    after.TPY = temperature, pressure, updated[zi, ci]
    sources_before = before.net_production_rates * gas.molecular_weights
    sources_after = after.net_production_rates * gas.molecular_weights
    gas.TP = 298.15, 101325.0
    formation_h = gas.partial_molar_enthalpies / gas.molecular_weights
    elements = np.array([[gas.n_atoms(k, name) * gas.atomic_weight(name) / gas.molecular_weights[k]
                          for name in gas.element_names] for k in range(gas.n_species)])
    axis_c = model["c_min"][:, None] + model["eta"][None, :] * (model["c_max"] - model["c_min"])[:, None]
    source_delta = sources_after - sources_before
    finite = bool(np.all(np.isfinite(source_delta)) and np.all(np.isfinite(after.enthalpy_mass)))
    maximum = lambda values: float(np.max(abs(values))) if np.all(np.isfinite(values)) else None
    metrics = {"species_change": maximum(delta), "enthalpy_change_J_kg": maximum(after.enthalpy_mass - before.enthalpy_mass),
        "Sc_change_kg_m3_s": maximum(source_delta[:, progress].sum(axis=1)),
        "Q_change_W_m3": maximum(source_delta @ formation_h), "mass_sum_error": maximum(updated.sum(axis=2) - 1),
        "progress_mapping_error": maximum(model["values"][:, :, 2] - axis_c)}
    within = finite and all(metrics[key] is not None and metrics[key] <= LIMITS[key] for key in metrics)
    return {"schema": "zero-endpoint-projection/v1", "policy": POLICY, "limits": LIMITS,
        "applied_to_new_derivation": True, "within_numerical_bounds": bool(within), "affected_rows": len(affected),
        "affected_nodes": len(changed_nodes), "affected_interior_eta_nodes": int(np.sum(changed_nodes[:, 1] != 0)) if len(changed_nodes) else 0,
        "original_Cmin_max": float(np.max(original_min)), "remaining_positive_Cmin_rows": int(np.sum(model["c_min"] > 0)),
        "strict_C0_row_queries_refused_before": int(np.sum(original_min > 0)),
        "strict_C0_row_queries_refused_after": int(np.sum(model["c_min"] > 0)),
        "minimum_species_after": float(np.min(updated)), "metrics": metrics,
        "max_element_mass_fraction_change": maximum(delta @ elements),
        "max_species_source_change_kg_m3_s": maximum(source_delta),
        "max_density_change_kg_m3": maximum(after.density - before.density),
        "source_evaluation_scope": "Cantera exact T/Y before and after at every altered node, including eta interiors; not an interpolated-source comparison",
        "source_and_temperature_adjusted": False, "raw_profiles_modified": False,
        "affine_mapping": "Subtract (1-eta)*old_Cmin from raw CO2+CO; stored C is actual species sum; no lookup tolerance changed",
        "original_tails": records, "scientific_acceptance": False}
