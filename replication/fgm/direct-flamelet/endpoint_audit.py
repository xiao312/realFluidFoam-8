"""Measure strict zero-progress coverage and a proposed tail closure without altering a table."""
import numpy as np


def audit(ct, gas, model, pressure):
    indices = [model["columns"].index("Y_" + name) for name in gas.species_names]
    progress = [gas.species_index(name) for name in ("CO2", "CO")]
    others = [i for i in range(gas.n_species) if i not in progress]
    y = model["values"][:, 0, indices].copy()
    temperature = model["values"][:, 0, model["columns"].index("T_K")]
    proposed = y.copy()
    # This audit only proposes an endpoint change. It does not write new table data.
    for j in range(len(y)):
        removed = float(np.sum(proposed[j, progress]))
        proposed[j, progress] = 0.0
        major = others[int(np.argmax(proposed[j, others]))]
        proposed[j, major] += removed
    before = ct.SolutionArray(gas, len(y))
    after = ct.SolutionArray(gas, len(y))
    before.TPY = temperature, pressure, y
    after.TPY = temperature, pressure, proposed
    source_before = before.net_production_rates * gas.molecular_weights
    source_after = after.net_production_rates * gas.molecular_weights
    gas.TP = 298.15, 101325.0
    formation_h = gas.partial_molar_enthalpies / gas.molecular_weights
    source_change = source_after - source_before
    mass_difference = proposed - y
    elements = np.array([[gas.n_atoms(k, name) * gas.atomic_weight(name) / gas.molecular_weights[k]
                          for name in gas.element_names] for k in range(gas.n_species)])
    rows = [{"Z": float(model["z"][j]), "Cmin": float(model["c_min"][j]), "Cmax": float(model["c_max"][j]),
             "raw_C_from_species_at_eta0": float(np.sum(y[j, progress])),
             "strict_C0_query_admissible": bool(model["c_min"][j] <= 0 <= model["c_max"][j]),
             "minimum_species_after_existing_projection": float(np.min(y[j])),
             "Tdiag_K": float(temperature[j]), "Sc_table_kg_m3_s": float(model["values"][j, 0, 3]),
             "Q_table_W_m3": float(model["values"][j, 0, 4])} for j in range(len(y))]
    finite = bool(np.all(np.isfinite(source_before)) and np.all(np.isfinite(source_after)))
    maximum = lambda values: float(np.max(abs(values))) if np.all(np.isfinite(values)) else None
    return {"schema": "strict-endpoint-audit/v1", "table_changed": False,
        "Cmin_minimum": float(np.min(model["c_min"])), "Cmin_maximum": float(np.max(model["c_min"])),
        "strict_C0_refused_rows": sum(not row["strict_C0_query_admissible"] for row in rows),
        "negative_Cmin_rows": int(np.sum(model["c_min"] < 0)), "row_count": len(rows),
        "pure_stream_rows": [rows[0], rows[-1]],
        "proposed_endpoint_closure": {"description": "Set eta0 CO/CO2 numerical tails to zero and add removed mass to largest non-progress species; retain raw input/table and audit. Full row mapping must be updated consistently before export.",
            "max_removed_C": maximum(np.sum(y[:, progress], axis=1)), "max_absolute_species_change": maximum(mass_difference),
            "max_mass_sum_error_after": maximum(proposed.sum(axis=1) - 1),
            "max_element_mass_fraction_change": maximum(mass_difference @ elements),
            "max_h_change_J_kg_at_fixed_T": maximum(after.enthalpy_mass - before.enthalpy_mass),
            "max_density_change_kg_m3": maximum(after.density - before.density),
            "source_evaluations_finite": finite,
            "max_species_source_change_kg_m3_s": maximum(source_change),
            "max_Sc_change_kg_m3_s": maximum(source_change[:, progress].sum(axis=1)),
            "max_Qformation_change_W_m3": maximum(source_change @ formation_h),
            "chemical_evaluation_scope": "Cantera at exact table endpoint T/Y before and after proposed tail removal; not the interpolated table-source difference",
            "applied": False, "scientific_acceptance": False},
        "rows": rows}
