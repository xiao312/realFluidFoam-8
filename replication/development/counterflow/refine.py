"""Plan/apply a paper-resolution oxyfuel warm start from an immutable checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'validation/flames/adaptive'))
from fields import species

DONORS={'oxy-1':('124767586','0.07'),'oxy-200':('124767667','0.058')}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply'])
    parser.add_argument('condition',choices=list(DONORS))
    parser.add_argument('job',type=Path)
    args=parser.parse_args();job=args.job.resolve()
    root=job.parent.parent
    if job.parent.name!='jobs' or not job.name.isdigit():raise ValueError('Expected ROOT/jobs/JOB_ID')
    donor_id,time=DONORS[args.condition];source=root/'jobs'/donor_id/'case'
    for name in ['paper-cases','donor']:
        if (job/name).exists():raise ValueError('Refusing existing '+str(job/name))
    if not source.is_dir():raise ValueError('Missing source '+str(source))
    names=species(source);assert len(names)==53
    fields=['T','p','U',*names]
    hashes={}
    for rank in range(8):
        for name in fields:
            path=source/('processor'+str(rank))/time/name
            if not path.is_file():raise ValueError('Missing checkpoint field '+str(path))
            hashes[str(path.relative_to(root))]=digest(path)
    cfg={'condition':args.condition,'donor_job':donor_id,'donor_time_s':float(time),
         'ranks':32,'target_time_s':1e-5,'initial_dt_s':1e-7,'max_dt_s':1e-6,'max_co':.2,
         'mapping':'OF8 mapFields interpolate, primitive fields only; nonconservative warm start',
         'checkpoint_sha256':hashes}
    print(json.dumps(cfg,indent=2))
    if args.action=='plan':return
    subprocess.run([sys.executable,'-B',str(HERE/'prepare.py'),'apply',args.condition,'paper',str(job/'paper-cases')],check=True)
    case=job/'paper-cases/gri30'
    if species(case)!=names:raise ValueError('Donor/target species order differs')
    template=(case/'0/Ydefault').read_text()
    for name in names:
        path=case/'0'/name
        if not path.exists():path.write_text(re.sub(r'\bobject\s+Ydefault;', 'object '+name+';',template))
    control=case/'system/controlDict'
    control.write_text('''FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application rfReactingFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime 1e-5; deltaT 1e-7;
adjustTimeStep yes; maxCo 0.2; maxDeltaT 1e-6;
writeControl adjustableRunTime; writeInterval 1e-5; purgeWrite 0;
writeFormat ascii; writePrecision 12; writeCompression off;
timeFormat general; timePrecision 12; runTimeModifiable false;
''')
    (case/'system/decomposeParDict').write_text('''FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }
numberOfSubdomains 32; method simple; simpleCoeffs { n (8 1 4); delta 0.001; }
''')
    (case/'system/mapFieldsDict').write_text('''FoamFile { version 2.0; format ascii; class dictionary; object mapFieldsDict; }
patchMap (); cuttingPatches ();
''')
    # Resolve the outlet pressure alias before internalField becomes nonuniform.
    p=case/'0/p'
    text,count=re.subn(r'p0\s+\$internalField;', 'p0 uniform '+str((1 if args.condition=='oxy-1' else 200)*101325)+';',p.read_text())
    if count!=1:raise ValueError('Expected one outlet pressure alias')
    p.write_text(text)
    donor=job/'donor'
    for directory in ['constant','system']:
        shutil.copytree(source/directory,donor/directory)
    for rank in range(8):
        proc='processor'+str(rank)
        shutil.copytree(source/proc/'constant',donor/proc/'constant')
        destination=donor/proc/time;destination.mkdir()
        for name in fields:
            path=source/proc/time/name;target=destination/name
            shutil.copy2(path,target)
            expected=hashes[str(path.relative_to(root))]
            if digest(target)!=expected or digest(path)!=expected:raise ValueError('Changing checkpoint '+str(path))
    (job/'refinement.json').write_text(json.dumps(cfg,indent=2)+'\n')


if __name__=='__main__':main()
