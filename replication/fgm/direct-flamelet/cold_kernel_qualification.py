"""Qualify a separate cold arithmetic build against the retained failure and actual derivatives."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from common import sha256, write_json
from cold_rate_probe import GRI_SHA256
from spitfire_patch import UPSTREAM


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-probe", type=Path, required=True)
    parser.add_argument("--previous-qualification", type=Path)
    parser.add_argument("--mechanism", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--upstream-patch-receipt", type=Path, required=True)
    parser.add_argument("--upstream-cold-patch-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    baseline = json.loads(args.baseline_probe.read_text())
    failed = [row for row in baseline.get("results", []) if row["T_K"] == 85 and
              {"H", "CN", "HCN"}.issubset(row["isolated_griffon_nonfinite_species"]) and row["griffon_nonfinite_species"]]
    if (baseline.get("schema") != "cold-chemistry-probe/v1" or baseline.get("mechanism_sha256") != GRI_SHA256 or
            len(baseline.get("results", [])) != 8 or not failed or
            baseline.get("spitfire_runtime", {}).get("cold_source_patch") is not None or sha256(args.mechanism) != GRI_SHA256):
        raise ValueError("Retained original-runtime eight-state probe must reproduce the isolated229/full85K failure")
    result = {"schema": "cold-kernel-qualification/v1", "source_commit": args.source_commit,
        "baseline_probe_sha256": sha256(args.baseline_probe), "original_failure_reproduced": True,
        "mechanism_sha256": GRI_SHA256, "scientific_acceptance": False,
        "scope": "Software rate and derivative qualification only; cold thermochemistry/flame agreement remain unqualified",
        "criteria": {"warm_rate_regularized_error": 1e-8, "Jacobian_floor_relative_error": 1e-3,
                     "Jacobian_relative_floor_fraction_of_column_peak": 1e-6,
                     "finite_difference_step_agreement_peak_relative": 1e-3}, "states": []}
    previous = None
    if args.previous_qualification is not None:
        previous = json.loads(args.previous_qualification.read_text())
        if previous.get("qualification_passed") is not False or previous.get("mechanism_sha256") != GRI_SHA256:
            raise ValueError("Previous qualification must be the retained failed check for this mechanism")
        result["previous_failed_qualification_sha256"] = sha256(args.previous_qualification)
    result["HCN_difference_policy"] = "first-adjacent-FD-stable-plateau/v1; selection independent of analytic Jacobians"
    if args.plan:
        print(json.dumps(result, indent=2))
        return 0
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new directory")
    args.out.mkdir(parents=True)
    write_json(args.out / "receipt.json", result)
    try:
        import cantera as ct
        import numpy as np
        from spitfire import ChemicalMechanismSpec
        from spitfire_identity import runtime_identity
        from sensitivity_steps import select_hcn_plateau
        result["runtime"] = runtime_identity({"upstream_revision": UPSTREAM}, args.upstream_patch_receipt, args.upstream_cold_patch_receipt)
        if result["runtime"]["extension_sha256"] == baseline["spitfire_runtime"]["extension_sha256"]:
            raise ValueError("New candidate extension is identical to original failing runtime")
        if previous is not None and result["runtime"]["extension_sha256"] != previous["runtime"]["extension_sha256"]:
            raise ValueError("Evaluator repair must use the exact previously evaluated compiled extension")
        command = [sys.executable, str(Path(__file__).with_name("cold_rate_probe.py")),
            "--mechanism", str(args.mechanism), "--mechanism-sha256", GRI_SHA256,
            "--source-commit", args.source_commit, "--upstream-patch-receipt", str(args.upstream_patch_receipt),
            "--upstream-cold-patch-receipt", str(args.upstream_cold_patch_receipt),
            "--out", str(args.out / "candidate-rate-probe.json"), "--require-finite"]
        with (args.out / "candidate-rate-probe.log").open("w") as log:
            child = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        result["candidate_rate_probe_exit"] = child.returncode
        if child.returncode != 0:
            raise ValueError("New-runtime eight-state probe failed; inspect retained result/log")
        gas = ct.Solution(str(args.mechanism))
        mechanism = ChemicalMechanismSpec(cantera_solution=gas)
        count = gas.n_species
        reference = gas.species_index("O2")
        passed = True

        def production(temperature, density, composition):
            values = np.empty(count)
            mechanism.griffon.production_rates(temperature, density, composition, values)
            return values

        for temperature in (85.0, 300.0, 1200.0):
            gas.TPY = temperature, 5610000.0, {"O2": .99, "CH4": .01, "H": 1e-10, "CN": 1e-10, "HCN": 1e-10}
            y, density = gas.Y.copy(), gas.density
            expected = gas.net_production_rates * gas.molecular_weights
            actual = production(temperature, density, y)
            finite = bool(np.all(np.isfinite(actual)))
            warm_error = float(np.max(abs(actual - expected) / (1 + abs(expected)))) if finite else None
            state = {"T_K": temperature, "P_Pa": gas.P, "rho_kg_m3": density,
                     "composition_note": "Declared O2-rich evaluator state with H/CN/HCN1e-10 mass traces; not a flame simulation",
                     "cantera_rate_error_regularized": warm_error, "cold_Cantera_coefficient_agreement_required": False,
                     "rate_finite": finite, "Jacobian_modes": {}, "directions": []}
            jacobians = {}
            for mode, label in ((0, "dense"), (1, "no-TBAF"), (2, "sparse")):
                flat = np.zeros((count + 1) ** 2)
                # This API is (rho,T,Y,option,out), unlike production_rates(T,rho,Y,out).
                mechanism.griffon.prod_rates_primitive_sensitivities(density, temperature, y, mode, flat)
                matrix = flat.reshape((count + 1, count + 1), order="F")[:-1]
                jacobians[label] = matrix
                state["Jacobian_modes"][label] = {"all_finite": bool(np.all(np.isfinite(matrix))),
                    "scope": "Finiteness only; omitted TBAF derivatives remain approximate" if mode == 1 else "Compared with actual production-kernel finite differences"}
                passed = passed and state["Jacobian_modes"][label]["all_finite"]
            for name in ("density", "temperature", "H", "CN", "HCN"):
                if name == "density":
                    step, column = density * 1e-6, 0
                elif name == "temperature":
                    step, column = temperature * 1e-6, 1
                else:
                    species = gas.species_index(name)
                    step, column = y[species] * .01, species + 2
                estimates, sweep = [], None
                if name == "HCN":
                    fine, sweep = select_hcn_plateau(production, temperature, density, y, species, reference, gas.species_names)
                    if fine is None:
                        state["directions"].append({"direction": name, "finite_difference_resolved": False,
                            "all_finite": all(row["finite"] for row in sweep["candidates"]), "sweep": sweep})
                        passed = False
                        continue
                    selected = sweep["candidates"][sweep["selected_index"]]
                    step = selected["step"]
                    coarse = np.array([row["coarse_derivative"] for row in selected["species_residuals"]])
                    estimates = [coarse, fine]
                else:
                    for delta in (step, step / 2):
                        yp, ym = y.copy(), y.copy()
                        tp = tm = temperature
                        rp = rm = density
                        if name == "density":
                            rp, rm = density + delta, density - delta
                        elif name == "temperature":
                            tp, tm = temperature + delta, temperature - delta
                        else:
                            yp[species] += delta
                            yp[reference] -= delta
                            ym[species] -= delta
                            ym[reference] += delta
                        estimates.append((production(tp, rp, yp) - production(tm, rm, ym)) / (2 * delta))
                coarse, fine = estimates
                finite_direction = bool(np.all(np.isfinite(coarse)) and np.all(np.isfinite(fine)))
                comparison = {"direction": name, "step": step, "all_finite": finite_direction}
                if sweep is not None:
                    comparison.update(finite_difference_resolved=True, sweep=sweep)
                if finite_direction:
                    peak = max(float(np.max(abs(fine))), 1e-6)
                    denominator = np.maximum(abs(fine), peak * 1e-6)
                    agreement = float(np.max(abs(fine - coarse)) / peak)
                    comparison.update(finite_difference_peak=peak, step_agreement_peak_relative=agreement)
                    passed = passed and agreement <= 1e-3
                    for label in ("dense", "sparse"):
                        analytic = jacobians[label][:, column].copy()
                        if name not in ("density", "temperature"):
                            analytic -= jacobians[label][:, reference + 2]
                        if np.all(np.isfinite(analytic)):
                            error = float(np.max(abs(analytic - fine) / denominator))
                            comparison[label + "_max_floor_relative_error"] = error
                            comparison[label + "_max_peak_relative_error"] = float(np.max(abs(analytic - fine)) / peak)
                            if name == "HCN":
                                comparison[label + "_species_residuals"] = [{"species": species_name,
                                    "analytic_derivative": float(analytic[k]), "FD_derivative": float(fine[k]),
                                    "floor_relative_error": float(abs(analytic[k] - fine[k]) / denominator[k])}
                                    for k, species_name in enumerate(gas.species_names)]
                            passed = passed and error <= 1e-3
                        else:
                            comparison[label + "_max_floor_relative_error"] = None
                            passed = False
                else:
                    passed = False
                state["directions"].append(comparison)
            passed = passed and finite and (temperature < 300 or warm_error <= 1e-8)
            result["states"].append(state)
            write_json(args.out / "receipt.json", result)
        result.update(qualification_passed=bool(passed), status="measured_software_qualification",
            artifacts={name: sha256(args.out / name) for name in ("candidate-rate-probe.json", "candidate-rate-probe.log")})
        write_json(args.out / "receipt.json", result)
        print(json.dumps(result, indent=2))
        return 0 if passed else 5
    except Exception as error:
        result.update(status="qualification_failed", qualification_passed=False, error_type=type(error).__name__, error=str(error))
        write_json(args.out / "receipt.json", result)
        print(json.dumps(result, indent=2))
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
