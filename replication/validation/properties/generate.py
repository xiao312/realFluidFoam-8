"""Generate a fresh one-cell property case from pinned author coefficients."""
import hashlib
import json
import re
import sys
from pathlib import Path


def header(name, kind="dictionary"):
    return 'FoamFile { version 2.0; format ascii; class %s; object %s; }\n' % (kind, name)


def species_block(text, name):
    match = re.search(r"(?m)^" + re.escape(name) + r"\s*\{", text)
    if not match:
        raise ValueError("Missing species: " + name)
    depth = 0
    for pos in range(text.index("{", match.start()), len(text)):
        depth += (text[pos] == "{") - (text[pos] == "}")
        if depth == 0:
            return text[match.start():pos+1]
    raise ValueError("Unclosed species dictionary")


def generate(inputs, output, eos, species="CH4", data=None):
    if eos not in ("SRK", "PR"):
        raise ValueError("EOS must be SRK or PR")
    if species not in ("CH4", "N2") or (species == "N2" and data is None):
        raise ValueError("N2 requires its pinned upstream thermochemistry path")
    manifest = json.loads((inputs / "provenance.json").read_text())
    for item in manifest["files"]:
        assert hashlib.sha256((inputs/item["file"]).read_bytes()).hexdigest() == item["stored_sha256"]
    output.mkdir(parents=True, exist_ok=False)
    for part in ("0", "constant", "system"):
        (output/part).mkdir()
    def write(name, text):
        with (output/name).open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    block = species_block((data or inputs/"property-thermo.inputData").read_text(), species)
    model = "soaveRedlichKwong" if eos == "SRK" else "PengRobinson"
    write("constant/thermophysicalProperties", header("thermophysicalProperties") +
          "thermoType { type hePsiThermo; mixture %schungTakaMixture; transport chungTaka; "
          "thermo rfJanaf; energy sensibleEnthalpy; equationOfState %s; specie rfSpecie; }\n"
          "inertSpecie %s;\nspecies (%s);\n%s\n" % (eos, model, species, species, block))
    for name, dimensions, value in (("p", "1 -1 -2 0 0 0 0", "101325"),
                                     ("T", "0 0 0 1 0 0 0", "300"),
                                     (species, "0 0 0 0 0 0 0", "1"),
                                     ("Ydefault", "0 0 0 0 0 0 0", "0")):
        write("0/"+name, header(name, "volScalarField") +
              "dimensions [%s]; internalField uniform %s;\n"
              "boundaryField { allFaces { type fixedValue; value uniform %s; } }\n" %
              (dimensions, value, value))
    write("system/blockMeshDict", header("blockMeshDict") + """
convertToMeters 0.001;
vertices ((0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 1) (1 0 1) (1 1 1) (0 1 1));
blocks (hex (0 1 2 3 4 5 6 7) (1 1 1) simpleGrading (1 1 1));
edges ();
boundary (allFaces { type patch; faces ((0 4 7 3) (1 2 6 5) (0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); });
mergePatchPairs ();
""")
    write("system/controlDict", header("controlDict") + """
application rfPropertyProbe;
startFrom startTime; startTime 0; stopAt endTime; endTime 0; deltaT 1;
writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 12;
runTimeModifiable false;
""")
    write("system/fvSchemes", header("fvSchemes") + """
ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes { default none; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
""")
    write("system/fvSolution", header("fvSolution") + "solvers {}\n")
    print("Generated", eos, output)


if __name__ == "__main__":
    generate(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3],
             sys.argv[4] if len(sys.argv) > 4 else "CH4", Path(sys.argv[5]).resolve() if len(sys.argv) > 5 else None)
