"""Build a separate ideal-gas Cantera transport experiment from tracked source."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['plan','apply'])
p.add_argument('release',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();module=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-B',str(module.parent/'flame-tracking/instrument.py'),
                a.action,str(a.release),str(a.output)],check=True)
print('Cantera transport with explicit native/adiabaticCP chemistry mode; current native species enthalpy')
if a.action=='plan':sys.exit(0)
shutil.copy2(module/'CanteraTransport.H',a.output)
shutil.copy2(module.parent/'cantera-bridge/bridge.h',a.output)
def replace(name,old,new):
    path=a.output/name;text=path.read_text()
    if text.count(old)!=1:raise ValueError('Unexpected anchor '+old)
    path.write_text(text.replace(old,new))
for name in ['rfReactingFoam.C','createFields.H']:
    replace(name,'thermo.hei(i)','thermo.composition().HE(i, thermo.p(), thermo.T())')
replace('rfReactingFoam.C','#include "FrontTracking.H"',
        '#include "FrontTracking.H"\n#include "CanteraTransport.H"')
replace('rfReactingFoam.C','    turbulence->validate();',
        '    CanteraTransport canteraTransport(mesh, composition.species());\n'
        '    scalarField canteraFormationHeats(Y.size());\n'
        '    scalarField canteraWeights(Y.size());\n'
        '    forAll(Y,i) {canteraFormationHeats[i]=composition.Hf(i);canteraWeights[i]=composition.W(i);}\n'
        '    canteraTransport.setFormationHeats(canteraFormationHeats,canteraWeights);\n'
        '    canteraTransport.update(T,p,Y,kappa,Dimix);\n    turbulence->validate();')
replace('rfReactingFoam.C','        // ---\n        #include "endStepDiagnostics.H"',
        '        canteraTransport.update(T,p,Y,kappa,Dimix);\n'
        '        // ---\n        #include "endStepDiagnostics.H"')
replace('YEqn.H','    reaction->correct();\n    Qdot = reaction->Qdot();',
        '    if(canteraTransport.integratesChemistry())\n'
        '        canteraTransport.correctChemistry(T,p,rho,Y,runTime.deltaTValue(),Qdot);\n'
        '    else { reaction->correct(); Qdot=reaction->Qdot(); }')
replace('YEqn.H','            fvScalarMatrix YiEqn',
        '            tmp<fvScalarMatrix> selectedReaction=reaction->R(Yi);\n'
        '            if(canteraTransport.integratesChemistry()) {\n'
        '                selectedReaction=tmp<fvScalarMatrix>(new fvScalarMatrix(Yi,dimMass/dimTime));\n'
        '                selectedReaction.ref().source()=mesh.V()*canteraTransport.source(i).primitiveField();\n'
        '            }\n            fvScalarMatrix YiEqn')
replace('YEqn.H','                reaction->R(Yi)','                selectedReaction')
replace('YEqn.H','                sampledSource=mesh.lookupObject<basicChemistryModel>("chemistryProperties").RR(i);',
        '                if(canteraTransport.integratesChemistry()) sampledSource=canteraTransport.source(i).primitiveField();\n'
        '                else sampledSource=mesh.lookupObject<basicChemistryModel>("chemistryProperties").RR(i);')
replace('Make/files','/rfTrackedReactingFoam','/rfCanteraBridgeFoam')
replace('Make/options','    -lcombustionModels','    -lcombustionModels \\\n    -ldl')
