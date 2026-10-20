"""Build a named current-enthalpy solver against the selected library."""
import argparse
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['plan','apply'])
p.add_argument('release',type=Path);p.add_argument('output',type=Path)
a=p.parse_args()
subprocess.run([sys.executable,'-B',str(a.release/'replication/development/flame-tracking/instrument.py'),
                a.action,str(a.release),str(a.output)],check=True)
print('Current species enthalpy; selected native library; unchanged native chemistry/transport')
if a.action=='apply':
    for name in ['rfReactingFoam.C','createFields.H']:
        path=a.output/name;text=path.read_text()
        if text.count('thermo.hei(i)')!=1:raise ValueError('Unexpected enthalpy anchor')
        path.write_text(text.replace('thermo.hei(i)','thermo.composition().HE(i, thermo.p(), thermo.T())'))
    path=a.output/'Make/files';text=path.read_text()
    if text.count('/rfTrackedReactingFoam')!=1:raise ValueError('Unexpected executable name')
    path.write_text(text.replace('/rfTrackedReactingFoam','/rfThermoReactingFoam'))
