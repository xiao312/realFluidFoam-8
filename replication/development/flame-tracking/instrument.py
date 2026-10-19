"""Add read-only tracking and omit unused instantaneous reaction-rate evaluation."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply']);p.add_argument('release',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();module=Path(__file__).resolve().parent
    subprocess.run([sys.executable,'-B',str(module.parent/'premixed-paper/instrument.py'),a.action,
                    str(a.release/'replication/development/solver'),str(a.output)],check=True)
    if a.action=='plan':return
    for name in ['FrontTracking.H','trackingCore.H']:shutil.copy2(module/name,a.output/name)
    def replace(name,old,new):
        path=a.output/name;text=path.read_text()
        if text.count(old)!=1:raise ValueError('Unexpected anchor '+old)
        path.write_text(text.replace(old,new))
    replace('rfReactingFoam.C','#include "FlameSpeedDiagnostics.H"','#include "FlameSpeedDiagnostics.H"\n#include "FrontTracking.H"')
    replace('rfReactingFoam.C','    FlameSpeedDiagnostics flameSpeed(mesh);',
            '    FlameSpeedDiagnostics flameSpeed(mesh);\n    FrontTracking frontTracking(mesh);\n    frontTracking.write(rho,U,T,Y[composition.species()["OH"]]);')
    # The prior end-step evaluator calls chemistry.calculate(); it is not needed
    # for kinematic tracking and is deliberately absent from this executable.
    (a.output/'endStepDiagnostics.H').write_text('if(frontTracking.due()) frontTracking.write(rho,U,T,Y[composition.species()["OH"]]);\n')
    replace('Make/files','/rfPaperReactingFoam','/rfTrackedReactingFoam')


if __name__=='__main__':main()
