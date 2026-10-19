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
print('Cantera conductivity/diffusion and current native species enthalpy; chemistry unchanged')
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
        '    canteraTransport.update(T,p,Y,kappa,Dimix);\n    turbulence->validate();')
replace('rfReactingFoam.C','        // ---\n        #include "endStepDiagnostics.H"',
        '        canteraTransport.update(T,p,Y,kappa,Dimix);\n'
        '        // ---\n        #include "endStepDiagnostics.H"')
replace('Make/files','/rfTrackedReactingFoam','/rfCanteraTransportFoam')
replace('Make/options','    -lcombustionModels','    -lcombustionModels \\\n    -ldl')
