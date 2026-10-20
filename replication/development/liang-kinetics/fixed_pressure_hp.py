"""Qualify an author-rate-preserving HP input restricted to exactly 100 atm.

This is an exact-input preparer, not a general PLOG converter.
No pressure interpolation is approximated: 100 atm must be a supplied node or
outside the tabulated range, where Cantera uses the nearest endpoint.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import warnings

import cantera as ct
import numpy as np
from ruamel.yaml import YAML

SOURCE_SHA = "63a07e9a8c9e2093232cad8acb164844459f0f9b97018b9db2e4e2479ea0a4a0"
TARGET_SHA = "cc34fbe54bfe71c79edabc6763934bdfbe4d1046ae5e33f67ca1efae02aa9afb"
LOWER_T, UPPER_T, PRESSURE_ATM = 298.0, 3500.0, 100.0
R_CAL = ct.gas_constant / 4184.0
CONVERT_ONE_BASED = {45, 46, 48, 49, 51, 52, 234}


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def rate(terms, temperature):
    return sum(row["A"] * temperature ** row["b"]
               * math.exp(-row["Ea"] / (R_CAL * temperature)) for row in terms)


def endpoint(reaction):
    rows = reaction["rate-constants"]
    pressures = sorted({float(row["P"].split()[0]) for row in rows})
    assert all(row["P"].split()[1] == "atm" for row in rows)
    selected = min(max(PRESSURE_ATM, pressures[0]), pressures[-1])
    if selected not in pressures:
        raise ValueError(f"100 atm is between PLOG nodes: {reaction['equation']}")
    return selected, [{key: row[key] for key in ("A", "b", "Ea")}
                      for row in rows if float(row["P"].split()[0]) == selected]


def positive_pair_certificate(terms):
    """For one positive and one negative term, minimize positive/abs(negative)."""
    positive = [row for row in terms if row["A"] > 0]
    negative = [row for row in terms if row["A"] < 0]
    if not negative:
        return {"kind": "all-positive-terms", "passed": True}
    if len(terms) != 2 or len(positive) != 1 or len(negative) != 1:
        raise ValueError("Analytic positivity certificate requires two signed terms")
    a, b = positive[0], negative[0]
    delta_b = a["b"] - b["b"]
    delta_e = a["Ea"] - b["Ea"]
    candidates = [LOWER_T, UPPER_T]
    if delta_b:
        stationary = -delta_e / (R_CAL * delta_b)
        if LOWER_T < stationary < UPPER_T:
            candidates.append(stationary)
    log_ratios = [(temperature, math.log(a["A"] / -b["A"])
                   + delta_b * math.log(temperature)
                   - delta_e / (R_CAL * temperature))
                  for temperature in candidates]
    temperature, log_ratio = min(log_ratios, key=lambda value: value[1])
    return {"kind": "analytic-minimum-positive-to-negative-ratio",
            "minimum_ratio": math.exp(log_ratio), "temperature_K": temperature,
            "passed": log_ratio > 0, "candidate_log_ratios": log_ratios}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if ct.__version__ != "3.2.0":
        raise ValueError("Use the pinned Cantera 3.2.0 environment")
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("Expected the recorded HP author YAML; consult the source audit")
    if args.output.exists():
        raise ValueError("Choose a new output directory")
    source, target = args.source, args.output / "hp-2017-fixed-100atm.yaml"
    yaml = YAML(typ="safe")
    original = yaml.load(source.read_text(encoding="utf-8"))
    assert original["units"] == {
        "length": "cm", "time": "s", "quantity": "mol",
        "activation-energy": "cal/mol"}
    variant = deepcopy(original)
    converted, reactions, mapping = [], [], {}
    endpoint_groups = defaultdict(list)
    for number, reaction in enumerate(original["reactions"], 1):
        indices = []
        if number not in CONVERT_ONE_BASED:
            indices.append(len(reactions))
            reactions.append(deepcopy(reaction))
        else:
            assert reaction.get("type") == "pressure-dependent-Arrhenius"
            pressure, terms = endpoint(reaction)
            endpoint_groups[reaction["equation"]].extend(terms)
            for term in terms:
                row = deepcopy(reaction)
                row.pop("type")
                row.pop("rate-constants")
                row["rate-constant"] = term
                row["id"] = f"author-reaction-{number}-term-{len(indices)+1}"
                if term["A"] < 0:
                    row["negative-A"] = True
                if len(terms) > 1:
                    row["duplicate"] = True
                row["note"] = (str(row.get("note", "")) +
                    f"\nExact 100-atm specialization of author reaction {number}; "
                    f"selected PLOG node {pressure:g} atm. All A,b,E unchanged.")
                indices.append(len(reactions))
                reactions.append(row)
            converted.append({
                "author_reaction_one_based": number,
                "equation": reaction["equation"],
                "selected_node_atm": pressure,
                "selected_terms": terms,
                "selected_terms_sha256": digest(terms),
                "all_original_plog_coefficients_sha256":
                    digest(reaction["rate-constants"]),
                "variant_reactions_zero_based": indices})
        mapping[number] = indices

    certificates = {equation: positive_pair_certificate(terms)
                    for equation, terms in endpoint_groups.items()}
    if not all(item["passed"] for item in certificates.values()):
        raise ValueError("A summed endpoint channel is not positive in 298–3500 K")
    variant["reactions"] = reactions
    variant["description"] = (
        "HP-Mech author release dated May 18, 2017; fixed 100-atm diagnostic.\n"
        "Seven PLOG reactions specialized to 100-atm endpoint Arrhenius terms, "
        "including explicit negative-A duplicate terms. Other PLOGs unchanged. "
        "Exact only at 100 atm.\n"
        "Temperature qualification: 298–3500 K. Must use load_fixed_100atm().\n"
        "Full author mechanism; Liang's unpublished methane subset is unidentified.")
    variant["generator"] = "fixed_pressure_hp.py"
    variant["qualification"] = {
        "pressure_Pa": PRESSURE_ATM * ct.one_atm,
        "temperature_range_K": [LOWER_T, UPPER_T],
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "exact_liang_subset": False}
    print(json.dumps({"source_sha256": SOURCE_SHA, "output": str(target.resolve()),
                      "converted_author_reactions": sorted(CONVERT_ONE_BASED),
                      "pressure_atm": PRESSURE_ATM,
                      "temperature_interval_K": [LOWER_T, UPPER_T],
                      "remote_writes": False}))
    if args.action == "plan":
        return
    args.output.mkdir(parents=True)
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        yaml.dump(variant, stream)
    if hashlib.sha256(target.read_bytes()).hexdigest() != TARGET_SHA:
        raise ValueError("Output differs from the qualified historical input; preserve it for review")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        gas = ct.Solution(str(target))
    assert gas.n_species == len(original["phases"][0]["species"])
    temperatures = np.unique(np.concatenate((
        np.linspace(LOWER_T, UPPER_T, 3203),
        np.array([298.15, 500, 1000, 1500, 2000, 2500, 3000, 3500]))))
    maximum_relative_error = 0.0
    equation_relative_errors = {}
    minimum_rates = {equation: (math.inf, None) for equation in endpoint_groups}
    for temperature in temperatures:
        # A nonzero frozen concentration for every species exercises all rates.
        gas.TPX = float(temperature), PRESSURE_ATM * ct.one_atm, np.ones(gas.n_species)
        actual = gas.forward_rate_constants
        for item in converted:
            indices = item["variant_reactions_zero_based"]
            order = sum(gas.reaction(indices[0]).reactants.values())
            expected = rate(item["selected_terms"], float(temperature)) * 1e-3 ** (order-1)
            observed = sum(float(actual[index]) for index in indices)
            error = abs(observed-expected) / max(abs(expected), 1e-300)
            maximum_relative_error = max(maximum_relative_error, error)
            if error > 1e-10:
                raise ValueError(f"Rate parity failed for reaction {item}: {error}")
        for equation, terms in endpoint_groups.items():
            expected = rate(terms, float(temperature))
            if expected < minimum_rates[equation][0]:
                minimum_rates[equation] = (expected, float(temperature))
    # Confirm complete equation-group forward production rates, not just k.
    for temperature in [298.15, 500, 1000, 2000, 3500]:
        gas.TPX = temperature, PRESSURE_ATM * ct.one_atm, np.arange(1, gas.n_species+1)
        actual_rop = gas.forward_rates_of_progress
        for equation, terms in endpoint_groups.items():
            items = [item for item in converted if item["equation"] == equation]
            indices = [i for item in items for i in item["variant_reactions_zero_based"]]
            reactants = gas.reaction(indices[0]).reactants
            order = sum(reactants.values())
            concentration_product = math.prod(
                gas.concentrations[gas.species_index(name)] ** coefficient
                for name, coefficient in reactants.items())
            expected = rate(terms, temperature) * 1e-3 ** (order-1) * concentration_product
            observed = sum(float(actual_rop[index]) for index in indices)
            error = abs(observed-expected) / max(abs(expected), 1e-300)
            equation_relative_errors[equation] = max(
                equation_relative_errors.get(equation, 0), error)
            if error > 1e-10:
                raise ValueError(f"Forward-rate parity failed for {equation}: {error}")
    result = {
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output": target.name,
        "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "cantera_version": ct.__version__, "species": gas.n_species,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "original_reactions": len(original["reactions"]),
        "variant_reactions": gas.n_reactions,
        "fixed_pressure_Pa": PRESSURE_ATM * ct.one_atm,
        "qualification_temperature_K": [LOWER_T, UPPER_T],
        "temperature_samples": len(temperatures),
        "maximum_rate_constant_relative_error": maximum_relative_error,
        "maximum_group_forward_rate_relative_error": max(equation_relative_errors.values()),
        "analytic_positivity_certificates": certificates,
        "minimum_group_cgs_rates_on_grid": minimum_rates,
        "converted_plog_reactions": converted,
        "original_to_variant_zero_based": mapping,
        "warnings": [str(item.message) for item in caught],
        "limits": [
            "100 atm only; no between-pressure equivalence claimed",
            "298–3500 K checked and signed pairs analytically positive on this interval",
            "Full author release, not an identified Liang methane submodel",
            "Other original rates, thermo and transport retained without qualification changes",
            "No flame calculation in this verification artifact"]}
    (args.output / "hp-fixed-100atm-validation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("converted_plog_reactions",
                                     "original_to_variant_zero_based",
                                     "analytic_positivity_certificates",
                                     "minimum_group_cgs_rates_on_grid",
                                     "warnings")}, indent=2))


def load_fixed_100atm(path, pressure_pa, temperature_k=298.15):
    """Load the exact qualified input with explicit pressure/temperature guards."""
    if pressure_pa != PRESSURE_ATM * ct.one_atm:
        raise ValueError("HP input is qualified only at exactly 100 atm")
    if not LOWER_T <= temperature_k <= UPPER_T:
        raise ValueError("HP input is qualified only for 298–3500 K")
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != TARGET_SHA:
        raise ValueError("Expected the qualified fixed-pressure mechanism")
    gas = ct.Solution(str(path))
    gas.TP = temperature_k, pressure_pa
    return gas


if __name__ == "__main__":
    main()
