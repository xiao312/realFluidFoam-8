"""Prepare separate tutorial and paper-condition meshes from preserved inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
FLAMES=HERE.parents[1]/'validation/flames'
sys.path.insert(0,str(FLAMES/'paper-campaign'))
from prepare import patch_boundary


def plan(condition,variant):
    pressure=int(condition.split('-')[1])*101325
    length=.005 if condition=='oxy-200' else .02
    if variant=='tutorial':nr,nz,ratio=80,[40,60,40],1
    elif condition=='oxy-1':nr,nz,ratio=1000,[244,400,244],1.5
    elif condition=='oxy-200':nr,nz,ratio=1000,[208,400,208],2
    else:nr,nz,ratio=4000,[189,1600,189],20
    outer=.3*length;n=nz[0]
    q=ratio**(1/(n-1));first=outer/n if ratio==1 else outer*(q-1)/(q**n-1)
    return dict(condition=condition,variant=variant,pressure_Pa=pressure,length_m=length,
        radial_cells=nr,axial_cells=nz,cells=nr*sum(nz),radial_spacing_m=length/nr,
        center_axial_spacing_m=.4*length/nz[1],outer_endpoint_spacing_m=[first,first*ratio],
        outer_expansion=ratio,qualification='preserved tutorial' if variant=='tutorial' else 'paper-informed reconstruction; zone extent and grading unpublished')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','apply'])
    p.add_argument('condition',choices=['oxy-1','oxy-200','air-100']);p.add_argument('variant',choices=['tutorial','paper']);p.add_argument('output',type=Path)
    args=p.parse_args();cfg=plan(args.condition,args.variant)
    if args.output.exists():raise ValueError('Refusing existing output')
    print(json.dumps(cfg,indent=2))
    if args.action=='plan':return
    if args.condition=='oxy-1':cmd=[str(FLAMES/'author-counterflow/prepare.py'),'apply',str(args.output),'full']
    else:cmd=[str(FLAMES/'paper-campaign/prepare.py'),'apply',args.condition,str(args.output),'full']
    subprocess.run([sys.executable,'-B',*cmd],check=True)
    if args.variant=='paper':
        for phase in ['one-step','gri30']:
            case=args.output/phase
            mesh=case/'system/blockMeshDict';text=mesh.read_text()
            # Preserve vertices/patches and replace only the three block resolutions/grading.
            index=[0]
            def block(match):
                i=index[0];index[0]+=1
                grade=[1/cfg['outer_expansion'],1,cfg['outer_expansion']][i]
                return match[1]+f"({cfg['radial_cells']} 1 {cfg['axial_cells'][i]}) simpleGrading (1 1 {grade:.16g})"
            text,count=re.subn(r'(hex\s*\([^)]*\)\s*)\(80 1 (?:40|60)\)\s*simpleGrading\s*\(1 1 1\)',block,text)
            assert count==3;mesh.write_text(text)
            if args.condition.startswith('oxy'):
                thermo_name='thermo.inputData' if phase=='one-step' else 'thermo.inputData_GRI'
                thermo=(case/'constant'/thermo_name).read_text()
                mw={n:float(re.search(r'(?m)^'+n+r'\s*\{\s*specie\s*\{\s*molWeight\s+([\d.]+)',thermo)[1]) for n in ['O2','CO2']}
                yo=.21*mw['O2']/(.21*mw['O2']+.79*mw['CO2'])
                for name,value in [('O2',yo),('CO2',1-yo)]:patch_boundary(case/'0'/name,'oxidizer',f'type fixedValue; value uniform {value:.16g};')
                for patch in ['fuel','oxidizer']:patch_boundary(case/'0/U',patch,'type fixedValue; value uniform (0 0 0);')
                (case/'pilot.json').write_text(json.dumps(dict(case=args.condition,pressure_Pa=cfg['pressure_Pa'],length_m=cfg['length_m'],velocity_constraint='momentum',velocities_finalized=False),indent=2)+'\n')
            for f in (case/'0').iterdir():
                if f.is_file() and f.name!='p':patch_boundary(f,'outlet','type zeroGradient;')
            metadata=json.loads((case/'author-case.json').read_text())
            metadata.update(cells=cfg['cells'],variant='paper-informed mesh reconstruction')
            (case/'author-case.json').write_text(json.dumps(metadata,indent=2)+'\n')
    cfg['input_hashes']={f.relative_to(args.output).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(args.output.rglob('*')) if f.is_file()}
    (args.output/'variant.json').write_text(json.dumps(cfg,indent=2)+'\n')


if __name__=='__main__':main()
