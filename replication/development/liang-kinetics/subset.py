"""Prepare an explicit carbon-count sensitivity mechanism, without rate fitting."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import cantera as ct
import numpy as np
from ruamel.yaml import YAML


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(full, max_carbon):
    species = [s for s in full.species() if s.composition.get("C", 0) <= max_carbon]
    names = {s.name for s in species}
    skeleton = ct.Solution(thermo="ideal-gas", kinetics="gas", species=species)
    reactions, indices, removed = [], [], []
    for i, reaction in enumerate(full.reactions()):
        participants = set(reaction.reactants) | set(reaction.products) | set(reaction.orders)
        body = reaction.third_body
        if body is not None and body.name != "M":
            participants.add(body.name)
        if not participants <= names:
            removed.append({"index": i, "equation": reaction.equation,
                            "absent": sorted(participants - names)})
            continue
        data = dict(reaction.input_data)
        if "efficiencies" in data:
            data["efficiencies"] = {k: v for k, v in data["efficiencies"].items()
                                    if k in names}
        reactions.append(ct.Reaction.from_dict(data, skeleton))
        indices.append(i)
    reduced = ct.Solution(thermo="ideal-gas", kinetics="gas", species=species,
                          reactions=reactions, transport_model="mixture-averaged")
    reduced.name = "gas"
    return reduced, indices, removed


def verify(full, reduced, indices):
    """Retained-channel parity where the discarded species are exactly absent."""
    records = []
    concentrations = [
        {name: 1 for name in reduced.species_names},
        {"CH4": 1, "O2": 2, "N2": 2 * 79 / 21},
        {"CO2": 1, "H2O": 2, "N2": 2 * 79 / 21, "H": 1e-7, "OH": 1e-5},
    ]
    for temperature in [298., 500., 1000., 1800., 2500., 3500.]:
        for composition_id, composition in enumerate(concentrations):
            full.TPX = reduced.TPX = temperature, 100 * ct.one_atm, composition
            for name in ["forward_rates_of_progress", "reverse_rates_of_progress"]:
                a = getattr(full, name)[indices]
                b = getattr(reduced, name)
                if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
                    raise ValueError("Nonfinite rate in retained-channel qualification")
                error = np.max(np.abs(a - b) / np.maximum(np.maximum(np.abs(a), np.abs(b)), 1e-280))
                # Very small cancellation in signed HP third-body terms can amplify
                # a relative error. Keep a separate global-scale residual too.
                global_error = np.max(np.abs(a - b)) / max(np.max(np.abs(a)), 1e-280)
                records.append(dict(T_K=temperature, composition=composition_id,
                                    property=name, max_relative=float(error),
                                    max_global_scaled=float(global_error)))
                if error > 1e-7 or global_error > 1e-12:
                    raise ValueError(f"Retained-channel parity failed: {records[-1]}")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-carbon", type=int, choices=[2], required=True)
    args = parser.parse_args()
    if ct.__version__ != "3.2.0":
        raise ValueError("Use the pinned Cantera 3.2.0 environment")
    if args.output.exists():
        raise ValueError("Choose a new output directory; historical inputs are immutable")
    full = ct.Solution(str(args.input))
    if full.thermo_model != "ideal-gas":
        raise ValueError("This sensitivity preparer supports ideal gas mechanisms only")
    reduced, indices, removed = select(full, args.max_carbon)
    record = dict(input=str(args.input.resolve()), input_sha256=sha(args.input),
                  cantera_version=ct.__version__, max_carbon=args.max_carbon,
                  interpretation="Structural sensitivity; not an identified Liang subset",
                  qualification_pressure_Pa=100 * ct.one_atm,
                  qualification_temperature_K=[298, 3500],
                  full_species=full.n_species, full_reactions=full.n_reactions,
                  retained_species=reduced.n_species, retained_reactions=reduced.n_reactions,
                  removed_species=sorted(set(full.species_names) - set(reduced.species_names)),
                  retained_reaction_indices=indices, removed_reactions=removed,
                  script_sha256=sha(Path(__file__)))
    print(json.dumps({k: record[k] for k in ["input_sha256", "full_species", "full_reactions",
                                           "retained_species", "retained_reactions"]}))
    if args.action == "plan":
        return
    record["rate_checks"] = verify(full, reduced, indices)
    # Retain the source YAML's units and scalar representation. Cantera 3.2's
    # writer fails for this signed HP input; no kinetics repair is implied.
    yaml = YAML()
    source = yaml.load(args.input.read_text(encoding="utf-8"))
    if len(source["phases"]) != 1 or len(source["reactions"]) != full.n_reactions:
        raise ValueError("Expected one phase with an explicit ordered reaction list")
    source["phases"][0]["species"] = reduced.species_names
    source["species"] = [s for s in source["species"] if s["name"] in reduced.species_names]
    source["reactions"] = [source["reactions"][i] for i in indices]
    for reaction in source["reactions"]:
        if "efficiencies" in reaction:
            reaction["efficiencies"] = {
                k: v for k, v in reaction["efficiencies"].items()
                if k in reduced.species_names}
    source["description"] = (str(source.get("description", "")) +
                             "\nC0-C2 structural sensitivity; not a Liang author subset.")
    stream = io.StringIO()
    yaml.dump(source, stream)
    text = stream.getvalue()
    roundtrip = ct.Solution(yaml=text)
    record["serialized_rate_checks"] = verify(full, roundtrip, indices)
    args.output.mkdir(parents=True)
    target = args.output / "mechanism.yaml"
    target.write_text(text, encoding="utf-8", newline="\n")
    record["output_sha256"] = sha(target)
    (args.output / "qualification.json").write_text(json.dumps(record, indent=2) + "\n",
                                                   encoding="utf-8", newline="\n")
    print(f"PASS retained rates before/after serialization: {target}")


if __name__ == "__main__":
    main()
