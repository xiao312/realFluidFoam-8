"""Report and project only declared species roundoff at table export, preserving raw C."""
import hashlib
import numpy as np


def project(model, metadata):
    species = metadata["speciesOrder"]
    indices = [model["columns"].index("Y_" + name) for name in species]
    progress = [species.index(name) for name in ("CO2", "CO")]
    allowed = [i for i in range(len(species)) if i not in progress]
    before = model["values"][:, :, indices].copy()
    after = before.copy()
    negative_limit, correction_limit = 2e-10, 2e-9
    if np.min(before) < -negative_limit:
        raise ValueError(f"Material table species negative {np.min(before)} below {-negative_limit}")
    if np.min(before[:, :, progress]) < 0:
        raise ValueError("Negative progress species cannot be projected while preserving raw C")
    elements = sorted({element for item in metadata["species"] for element in item["composition"]})
    coefficients = np.array([[item["composition"].get(element, 0) / item["molecularWeight_kg_kmol"]
                              for element in elements] for item in metadata["species"]])
    changes = []
    for i in range(after.shape[0]):
        for j in range(after.shape[1]):
            original, corrected = before[i, j], after[i, j]
            corrected[corrected < 0] = 0
            correction = float(np.sum(corrected) - 1)
            if np.max(abs(corrected - original)) > correction_limit or abs(correction) > correction_limit:
                raise ValueError(f"Composition correction exceeds {correction_limit} at ({i},{j})")
            major = allowed[int(np.argmax(corrected[allowed]))]
            corrected[major] -= correction
            if corrected[major] < 0:
                raise ValueError(f"No positive non-progress mass reservoir at ({i},{j})")
            delta = corrected - original
            if np.any(delta):
                changes.append({"z_index": i, "eta_index": j, "Z": float(model["z"][i]),
                    "eta": float(model["eta"][j]), "minimum_before": float(np.min(original)),
                    "negative_entries": int(np.sum(original < 0)), "balance_species": species[major],
                    "max_absolute_correction": float(np.max(abs(delta))),
                    "mass_sum_change": float(np.sum(delta)),
                    "progress_change": float(np.sum(delta[progress])),
                    "element_moles_change_kmol_kg": dict(zip(elements, map(float, delta @ coefficients)))})
    model["values"][:, :, indices] = after
    difference = after - before
    return {"schema": "table-roundoff-projection/v1", "negative_limit": negative_limit,
            "maximum_allowed_correction": correction_limit,
            "minimum_before": float(np.min(before)), "minimum_after": float(np.min(after)),
            "changed_nodes": len(changes), "negative_entries_before": int(np.sum(before < 0)),
            "max_absolute_correction": float(np.max(abs(difference))),
            "max_mass_sum_error_after": float(np.max(abs(after.sum(axis=2) - 1))),
            "max_progress_change": float(np.max(abs(difference[:, :, progress].sum(axis=2)))),
            "max_element_moles_change_kmol_kg": float(np.max(abs(difference @ coefficients))),
            "input_Y_float64_sha256": hashlib.sha256(before.tobytes()).hexdigest(),
            "output_Y_float64_sha256": hashlib.sha256(after.tobytes()).hexdigest(),
            "source_temperature_adjusted": False, "raw_profiles_modified": False,
            "scientific_acceptance": False, "nodes": changes}
