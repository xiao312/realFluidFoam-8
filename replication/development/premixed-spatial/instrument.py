"""Extend the qualified generator with spatial output in a separate executable."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def instrument(action,release,output):
    module=Path(__file__).resolve().parent
    paper=release/'replication/development/premixed-paper'
    subprocess.run([sys.executable,'-B',str(paper/'instrument.py'),action,
                    str(release/'replication/development/solver'),str(output)],check=True)
    if action=='plan':return
    def replace(file,old,new):
        path=output/file;text=path.read_text()
        if text.count(old)!=1:raise ValueError('Unexpected anchor: '+old)
        path.write_text(text.replace(old,new))
    shutil.copy2(module/'SpatialSpeedFields.H',output/'SpatialSpeedFields.H')
    replace('FlameSpeedDiagnostics.H','#include <memory>',
            '#include <memory>\n#include "SpatialSpeedFields.H"')
    replace('FlameSpeedDiagnostics.H','        Foam::volVectorField gradient',
            '        writeSpatialSpeedFields(stage,mesh_,rho,U,T,p,OH,source,diffusion);\n        Foam::volVectorField gradient')
    initial=(paper/'endStepDiagnostics.H').read_text().replace('instantaneous_end_step','instantaneous_checkpoint')
    (output/'checkpointDiagnostics.H').write_text(initial)
    replace('rfReactingFoam.C','    while (pimple.run(runTime))',
            '    #include "checkpointDiagnostics.H"\n\n    while (pimple.run(runTime))')
    replace('Make/files','/rfPaperReactingFoam','/rfSpatialReactingFoam')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','apply'])
    p.add_argument('release',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();instrument(a.action,a.release,a.output)
