"""Select one declared extinction path; retain exclusion and terminal-tail evidence."""
import numpy as np

POLICY = "post-peak-extinction/v1"
LIMITS = {"tail_progress": 1e-12, "temperature_K": 1e-4, "species_absolute": 2e-9,
          "density_relative": 1e-6, "source_peak_relative": 1e-8}


def select(states, times, columns, mixture):
    if len(times) != len(states) or np.any(np.diff(times) <= 0):
        raise ValueError("Extinction selection requires distinct, increasing physical frame times")
    peak = int(np.argmax(states[:, 2]))
    selected = np.arange(peak, len(states))
    final = states[-1]
    species = [i for i, name in enumerate(columns) if name.startswith("Y_") and name != "Y_CO2_plus_CO"]
    scales = np.maximum(np.max(abs(states), axis=0), 1.0)
    audit = {"Z": float(mixture), "policy": POLICY, "start_time_s": float(times[peak]),
             "peak_frame_index": peak, "early_excluded_count": peak,
             "early_excluded_times_s": times[:peak].tolist(), "tail_exclusions": [], "limits": LIMITS,
             "final_C": float(final[2]), "final_time_s": float(times[-1])}
    keep = []
    for index in selected:
        state = states[index]
        difference = abs(state - final)
        metrics = {"temperature_K": float(difference[0]),
            "species_absolute": float(np.max(difference[species])),
            "density_relative": float(difference[1] / max(abs(final[1]), 1e-12)),
            "source_peak_relative": float(max(difference[3] / scales[3], difference[4] / scales[4]))}
        close = all(metrics[key] <= LIMITS[key] for key in metrics)
        if index != len(states) - 1 and state[2] <= LIMITS["tail_progress"] and final[2] <= LIMITS["tail_progress"] and close:
            audit["tail_exclusions"].append({"time_s": float(times[index]), "C": float(state[2]), **metrics})
        else:
            keep.append(int(index))
    kept = states[keep]
    # Roundoff tail removal is explicit above. Do not sort a remaining physical rebound away.
    if np.any(np.diff(kept[:, 2]) > 0):
        raise ValueError(f"Selected extinction branch still rebounds at Z={mixture}; inspect the actual path")
    audit.update(selected_frames=len(keep), selected_times_s=times[keep].tolist(),
                 cold_C_zero_strictly_covered=bool(final[2] == 0.0))
    return kept, audit
