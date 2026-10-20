"""Isolate the six documented prompt-HCO additions in the publisher HP model."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import cantera as ct
import numpy as np
from ruamel.yaml import YAML

FIXED_SHA = "cc34fbe54bfe71c79edabc6763934bdfbe4d1046ae5e33f67ca1efae02aa9afb"
PUBLISHER_SHA = "6d44ddf4c95597464c20f363f47edf89941496d0add00585de1d4a55168b8dd1"
REMOVED = [46, 47, 49, 50, 52, 53]
PARENTS = {
    45: ({"CH2O": 1, "OH": 1}, {"HCO": 1, "H2O": 1}, [7.820e7, 1.630, -1055.]),
    48: ({"CH2O": 1, "H": 1}, {"HCO": 1, "H2": 1}, [5.860e3, 3.130, 1514.]),
    51: ({"CH2O": 1, "O": 1}, {"HCO": 1, "OH": 1}, [1.560e8, 1.670, 1770.]),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for name in ["mechanism", "qualification", "output"]:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    if ct.__version__ != "3.2.0" or digest(args.mechanism) != FIXED_SHA:
        raise ValueError("Use Cantera 3.2.0 and the exact qualified fixed-100-atm HP input")
    if args.output.exists():
        raise ValueError("Choose a new output directory")
    qualification = json.loads(args.qualification.read_text())
    if qualification["output_sha256"] != FIXED_SHA:
        raise ValueError("The mapping is not for this input")
    mapping = qualification["original_to_variant_zero_based"]
    removed = sorted(i for number in REMOVED for i in mapping[str(number)])
    parents = [i for number in PARENTS for i in mapping[str(number)]]
    if len(removed) != 6 or len(parents) != 3:
        raise ValueError("Unexpected endpoint specialization")
    yaml = YAML()
    data = yaml.load(args.mechanism.read_text(encoding="utf-8"))
    full = ct.Solution(str(args.mechanism))
    for number, (reactants, products, coefficients) in PARENTS.items():
        i = mapping[str(number)][0]
        reaction = full.reaction(i)
        if reaction.reactants != reactants or reaction.products != products:
            raise ValueError(f"Unexpected parent reaction {number}")
        literal = data["reactions"][i]["rate-constant"]
        if [literal[k] for k in ["A", "b", "Ea"]] != coefficients:
            raise ValueError("Parent coefficients do not match the publisher table")
        data["reactions"][i].pop("duplicate", None)
    kept = [i for i in range(full.n_reactions) if i not in removed]
    records = [{"author_reaction": number,
                "specialized_indices": mapping[str(number)],
                "equations": [full.reaction_equations([i])[0] for i in mapping[str(number)]]}
               for number in REMOVED]
    print(json.dumps(dict(removed=records, retained_reactions=len(kept),
                          pressure_Pa=100 * ct.one_atm)))
    if args.action == "plan":
        return
    data["reactions"] = [data["reactions"][i] for i in kept]
    data["description"] = str(data.get("description", "")) + (
        "\nSource-supported prompt-off sensitivity: author reactions 46/47,49/50,52/53 "
        "removed; baseline45/48/51 retained. Not an identified Liang subset.")
    stream = io.StringIO()
    yaml.dump(data, stream)
    text = stream.getvalue()
    reduced = ct.Solution(yaml=text)
    if reduced.species_names != full.species_names:
        raise ValueError("Species identity changed")
    checks = []
    for temperature in [298., 500., 1000., 1800., 2500., 3500.]:
        for composition_id, composition in enumerate([
                np.ones(full.n_species), np.arange(1, full.n_species + 1)]):
            full.TPX = reduced.TPX = temperature, 100 * ct.one_atm, composition
            for name in ["forward_rates_of_progress", "reverse_rates_of_progress"]:
                a, b = getattr(full, name)[kept], getattr(reduced, name)
                if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
                    raise ValueError("Nonfinite retained rate")
                error = float(np.max(np.abs(a-b) / np.maximum(np.maximum(np.abs(a), np.abs(b)), 1e-280)))
                checks.append(dict(T_K=temperature, composition=composition_id,
                                   property=name, max_relative=error))
                if error > 1e-10:
                    raise ValueError("A retained rate changed")
    args.output.mkdir(parents=True)
    target = args.output/"hp-prompt-off-fixed100atm.yaml"
    target.write_text(text, encoding="utf-8", newline="\n")
    record = dict(input_sha256=FIXED_SHA, output_sha256=digest(target),
                  publisher_zip_sha256=PUBLISHER_SHA,
                  publisher_url="https://ars.els-cdn.com/content/image/1-s2.0-S0010218017301724-mmc2.zip",
                  mapping_sha256=digest(args.qualification), script_sha256=digest(Path(__file__)),
                  removed=records, retained_parent_author_reactions=list(PARENTS),
                  retained_indices=kept, rate_checks=checks, species=reduced.n_species,
                  reactions=reduced.n_reactions, pressure_Pa=100 * ct.one_atm,
                  temperature_range_K=[298, 3500], exact_liang_subset=False)
    (args.output/"qualification.json").write_text(json.dumps(record, indent=2)+"\n",
                                                 encoding="utf-8", newline="\n")
    print(f"PASS {len(checks)} retained-rate checks; {reduced.n_reactions} reactions")


if __name__ == "__main__":
    main()
