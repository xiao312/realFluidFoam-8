"""Prepare hash-recorded Burke hydrogen inputs; plan makes no writes."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(args):
    import cantera as ct

    if ct.__version__ != "3.2.0":
        raise ValueError("Use the pinned Cantera 3.2.0 environment")
    gas = ct.Solution(args.mechanism)
    expected = ["H", "H2", "O", "OH", "H2O", "O2", "HO2", "H2O2",
                "N2", "AR", "HE", "CO", "CO2"]
    if gas.species_names != expected or gas.n_reactions != 27:
        raise ValueError("Expected the complete author Burke 2012 mechanism")
    if args.output.exists():
        raise ValueError("Choose a new immutable output directory")
    raw = args.mechanism.read_bytes()
    # The supplied converted author file has one malformed page-range dash in
    # a reaction note. Repair only that exact nonnumeric note, never parameters.
    bad_note = b"5718\xef\xbf5727"
    repaired_notes = raw.count(bad_note)
    source = raw.replace(bad_note, b"5718-5727").decode("utf-8")
    table = {row[0]: row[1:] for line in args.species.read_text().splitlines()
             if (row := line.split())}
    # NIST WebBook He Tc/Pc/rhoc; CoolProp He acentric factor.
    # HE has exactly zero elemental abundance in this H2/air campaign.
    table["HE"] = [5.2, 227400., 1/17.40, gas.molecular_weights[10], -0.385, 1]
    rows = []
    for k, name in enumerate(expected):
        values = list(table[name])
        values[3] = gas.molecular_weights[k]  # use mechanism atomic weights
        rows.append(" ".join(map(str, [name, *values])))
    manifest = {
        "mechanism": "Burke et al. 2012, author 6-10-2011 N2 bath-gas variant",
        "mechanism_sha256": digest(args.mechanism), "species": expected,
        "repaired_nonnumeric_page_range_notes": repaired_notes,
        "reactions": 27, "critical_table_sha256": digest(args.species),
        "helium_sources": [
            "https://webbook.nist.gov/cgi/cbook.cgi?ID=C7440597&Mask=4",
            "https://raw.githubusercontent.com/CoolProp/CoolProp/master/dev/fluids/Helium.json"],
        "helium_scope": "zero elemental abundance in H2/air; retained author species",
        "pressure_Pa": 10132500, "Tu_K": 298, "air": "O2:0.21,N2:0.79",
        "transport": "author conventional LJ rows; appended pair extension excluded",
        "limits": ["Tu not specified by Liang", "Liang critical table unavailable",
                   "rich-H2 conductivity modification not specified",
                   "Soret off; paper setting unspecified",
                   "Figure 6 diffusion species/closure unspecified"],
    }
    pairs = []
    if args.pairs:
        data = json.loads(args.pairs.read_text())
        for pair in data["pairs"]:
            if pair["present_in_burke_mechanism"]:
                pairs.append(" ".join(map(str, [*pair["pair"], *pair["D_coefficients"]])))
        if len(pairs) != 10:
            raise ValueError("Expected ten applicable author diffusion pairs")
        manifest["transport"] = "author LJ plus ten quantum binary-diffusion overrides"
        manifest["pair_source_sha256"] = digest(args.pairs)
        manifest["limits"].append("Liang use of appended Burke transport extension unknown")
    print(json.dumps(manifest, indent=2))
    if args.action == "plan":
        return
    if source.count("thermo: ideal-gas") != 1:
        raise ValueError("Expected one ideal phase")
    args.output.mkdir(parents=True)
    for name, text in {
        "ideal.yaml": source,
        "srk.yaml": source.replace("thermo: ideal-gas", "thermo: liang-srk"),
        "species.txt": "\n".join(rows) + "\n",
        "pairs.txt": "\n".join(pairs) + ("\n" if pairs else ""),
        "manifest.json": json.dumps(manifest, indent=2) + "\n",
    }.items():
        (args.output / name).write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for field in ("mechanism", "species", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--pairs", type=Path)
    prepare(parser.parse_args())
