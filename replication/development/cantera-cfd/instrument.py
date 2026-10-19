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
shutil.copy2(module/'RuntimeTimers.H',a.output)
shutil.copy2(module.parent/'cantera-bridge/bridge.h',a.output)
def replace(name,old,new):
    path=a.output/name;text=path.read_text()
    if text.count(old)!=1:raise ValueError('Unexpected anchor '+old)
    path.write_text(text.replace(old,new))
for name in ['rfReactingFoam.C','createFields.H']:
    replace(name,'thermo.hei(i)','thermo.composition().HE(i, thermo.p(), thermo.T())')
replace('rfReactingFoam.C','#include "FrontTracking.H"',
        '#include "FrontTracking.H"\n#include "CanteraTransport.H"\n#include "RuntimeTimers.H"')
replace('rfReactingFoam.C','    turbulence->validate();',
        '    CanteraTransport canteraTransport(mesh, composition.species());\n'
        '    RuntimeTimers runtimeTimers(mesh);\n'
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
for include,label in [('rhoEqn.H','continuity'),('UEqn.H','momentum'),('YEqn.H','species_total'),
                       ('EEqn.H','energy'),('pEqn.H','pressure')]:
    statement='#include "'+include+'"'
    replace('rfReactingFoam.C',statement,
            f'runtimeTimers.start("{label}");\n{statement}\nruntimeTimers.stop("{label}");')
replace('rfReactingFoam.C','        //- Update properties for nex time step //Nam',
        '        runtimeTimers.start("properties");\n        //- Update properties for nex time step //Nam')
replace('rfReactingFoam.C','        // ---\n        #include "endStepDiagnostics.H"',
        '        runtimeTimers.stop("properties");\n        runtimeTimers.write(runTime);\n'
        '        // ---\n        #include "endStepDiagnostics.H"')
replace('YEqn.H','\n    if(canteraTransport.integratesChemistry())\n',
        '\n    runtimeTimers.start("chemistry");\n    if(canteraTransport.integratesChemistry())\n')
replace('YEqn.H','    volScalarField Yt(0.0*Y[0]);',
        '    runtimeTimers.stop("chemistry");\n    volScalarField Yt(0.0*Y[0]);')
replace('YEqn.H','        // calculate correction term',
        '        runtimeTimers.start("diffusion_pairs");\n        // calculate correction term')
replace('YEqn.H','        if (i != inertIndex && composition.active(i))',
        '        runtimeTimers.stop("diffusion_pairs");\n        if (i != inertIndex && composition.active(i))')
replace('YEqn.H','            YiEqn.solve("Yi");',
        '            runtimeTimers.start("species_linear");\n            YiEqn.solve("Yi");\n'
        '            runtimeTimers.stop("species_linear");')
replace('Make/options','    -lcombustionModels','    -lcombustionModels \\\n    -ldl')
