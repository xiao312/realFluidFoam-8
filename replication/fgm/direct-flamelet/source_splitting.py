"""Actual-table 1D scalar advection/source splitting diagnostic, not an OpenFOAM flame."""
import argparse
import csv
import json
from pathlib import Path
import time
import numpy as np
from common import sha256, write_json
from source_ode import source_slice, exact_advance, chemical_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-dir", required=True, type=Path)
    parser.add_argument("--mechanism", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    source_receipt = json.loads((args.table_dir / "receipt.json").read_text())
    if (sha256(args.table_dir / "table.json") != source_receipt["artifacts"]["table.json"] or
            sha256(args.mechanism) != source_receipt["mechanism_sha256"]):
        raise ValueError("Table or mechanism identity differs")
    report = {"schema": "actual-table-scalar-splitting/v1", "script_sha256": sha256(__file__),
        "source_integrator_sha256": sha256(Path(__file__).with_name("source_ode.py")),
        "table_json_sha256": source_receipt["artifacts"]["table.json"],
        "mechanism_sha256": source_receipt["mechanism_sha256"], "mixture_fraction": .2,
        "cells": 64, "length_m": .001, "velocity_m_s": 20.0, "duration_s": 2e-6,
        "initial_hot_cells": [20, 28], "initial_hot_eta": .8, "inlet_C": 0.0,
        "spatial_operator": "first-order upwind finite volume, fixed Z and rho",
        "splitting": "source half step / exact semidiscrete advection / source half step",
        "scope": "Scientific scalar prototype only; no pressure, density evolution, species or enthalpy transport",
        "source_coefficients_changed": False, "source_clipping": False, "scientific_acceptance": False}
    if args.plan:
        print(json.dumps(report, indent=2))
        return 0
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new directory")
    import cantera as ct
    import scipy
    from scipy.integrate import solve_ivp
    from scipy.sparse import diags
    from scipy.sparse.linalg import expm_multiply
    if ct.__version__ != "3.2.0" or scipy.__version__ != "1.15.3":
        raise ValueError("Pinned Cantera3.2.0 and SciPy1.15.3 required")
    gas = ct.Solution(str(args.mechanism))
    model = json.loads((args.table_dir / "table.json").read_text())
    for key in ("z", "eta", "c_min", "c_max", "values"):
        model[key] = np.asarray(model[key])
    axis, values = source_slice(model, .2)
    hot = float(axis[0] + .8 * (axis[-1] - axis[0]))
    rho = chemical_state(gas, model, .2, hot, source_receipt["case"]["pressure_pa"])["rho_ideal_kg_m3"]
    rates = values[:, 3] / rho
    slopes = np.diff(rates) / np.diff(axis)
    cells = report["cells"]
    initial = np.zeros(cells)
    initial[20:28] = hot
    dx = report["length_m"] / cells
    velocity = report["velocity_m_s"]
    advect = diags([np.full(cells - 1, velocity / dx), np.full(cells, -velocity / dx)], [-1, 0], format="csc")
    def chemical(state):
        intervals = np.maximum(0, np.minimum(len(slopes) - 1, np.searchsorted(axis, state, side="right") - 1))
        return rates[intervals] + slopes[intervals] * (state - axis[intervals])
    def jacobian(t, state):
        intervals = np.maximum(0, np.minimum(len(slopes) - 1, np.searchsorted(axis, state, side="right") - 1))
        return advect + diags(slopes[intervals], 0, format="csc")
    args.out.mkdir(parents=True)
    report.update(fixed_density_kg_m3=rho, numpy=np.__version__, scipy=scipy.__version__, references=[], steps=[])
    write_json(args.out / "receipt.json", report)
    references = []
    for tolerance in (1e-8, 1e-10):
        before = time.monotonic()
        reference = solve_ivp(lambda t, state: advect @ state + chemical(state), (0, report["duration_s"]), initial,
            method="Radau", jac=jacobian, rtol=tolerance, atol=tolerance * .01, max_step=report["duration_s"] / 100)
        if not reference.success:
            raise ValueError("Adaptive coupled baseline failed: " + reference.message)
        references.append(reference.y[:, -1])
        report["references"].append({"method": "Radau", "rtol": tolerance, "atol": tolerance * .01,
            "elapsed_wall_s": time.monotonic() - before, "accepted_times": len(reference.t),
            "rhs_evaluations": reference.nfev,
            "accepted_min_C": float(reference.y.min()), "accepted_max_C": float(reference.y.max()),
            "trial_evaluation_policy": "Piecewise terminal segments extended for implicit trial states only; accepted-state bounds reported without clipping"})
        write_json(args.out / "receipt.json", report)
    report["baseline_refinement_max_C_difference"] = float(abs(references[-1] - references[-2]).max())
    profiles = [initial, references[-1]]
    headers = ["initial_C", "adaptive_Radau_C"]
    for dt in (1e-7, 5e-8, 2.5e-8, 1.25e-8):
        count = int(round(report["duration_s"] / dt))
        state = initial.copy()
        before = time.monotonic()
        crossings = 0
        min_c, max_c = float(state.min()), float(state.max())
        for _ in range(count):
            for stage in range(2):
                for cell in range(cells):
                    result = exact_advance(axis, rates, float(state[cell]), dt / 2)
                    if result["event"] == "outward_coverage_boundary":
                        raise ValueError("Split source reached an outward coverage boundary; no clipping permitted")
                    state[cell] = result["C"]
                    crossings += result["segments"]
                if stage == 0:
                    state = expm_multiply(dt * advect, state, traceA=dt * float(advect.diagonal().sum()))
                min_c, max_c = min(min_c, float(state.min())), max(max_c, float(state.max()))
        error = state - references[-1]
        report["steps"].append({"dt_s": dt, "steps": count, "advection_CFL": velocity * dt / dx,
            "elapsed_wall_s": time.monotonic() - before, "source_segments_crossed": crossings,
            "max_C_error": float(abs(error).max()), "rms_C_error": float(np.sqrt(np.mean(error ** 2))),
            "max_error_over_progress_span": float(abs(error).max() / (axis[-1] - axis[0])),
            "minimum_C_all_stages": min_c, "maximum_C_all_stages": max_c,
            "strict_bounds_preserved": bool(min_c >= axis[0] and max_c <= axis[-1])})
        profiles.append(state.copy())
        headers.append(f"Strang_dt_{dt:.3g}_C")
        write_json(args.out / "receipt.json", report)
        print(json.dumps(report["steps"][-1]), flush=True)
    with (args.out / "profiles.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cell_center_m", *headers])
        writer.writerows(zip((np.arange(cells) + .5) * dx, *profiles))
    report["artifacts"] = {"profiles.csv": sha256(args.out / "profiles.csv")}
    write_json(args.out / "receipt.json", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
