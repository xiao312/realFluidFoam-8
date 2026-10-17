"""Create a declared reconstructed premixed startup pilot, not a speed result."""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from generate_counterflow import header

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("inputs", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("phi", type=float)
args = parser.parse_args()
if not math.isfinite(args.phi) or not 0.9 <= args.phi <= 1.4:
    raise ValueError("Supported equivalence ratio range: 0.90 to 1.40")
case = args.output.resolve()
subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("generate_counterflow.py")),
                str(args.inputs), str(case), "air-100"], check=True)


def write(name, text):
    with (case/name).open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


thermo = (case/"constant/thermo.inputData_GRI").read_text()
weights = {}
for name in ("CH4", "O2", "N2"):
    match = re.search(r"(?m)^"+name+r"\s*\{\s*specie\s*\{\s*molWeight\s+([\d.]+)", thermo)
    weights[name] = float(match.group(1))
masses = {"CH4": args.phi*weights["CH4"], "O2": 2*weights["O2"], "N2": 2*(79/21)*weights["N2"]}
total = sum(masses.values())
fractions = {name: value/total for name, value in masses.items()}
for name, value in dict(fractions, Ydefault=0, T=298, p=10132500, U="(0 0 0)").items():
    dimensions = {"T": "0 0 0 1 0 0 0", "p": "1 -1 -2 0 0 0 0", "U": "0 1 -1 0 0 0 0"}.get(name, "0 0 0 0 0 0 0")
    boundary = "type zeroGradient;"
    if name == "p":
        boundary = "type waveTransmissive; phi phi; psi thermo:psi; gamma 1; fieldInf 10132500; lInf 0.002; value uniform 10132500;"
    write("0/"+name, header(name, "volVectorField" if name == "U" else "volScalarField")+f"""
dimensions [{dimensions}]; internalField uniform {value};
boundaryField {{ left {{ {boundary} }} right {{ {boundary} }} sides {{ type empty; }} }}
""")
write("system/blockMeshDict", header("blockMeshDict")+"""
convertToMeters 0.001;
vertices ((0 0 0) (2 0 0) (2 0.01 0) (0 0.01 0)
          (0 0 0.01) (2 0 0.01) (2 0.01 0.01) (0 0.01 0.01));
blocks (hex (0 1 2 3 4 5 6 7) (200 1 1) simpleGrading (1 1 1));
edges ();
boundary (
left { type patch; faces ((0 4 7 3)); }
right { type patch; faces ((1 2 6 5)); }
sides { type empty; faces ((0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); }
);
mergePatchPairs ();
""")
write("system/setFieldsDict", header("setFieldsDict")+"""
defaultFieldValues (volScalarFieldValue T 298);
regions (boxToCell {
box (0.0009 -1 -1) (0.0011 1 1);
fieldValues (volScalarFieldValue T 1800);
});
""")
write("pilot.json", json.dumps(dict(case="premixed", phi=args.phi, pressure_Pa=10132500,
    unburned_temperature_K=298, length_m=0.002, cells=200, spacing_m=1e-5,
    kernel_width_m=0.0002, kernel_temperature_K=1800, mass_fractions=fractions,
    status="reconstructed startup pilot, not a flame-speed measurement", boundary_finalized=False), indent=2)+"\n")
print("Generated premixed pilot; runtime Cp/Cv boundary finalization and setFields required")
