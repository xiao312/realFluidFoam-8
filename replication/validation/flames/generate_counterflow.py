"""Generate explicit coarse counterflow pilots; never label these paper meshes."""
import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path


def header(name, kind="dictionary"):
    return f"FoamFile {{ version 2.0; format ascii; class {kind}; object {name}; }}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("case", choices=("oxy-1", "oxy-200", "air-100"))
    args = parser.parse_args()
    inputs, output = args.inputs.resolve(), args.output.resolve()
    manifest = json.loads((inputs/"provenance.json").read_text())
    for entry in manifest["files"]:
        if hashlib.sha256((inputs/entry["file"]).read_bytes()).hexdigest() != entry["stored_sha256"]:
            raise ValueError("Input hash mismatch: " + entry["file"])
    pressure = int(args.case.split("-")[1])*101325
    air = args.case.startswith("air")
    length = 0.005 if pressure == 200*101325 else 0.02
    oxidizer_temperature = 300 if air else 1000
    inert = "N2" if air else "CO2"
    # Molecular weights are read from the pinned author input, not a second database.
    thermo = (inputs/"thermo.inputData_GRI").read_text()
    weights = {}
    for name in ("CH4", "O2", inert):
        match = re.search(r"(?m)^"+name+r"\s*\{\s*specie\s*\{\s*molWeight\s+([\d.]+)", thermo)
        weights[name] = float(match.group(1))
    oxygen = 0.21*weights["O2"]/(0.21*weights["O2"]+0.79*weights[inert])
    output.mkdir(parents=True, exist_ok=False)
    for directory in ("0", "constant", "system"):
        (output/directory).mkdir()
    def write(name, text):
        with (output/name).open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    for name in ("thermo.inputData_GRI", "reactionsGRI"):
        shutil.copyfile(inputs/name, output/"constant"/name)
    write("constant/thermophysicalProperties", header("thermophysicalProperties")+f"""
thermoType {{ type hePsiThermo; mixture SRKchungTakaMixture; transport chungTaka;
thermo rfJanaf; energy sensibleEnthalpy; equationOfState soaveRedlichKwong; specie rfSpecie; }}
inertSpecie {inert};
#include "thermo.inputData_GRI"
""")
    write("constant/chemistryProperties", header("chemistryProperties")+"""
chemistryType { solver ode; method SRKchungTakaStandard; }
chemistry on;
initialChemicalTimeStep 1e-8;
odeCoeffs { solver seulex; absTol 1e-8; relTol 1e-6; }
#include "reactionsGRI"
""")
    write("constant/combustionProperties", header("combustionProperties")+"combustionModel laminar;\n")
    write("constant/momentumTransport", header("momentumTransport")+"simulationType laminar;\n")
    # A uniform hot mixed initial state is an explicit pilot ignition assumption.
    # Replace it with a converged initialization for mesh studies.
    def field(name, dimensions, initial, fuel, oxidizer, outlet="zeroGradient", kind="volScalarField"):
        return header(name, kind)+f"""
dimensions [{dimensions}]; internalField uniform {initial};
boundaryField {{
fuel {{ {fuel} }}
oxidizer {{ {oxidizer} }}
outlet {{ type {outlet}; }}
axis {{ type empty; }}
front {{ type wedge; }}
back {{ type wedge; }}
}}
"""
    fixed = lambda value: f"type fixedValue; value uniform {value};"
    write("0/T", field("T", "0 0 0 1 0 0 0", 1800, fixed(300), fixed(oxidizer_temperature)))
    write("0/p", field("p", "1 -1 -2 0 0 0 0", pressure, "type zeroGradient;", "type zeroGradient;",
                        f"totalPressure; p0 uniform {pressure}; value uniform {pressure}"))
    composition = {"CH4": (0.5, 1, 0), "O2": (oxygen/2, 0, oxygen),
                   inert: ((1-oxygen)/2, 0, 1-oxygen), "Ydefault": (0, 0, 0)}
    for name, (initial, fuel, oxidizer) in composition.items():
        write("0/"+name, field(name, "0 0 0 0 0 0 0", initial, fixed(fuel), fixed(oxidizer)))
    write("0/U", field("U", "0 1 -1 0 0 0 0", "(0 0 0)", fixed("(0 0 0)"),
                       fixed("(0 0 0)"), kind="volVectorField"))
    radius = length
    x, y = radius*math.cos(math.radians(2.5)), radius*math.sin(math.radians(2.5))
    write("system/blockMeshDict", header("blockMeshDict")+f"""
convertToMeters 1;
vertices ((0 0 0) ({x} {y} 0) ({x} {-y} 0)
          (0 0 {length}) ({x} {y} {length}) ({x} {-y} {length}));
blocks (hex (0 2 1 0 3 5 4 3) (8 1 40) simpleGrading (1 1 1));
edges ();
boundary (
fuel {{ type patch; faces ((1 2 0 0)); }}
oxidizer {{ type patch; faces ((3 5 4 3)); }}
outlet {{ type patch; faces ((1 4 5 2)); }}
axis {{ type empty; faces ((3 0 0 3)); }}
front {{ type wedge; faces ((0 2 5 3)); }}
back {{ type wedge; faces ((0 3 4 1)); }}
);
mergePatchPairs ();
""")
    write("system/controlDict", header("controlDict")+"""
application realFluidReactingFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime 1e-6; deltaT 1e-8;
adjustTimeStep no; maxCo 0.2;
writeControl timeStep; writeInterval 100; writeFormat ascii; writePrecision 12;
purgeWrite 0; runTimeModifiable false;
""")
    write("system/fvSchemes", header("fvSchemes")+"""
ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes { default Gauss linear; div(phi,U) Gauss limitedLinearV 1;
div(phi,Yi_h) Gauss limitedLinear 1; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
""")
    write("system/fvSolution", header("fvSolution")+"""
solvers {
"rho.*" { solver diagonal; }
p { solver PCG; preconditioner DIC; tolerance 1e-7; relTol 0.1; }
pFinal { $p; relTol 0; }
"(U|h|e)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.1; }
"(U|h|e)Final" { $U; relTol 0; }
"Yi.*" { $hFinal; }
}
PIMPLE { momentumPredictor yes; nOuterCorrectors 1; nCorrectors 2; nNonOrthogonalCorrectors 0; }
""")
    write("pilot.json", json.dumps(dict(case=args.case, pressure_Pa=pressure, length_m=length,
        oxidizer_mass_fraction_O2=oxygen, velocity_constraint="mass" if air else "momentum",
        cells=320, status="coarse ignition/cost pilot, not scientific validation",
        velocities_finalized=False), indent=2)+"\n")
    print("Generated 320-cell pilot; inlet-density finalization required:", output)


if __name__ == "__main__":
    main()
