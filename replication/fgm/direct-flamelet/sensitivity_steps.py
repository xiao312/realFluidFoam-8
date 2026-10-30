"""Choose a resolved HCN difference plateau without access to the analytic Jacobian."""
import numpy as np

FRACTIONS = (.01, .05, .1, .25, .5)


def select_hcn_plateau(production, temperature, density, y, species, reference, names):
    candidates, estimates = [], []
    tolerance = 1e-3
    for fraction in FRACTIONS:
        step = float(y[species] * fraction)
        if step <= 0 or y[species] - step < 0 or y[reference] - step < 0:
            raise ValueError("HCN plateau sweep requires positive HCN and compensation-species mass fractions")
        differences, raw_signals = [], []
        for delta in (step, step / 2):
            yp, ym = y.copy(), y.copy()
            yp[species] += delta
            yp[reference] -= delta
            ym[species] -= delta
            ym[reference] += delta
            plus = production(temperature, density, yp)
            minus = production(temperature, density, ym)
            raw_signals.append(plus - minus)
            differences.append((plus - minus) / (2 * delta))
        coarse, fine = differences
        finite = bool(np.all(np.isfinite(coarse)) and np.all(np.isfinite(fine)))
        record = {"fraction_of_HCN": fraction, "step": step, "finite": finite}
        if finite:
            peak = max(float(np.max(abs(fine))), 1e-6)
            denominator = np.maximum(abs(fine), peak * 1e-6)
            residual = abs(coarse - fine) / denominator
            error = float(np.max(residual))
            record.update(self_max_floor_relative_error=error,
                self_max_peak_relative_error=float(np.max(abs(coarse - fine)) / peak),
                derivative_peak=peak, self_stable=error <= tolerance,
                fine_rate_difference_max=float(np.max(abs(raw_signals[1]))),
                worst_species=names[int(np.argmax(residual))],
                species_residuals=[{"species": name, "coarse_derivative": float(coarse[k]),
                    "fine_derivative": float(fine[k]), "self_floor_relative_error": float(residual[k]),
                    "fine_rate_difference": float(raw_signals[1][k])} for k, name in enumerate(names)])
        else:
            record.update(self_stable=False, nonfinite_species=[names[k] for k in np.flatnonzero(~np.isfinite(coarse) | ~np.isfinite(fine))])
        candidates.append(record)
        estimates.append(fine)
    selected = None
    comparisons = []
    for index in range(1, len(candidates)):
        previous, current = candidates[index - 1], candidates[index]
        if not previous["finite"] or not current["finite"]:
            comparisons.append({"indices": [index - 1, index], "finite": False, "stable": False})
            continue
        left, right = estimates[index - 1], estimates[index]
        peak = max(float(np.max(abs(left))), float(np.max(abs(right))), 1e-6)
        denominator = np.maximum(np.maximum(abs(left), abs(right)), peak * 1e-6)
        error = float(np.max(abs(left - right) / denominator))
        stable = previous["self_stable"] and current["self_stable"] and error <= tolerance
        comparisons.append({"indices": [index - 1, index], "finite": True,
                            "cross_step_max_floor_relative_error": error, "stable": bool(stable)})
        if selected is None and stable:
            selected = index
    report = {"policy": "first-adjacent-FD-stable-plateau/v1", "selection_uses_analytic_Jacobian": False,
        "tolerance": tolerance, "relative_floor_fraction_of_peak": 1e-6,
        "selected_index": selected, "selected_step": candidates[selected]["step"] if selected is not None else None,
        "candidates": candidates, "adjacent_comparisons": comparisons,
        "status": "resolved" if selected is not None else "finite_difference_unresolved"}
    return (estimates[selected] if selected is not None else None), report
