"""Verify pinned author inputs and prepare an explicit OF8 compatibility port."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def write(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def species_block(text):
    match = re.search(r"\bspecies\s*(?:\d+\s*)?\(.*?\)\s*;", text, re.S)
    if not match:
        raise ValueError("Missing species list")
    return match.group()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("output", type=Path)
    parser.add_argument("mode", choices=["smoke", "full"])
    args = parser.parse_args()
    manifest = json.loads((HERE / "provenance.json").read_text())
    for entry in manifest["files"]:
        if hashlib.sha256((HERE / "original" / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Original input hash mismatch: " + entry["path"])
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Refusing existing output: " + str(output))
    print(json.dumps(dict(output=str(output), mode=args.mode, source=manifest["revision"],
                         cells=11200, ranks=8, delta_t_s=1e-6,
                         end_times_s=[1e-5, 1e-5] if args.mode == "smoke" else [.13, .07]), indent=2))
    if args.action == "plan":
        return
    for original, name, end in [("1stepReactionMech", "one-step", .13), ("GRI30", "gri30", .07)]:
        case = output / name
        shutil.copytree(HERE / "original" / original, case)
        thermo_file = "thermo.inputData" if name == "one-step" else "thermo.inputData_GRI"
        reactions = "reactions" if name == "one-step" else "reactionsGRI"
        species = species_block((case / "constant" / reactions).read_text())
        reaction_file = case / "constant" / reactions
        reaction_text = reaction_file.read_text().replace(
            "reversiblethirdBodyArrheniusReaction", "reversibleThirdBodyArrhenius")
        reaction_text = re.sub(r"(\btype\s+\w+)Reaction;", r"\1;", reaction_text)
        write(reaction_file, reaction_text)
        write(case / "constant/thermophysicalProperties", """FoamFile { version 2.0; format ascii; class dictionary; object thermophysicalProperties; }
thermoType { type hePsiThermo; mixture SRKchungTakaMixture; transport chungTaka;
thermo rfJanaf; energy sensibleEnthalpy; equationOfState soaveRedlichKwong; specie rfSpecie; }
inertSpecie CO2;
""" + species + '\n#include "' + thermo_file + '"\n')
        chemistry = case / "constant/chemistryProperties"
        write(chemistry, chemistry.read_text() + '\n#include "' + reactions + '"\n')
        (case / "constant/turbulenceProperties").rename(case / "constant/momentumTransport")
        transport = case / "constant/momentumTransport"
        write(transport, transport.read_text().replace("object      turbulenceProperties", "object      momentumTransport"))
        end = 1e-5 if args.mode == "smoke" else end
        # GRI startup is expensive: retain restart points within a bounded job.
        write_interval = end if args.mode == "smoke" else (.001 if name == "gri30" else .01)
        write(case / "system/controlDict", f"""FoamFile {{ version 2.0; format ascii; class dictionary; object controlDict; }}
application realFluidReactingFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {end}; deltaT 1e-6;
writeControl adjustableRunTime; writeInterval {write_interval};
purgeWrite 0; writeFormat ascii; writePrecision 12; writeCompression off;
timeFormat general; timePrecision 9; runTimeModifiable false; adjustTimeStep no; maxCo 0.4;
""")
        write(case / "system/decomposeParDict", """FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }
numberOfSubdomains 8; method simple; simpleCoeffs { n (8 1 1); delta 0.001; }
""")
        solution = case / "system/fvSolution"
        text, replacements = re.subn(r"(?m)^(\s*)Yi\s*$", r'\1"Yi.*"', solution.read_text())
        if replacements != 1:
            raise ValueError("Expected one original Yi solver entry")
        write(solution, text)
        write(case / "author-case.json", json.dumps(dict(source=manifest["revision"], mode=args.mode,
              phase=name, cells=11200, species=species.split("(", 1)[1].rsplit(")", 1)[0].split(),
              end_time_s=end, scientific_status="author settings port; convergence not established"), indent=2)+"\n")


if __name__ == "__main__":
    main()
