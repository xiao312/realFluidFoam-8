"""Create an opt-in diagnostic solver without changing the baseline equations."""
import argparse
import json
from pathlib import Path
import shutil


def instrument(action, source, output):
    if output.exists():
        raise ValueError("Refusing existing solver output")
    print(json.dumps({"source":str(source.resolve()),"output":str(output.resolve()),
                      "executable":"rfPaperReactingFoam","physics_changes":False}))
    if action=="plan": return
    shutil.copytree(source,output)
    module=Path(__file__).resolve().parent
    for name in ["sampling.H","FlameSpeedDiagnostics.H","endStepDiagnostics.H"]:
        shutil.copy2(module/name,output/name)
    def replace(path,old,new):
        text=path.read_text()
        if text.count(old)!=1: raise ValueError("Unexpected source anchor: "+old)
        path.write_text(text.replace(old,new))
    main=output/"rfReactingFoam.C"
    replace(main,'#include "fvcSmooth.H"','#include "fvcSmooth.H"\n#include "FlameSpeedDiagnostics.H"')
    replace(main,'    turbulence->validate();','    turbulence->validate();\n    FlameSpeedDiagnostics flameSpeed(mesh);')
    replace(main,'        runTime.write();','        #include "endStepDiagnostics.H"\n        runTime.write();')
    replace(output/"Make/files",'$(FOAM_USER_APPBIN)/rfReactingFoam','$(FOAM_USER_APPBIN)/rfPaperReactingFoam')
    species=output/"YEqn.H"
    replace(species,'            fvScalarMatrix YiEqn','''            const bool sampleOH=flameSpeed.due() && Yi.name()=="OH";
            autoPtr<volScalarField> sampledExplicit;
            scalarField sampledSource;
            if (sampleOH)
            {
                sampledSource=mesh.lookupObject<basicChemistryModel>("chemistryProperties").RR(i);
                sampledExplicit.reset(new volScalarField
                (
                    "diagnosticExplicitDiffusion",
                    fvc::laplacian(rho*Dimix[i]*Yi/Wmix,Wmix)
                    -sumDiffusionCorrections1-sumDiffusionCorrections2
                ));
            }

            fvScalarMatrix YiEqn''')
    replace(species,'            Yt += Yi;','''            Yt += Yi;
            if (sampleOH)
            {
                volScalarField diffusion
                (
                    "diagnosticSolvedDiffusion",
                    fvc::laplacian(rho*Dimix[i],Yi)+sampledExplicit()
                );
                flameSpeed.write("integrated_species_solve",rho,U,T,p,Yi,sampledSource,diffusion);
            }''')


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=["plan","apply"]);p.add_argument("source",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();instrument(a.action,a.source,a.output)
