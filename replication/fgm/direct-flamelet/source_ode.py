"""Diagnose fixed-Z/fixed-rho table chemistry without changing its coefficients."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
from common import sha256, write_json
from table_io import lookup


def source_slice(model, z):
    upper = min(len(model["z"]) - 1, max(1, int(np.searchsorted(model["z"], z))))
    lower = upper - 1
    weight = (z - model["z"][lower]) / (model["z"][upper] - model["z"][lower])
    values = (1 - weight) * model["values"][lower] + weight * model["values"][upper]
    cmin = float(np.interp(z, model["z"], model["c_min"]))
    cmax = float(np.interp(z, model["z"], model["c_max"]))
    return cmin + model["eta"] * (cmax - cmin), values


def exact_advance(axis, rate, initial, duration):
    """Solve linear segments exactly; report a boundary event instead of clipping."""
    state, elapsed, transitions = float(initial), 0.0, 0
    if state < axis[0] or state > axis[-1]:
        raise ValueError("Initial progress lies outside the strict table domain")
    while elapsed < duration:
        velocity = float(np.interp(state, axis, rate))
        if velocity == 0:
            return {"C": state, "elapsed_s": duration, "event": "exact_zero_source", "segments": transitions}
        positive = velocity > 0
        if (positive and state == axis[-1]) or (not positive and state == axis[0]):
            return {"C": state, "elapsed_s": elapsed, "event": "outward_coverage_boundary", "segments": transitions}
        index = int(np.searchsorted(axis, state, side="right" if positive else "left")) - 1
        index = min(len(axis) - 2, max(0, index))
        slope = (rate[index + 1] - rate[index]) / (axis[index + 1] - axis[index])
        edge = axis[index + 1] if positive else axis[index]
        edge_velocity = rate[index + 1] if positive else rate[index]
        distance = edge - state
        ratio = slope * distance / velocity
        if slope == 0:
            crossing = distance / velocity
        elif edge_velocity * velocity <= 0:
            crossing = math.inf  # A zero source blocks this segment boundary.
        else:
            # Use the stored endpoint source when it is tiny: forming 1+ratio
            # would cancel its meaningful equilibrium residual against unity.
            crossing = (math.log1p(ratio) if abs(ratio) < .5 else math.log(edge_velocity / velocity)) / slope
        remaining = duration - elapsed
        if crossing > remaining:
            delta = velocity * remaining if slope == 0 else velocity * math.expm1(slope * remaining) / slope
            candidate = state + delta
            if candidate < axis[0] or candidate > axis[-1]:
                raise ArithmeticError("Analytic update left table coverage before its computed event")
            return {"C": float(candidate), "elapsed_s": duration, "event": "requested_time", "segments": transitions}
        if crossing < 0 or not math.isfinite(crossing):
            raise ArithmeticError("Invalid analytic segment crossing")
        state = float(edge)  # Exact knot event, not a clipped time-step overshoot.
        elapsed += crossing
        transitions += 1
        if transitions > 2 * len(axis):
            raise ArithmeticError("Unexpected source-direction cycle")
    return {"C": state, "elapsed_s": elapsed, "event": "requested_time", "segments": transitions}


def adaptive(axis, rate, initial, duration, tolerance):
    from scipy.integrate import solve_ivp
    probes = {"outside_trial_stages": 0, "max_trial_excursion": 0.0}
    def rhs(time, state):
        c = float(state[0])
        if c < axis[0] or c > axis[-1]:
            # Explicitly disclosed linear continuation is only for rejected RK stages
            # and boundary-event location; accepted out-of-coverage states are refused.
            index = 0 if c < axis[0] else len(axis) - 2
            probes["outside_trial_stages"] += 1
            probes["max_trial_excursion"] = max(probes["max_trial_excursion"], axis[0] - c, c - axis[-1])
            value = rate[index] + (c - axis[index]) * (rate[index + 1] - rate[index]) / (axis[index + 1] - axis[index])
        else:
            value = np.interp(c, axis, rate)
        return [value]
    def lower(time, state):
        return state[0] - axis[0]
    def upper(time, state):
        return axis[-1] - state[0]
    lower.terminal = upper.terminal = True
    lower.direction = upper.direction = -1
    solution = solve_ivp(rhs, (0, duration), [initial], method="DOP853", rtol=tolerance,
                         atol=tolerance * .01, max_step=duration / 200, events=(lower, upper))
    excursion = max(0.0, float(axis[0] - solution.y[0].min()), float(solution.y[0].max() - axis[-1]))
    return {"success": solution.success, "message": solution.message, "C": float(solution.y[0, -1]),
            "elapsed_s": float(solution.t[-1]), "accepted_points": len(solution.t), "function_evaluations": solution.nfev,
            "accepted_coverage_excursion": excursion, "rtol": tolerance, "atol": tolerance * .01, **probes}


def chemical_state(gas, model, z, c, pressure):
    values = lookup(model, z, c)
    gas.TPY = values[0], pressure, values[5:]
    progress = [gas.species_index(name) for name in ("CO2", "CO")]
    source = gas.net_production_rates * gas.molecular_weights
    return {"C": float(c), "T_K": float(values[0]), "rho_ideal_kg_m3": gas.density,
            "stored_Sc_kg_m3_s": float(values[3]), "stored_Qformation_W_m3": float(values[4]),
            "reevaluated_Sc_kg_m3_s": float(np.sum(source[progress])),
            "reevaluated_max_species_source_kg_m3_s": float(np.max(abs(source))),
            "interpretation": "Chemical reevaluation of interpolated table T/Y; not a replacement source"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-dir", required=True, type=Path)
    parser.add_argument("--mechanism", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    receipt = json.loads((args.table_dir / "receipt.json").read_text())
    if (sha256(args.table_dir / "table.json") != receipt["artifacts"]["table.json"] or
            sha256(args.mechanism) != receipt["mechanism_sha256"]):
        raise ValueError("Table or mechanism identity differs")
    identity = {"schema": "fixed-state-table-source-ode/v1", "script_sha256": sha256(__file__),
                "table_json_sha256": receipt["artifacts"]["table.json"], "physical_tbl_sha256": receipt["artifacts"]["physical.tbl"],
                "table_receipt_sha256": sha256(args.table_dir / "receipt.json"), "mechanism_sha256": sha256(args.mechanism),
                "equation": "dC/dt = stored Sc(Z,C) / fixed rho", "coefficients_changed": False,
                "source_clipping": False, "scientific_acceptance": False}
    if args.plan:
        print(json.dumps(identity, indent=2))
        return 0
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new directory")
    import cantera as ct
    import scipy
    if ct.__version__ != "3.2.0" or scipy.__version__ != "1.15.3":
        raise ValueError("Cantera3.2.0 and SciPy1.15.3 are required for this comparison")
    gas = ct.Solution(str(args.mechanism))
    model = json.loads((args.table_dir / "table.json").read_text())
    for name in ("z", "eta", "c_min", "c_max", "values"):
        model[name] = np.asarray(model[name])
    args.out.mkdir(parents=True)
    identity.update(cantera=ct.__version__, numpy=np.__version__, scipy=scipy.__version__, slices=[])
    write_json(args.out / "receipt.json", identity)
    for z in (.1, .2, .4, .6):
        axis, values = source_slice(model, z)
        initial = axis[0] + .8 * (axis[-1] - axis[0])
        representative = chemical_state(gas, model, z, initial, receipt["case"]["pressure_pa"])
        rho = representative["rho_ideal_kg_m3"]
        rate = values[:, 3] / rho
        roots = []
        for i in range(len(axis) - 1):
            if rate[i] * rate[i + 1] < 0:
                fraction = -rate[i] / (rate[i + 1] - rate[i])
                c = float(axis[i] + fraction * (axis[i + 1] - axis[i]))
                root = chemical_state(gas, model, z, c, receipt["case"]["pressure_pa"])
                root.update(eta=(c - axis[0]) / (axis[-1] - axis[0]), stable=bool(rate[i] > 0),
                            bracket_nodes=[i, i + 1], relaxation_timescale_s=abs((axis[i + 1] - axis[i]) / (rate[i + 1] - rate[i])))
                roots.append(root)
        rows = []
        for eta in (.1, .8, .98, 1.0):
            start = float(axis[0] + eta * (axis[-1] - axis[0]))
            exact = exact_advance(axis, rate, start, 1e-4)
            row = {"initial_eta": eta, "fixed_density_kg_m3": rho, "horizon_s": 1e-4, "exact": exact}
            if exact["elapsed_s"] > 0:
                target = 0.9 * exact["elapsed_s"] if exact["event"] == "outward_coverage_boundary" else 1e-4
                reference = exact_advance(axis, rate, start, target)
                row.update(comparison_time_s=target, exact_comparison=reference,
                           adaptive=[adaptive(axis, rate, start, target, tolerance) for tolerance in (1e-10, 1e-12)], refinements=[])
                for subdivisions in (1, 10, 100, 1000):
                    state = start
                    for _ in range(subdivisions):
                        step = exact_advance(axis, rate, state, target / subdivisions)
                        if step["event"] == "outward_coverage_boundary":
                            raise ArithmeticError("Refinement unexpectedly crossed coverage")
                        state = step["C"]
                    row["refinements"].append({"macro_steps": subdivisions, "C": state,
                                               "difference_from_one_advance": state - reference["C"]})
                for result in row["adaptive"]:
                    result["difference_from_exact"] = result["C"] - reference["C"]
            rows.append(row)
        summary = {"Z": z, "fixed_density_reference": representative, "Cmin": float(axis[0]), "Cmax": float(axis[-1]),
            "source_min_max_kg_m3_s": [float(values[:, 3].min()), float(values[:, 3].max())],
            "endpoint_source_relative_to_peak": float(values[-1, 3] / abs(values[:, 3]).max()),
            "Cmax_chemistry": chemical_state(gas, model, z, float(axis[-1]), receipt["case"]["pressure_pa"]),
            "roots": roots, "integrations": rows}
        identity["slices"].append(summary)
        path = args.out / f"source-Z{z:.1f}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["C", "eta", "Sc_kg_m3_s", "dCdt_fixed_rho_per_s", "Tdiag_K", "Qformation_W_m3"])
            writer.writerows(zip(axis, model["eta"], values[:, 3], rate, values[:, 0], values[:, 4]))
        write_json(args.out / "receipt.json", identity)
        print(json.dumps({"Z": z, "roots": [{"eta": r["eta"], "stable": r["stable"]} for r in roots],
                          "eta08_final": rows[1]["exact"]}), flush=True)
    identity["artifacts"] = {p.name: sha256(p) for p in args.out.glob("*.csv")}
    write_json(args.out / "receipt.json", identity)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
