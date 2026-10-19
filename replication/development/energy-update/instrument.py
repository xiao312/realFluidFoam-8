"""Build a separate tracked solver with only species-enthalpy reads changed."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('action', choices=['plan', 'apply'])
p.add_argument('release', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
module = Path(__file__).resolve().parent
subprocess.run([sys.executable, '-B', str(module.parent/'flame-tracking/instrument.py'),
                a.action, str(a.release), str(a.output)], check=True, stdout=subprocess.PIPE)
print(json.dumps({'source':str(a.release), 'output':str(a.output),
                  'executable':'rfEnergyReactingFoam', 'physics_changes':True,
                  'change':'Initial and timestep-end species enthalpy evaluated at current p,T'}))
if a.action == 'apply':
    shutil.copy2(module/'CurrentSpeciesEnthalpy.H', a.output)
    for name in ['rfReactingFoam.C', 'createFields.H']:
        path = a.output/name
        text = path.read_text()
        if text.count('thermo.hei(i)') != 1:
            raise ValueError('Unexpected enthalpy call count in '+name)
        text = text.replace('thermo.hei(i)', 'currentSpeciesEnthalpy(thermo, i)')
        if name == 'rfReactingFoam.C':
            text = text.replace('#include "psiReactionThermo.H"',
                                '#include "psiReactionThermo.H"\n#include "CurrentSpeciesEnthalpy.H"')
        path.write_text(text)
    path = a.output/'Make/files'
    path.write_text(path.read_text().replace('/rfTrackedReactingFoam', '/rfEnergyReactingFoam'))
