"""Eight fixed-state evaluator measurements; no flame solve or chemistry modification."""
import argparse
import json
import math
from pathlib import Path
import re
from common import sha256, write_json
from spitfire_patch import UPSTREAM

GRI_SHA256 = "06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345"


def finite_or_label(value):
    value = float(value)
    return value if math.isfinite(value) else ("NaN" if math.isnan(value) else ("+Inf" if value > 0 else "-Inf"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanism", required=True, type=Path)
    parser.add_argument("--mechanism-sha256", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--upstream-patch-receipt", type=Path)
    parser.add_argument("--upstream-cold-patch-receipt", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--require-finite", action="store_true")
    args = parser.parse_args()
    if args.mechanism_sha256 != GRI_SHA256 or sha256(args.mechanism) != GRI_SHA256:
        raise ValueError("This bounded probe requires the exact retained GRI30 mechanism")
    if not re.fullmatch("[0-9a-f]{40}", args.source_commit):
        raise ValueError("Full source commit required")
    points = [{"T_K": temperature, "P_Pa": 5610000.0, "X": {"O2": 1 - methane, "CH4": methane}}
              for temperature in (85.0, 100.0, 150.0, 300.0) for methane in (0.0, 1e-8)]
    result = {"schema": "cold-chemistry-probe/v1", "source_commit": args.source_commit,
              "mechanism_sha256": GRI_SHA256, "points": points,
              "purpose": "Actual compiled evaluator and numerical arithmetic diagnosis; not flame validation",
              "production_mechanism_changed": False, "scientific_acceptance": False, "results": []}
    if args.plan:
        print(json.dumps(result, indent=2))
        return 0
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new JSON path")
    import cantera as ct
    import numpy as np
    from spitfire import ChemicalMechanismSpec
    from spitfire_identity import runtime_identity
    if ct.__version__ != "3.2.0":
        raise ValueError("Cantera3.2.0 required")
    result.update(cantera=ct.__version__, script_sha256=sha256(__file__),
                  spitfire_runtime=runtime_identity({"upstream_revision": UPSTREAM}, args.upstream_patch_receipt, args.upstream_cold_patch_receipt))
    gas = ct.Solution(str(args.mechanism))
    full = ChemicalMechanismSpec(cantera_solution=gas)
    reaction_index = 229
    reaction = gas.reaction(reaction_index)
    if reaction.equation != "HCN + M <=> CN + H + M" or reaction.reaction_type != "three-body-Arrhenius":
        raise ValueError("Pinned reaction229 identity differs")
    isolated_gas = ct.Solution(thermo="ideal-gas", kinetics="gas", species=gas.species(), reactions=[reaction])
    isolated = ChemicalMechanismSpec(cantera_solution=isolated_gas)
    stoich = gas.product_stoich_coeffs[:, reaction_index] - gas.reactant_stoich_coeffs[:, reaction_index]
    equations = gas.reaction_equations()
    result["isolation"] = {"reaction_index_zero_based": reaction_index, "equation": reaction.equation,
        "species_count": gas.n_species, "reaction_count": 1,
        "purpose": "Same species thermodynamics and single original reaction; isolate evaluator overflow, never used for physical runs"}
    write_json(args.out, result)
    for point in points:
        gas.TPX = point["T_K"], point["P_Pa"], point["X"]
        isolated_gas.TPY = gas.T, gas.P, gas.Y
        actual = np.zeros(gas.n_species)
        isolated_actual = np.zeros(gas.n_species)
        full.griffon.production_rates(gas.T, gas.density, gas.Y, actual)
        isolated.griffon.production_rates(gas.T, gas.density, gas.Y, isolated_actual)
        expected = gas.net_production_rates * gas.molecular_weights
        isolated_expected = isolated_gas.net_production_rates * isolated_gas.molecular_weights
        finite = np.isfinite(actual) & np.isfinite(expected)
        rate = reaction.rate
        log_kf = math.log(rate.pre_exponential_factor) + rate.temperature_exponent * math.log(gas.T) - rate.activation_energy / (ct.gas_constant * gas.T)
        log_inverse_kc = float(stoich @ gas.standard_gibbs_RT - stoich.sum() * math.log(gas.reference_pressure / (ct.gas_constant * gas.T)))
        third_body = float(gas.third_body_concentrations[reaction_index])
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            kf_naive = rate.pre_exponential_factor * np.exp(rate.temperature_exponent * np.log(gas.T) - rate.activation_energy / (ct.gas_constant * gas.T))
            inverse_kc_naive = np.exp(log_inverse_kc)
            kr_naive = kf_naive * third_body * inverse_kc_naive
            kr_log = np.exp(log_kf + math.log(third_body) + log_inverse_kc)
        row = {**point,
            "species_rates_kg_m3_s": [{"species": name, "cantera": finite_or_label(expected[k]),
                "griffon": finite_or_label(actual[k]), "isolated_cantera": finite_or_label(isolated_expected[k]),
                "isolated_griffon": finite_or_label(isolated_actual[k])} for k, name in enumerate(gas.species_names)],
            "griffon_nonfinite_species": [gas.species_names[k] for k in np.flatnonzero(~np.isfinite(actual))],
            "isolated_griffon_nonfinite_species": [gas.species_names[k] for k in np.flatnonzero(~np.isfinite(isolated_actual))],
            "cantera_nonfinite_species": [gas.species_names[k] for k in np.flatnonzero(~np.isfinite(expected))],
            "finite_species_max_absolute_difference": float(np.max(abs(actual[finite] - expected[finite]))) if np.any(finite) else None,
            "cantera_nonfinite_reactions": [{"index": int(k), "equation": equations[k], "value": finite_or_label(gas.net_rates_of_progress[k])}
                                            for k in np.flatnonzero(~np.isfinite(gas.net_rates_of_progress))],
            "reaction229": {"A": rate.pre_exponential_factor, "b": rate.temperature_exponent,
                "Ea_J_kmol": rate.activation_energy, "log_kf": log_kf, "log_inverse_Kc": log_inverse_kc,
                "third_body_kmol_m3": third_body, "log_kr_with_third_body": log_kf + math.log(third_body) + log_inverse_kc,
                "naive_kf": finite_or_label(kf_naive), "naive_inverse_Kc": finite_or_label(inverse_kc_naive),
                "naive_kr_with_third_body": finite_or_label(kr_naive),
                "combined_log_kr_with_third_body": finite_or_label(kr_log),
                "cantera_forward_rate_constant": finite_or_label(gas.forward_rate_constants[reaction_index]),
                "cantera_reverse_rate_constant": finite_or_label(gas.reverse_rate_constants[reaction_index]),
                "cantera_net_rate_of_progress_kmol_m3_s": finite_or_label(gas.net_rates_of_progress[reaction_index]),
                "scope": "Stable combined log is arithmetic evidence, not an implemented kinetics change; Griffon per-reaction ROP API is not exposed"}}
        result["results"].append(row)
        write_json(args.out, result)
        print(json.dumps({key: value for key, value in row.items() if key != "species_rates_kg_m3_s"}), flush=True)
    result["all_Griffon_outputs_finite"] = all(not row["griffon_nonfinite_species"] and not row["isolated_griffon_nonfinite_species"] for row in result["results"])
    result["status"] = "measurements_complete_not_scientifically_accepted"
    write_json(args.out, result)
    return 5 if args.require_finite and not result["all_Griffon_outputs_finite"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
