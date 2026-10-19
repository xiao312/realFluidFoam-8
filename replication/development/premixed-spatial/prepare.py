"""Copy completed checkpoints from the active donor; never modify donor files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

TIMES=['2.00025485065e-05','3.99834968798e-05','5.99834968798e-05','7.99834968798e-05']


def prepare(action,job):
    root=Path('/work').resolve();job=job.resolve()
    if root not in job.parents or job.parent.name!='jobs':raise ValueError('Expected contained job directory')
    donor=root/'jobs/124864929/case'
    cases=[('on'+str(i),time) for i,time in enumerate(TIMES)]+[('off0',TIMES[0])]
    print(json.dumps({'donor':str(donor),'output':str(job),'cases':cases,'step_s':1e-7}))
    for name,time in cases:
        if (job/name).exists():raise ValueError('Refusing existing replay '+name)
        for rank in range(8):
            if not (donor/f'processor{rank}'/time/'T').is_file():raise ValueError('Incomplete checkpoint '+time)
    if action=='plan':return
    receipt={}
    for name,time in cases:
        case=job/name;hashes={}
        relative=[Path('constant'),Path('system')]
        for rank in range(8):relative += [Path(f'processor{rank}/constant'),Path(f'processor{rank}')/time]
        for directory in relative:
            for source in sorted((donor/directory).rglob('*')):
                if source.is_symlink():raise ValueError('Unreviewed symlink')
                if not source.is_file():continue
                rel=source.relative_to(donor);dest=case/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
                original=digest(source);shutil.copy2(source,dest)
                if digest(dest)!=original or digest(source)!=original:raise ValueError('Checkpoint changed '+str(rel))
                hashes[str(rel)]=original
        path=case/'system/controlDict';text=path.read_text()
        text=re.sub(r'\nfunctions\s*\{.*\}\s*$', '\n',text,flags=re.S)
        if re.search(r'\bfunctions\b|#include',text):raise ValueError('Unreviewed runtime actions')
        controls={'startFrom':'startTime','startTime':time,'endTime':format(float(time)+1e-7,'.12g'),
                  'deltaT':'1e-7','adjustTimeStep':'no','writeControl':'timeStep','writeInterval':'1'}
        for key,value in controls.items():
            text,n=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text)
            if n!=1:raise ValueError('Missing/repeated control '+key)
        path.write_text(text)
        path=case/'constant/flameSpeedProperties';text=path.read_text()
        text,n=re.subn(r'\binterval\s+[^;]+;','interval 1;',text)
        if n!=1:raise ValueError('Missing diagnostic interval')
        path.write_text(text)
        receipt[name]={'time':time,'end_time':controls['endTime'],'original_sha256':hashes,
                       'controls':controls,'diagnostic_interval':1,'runtime_functions_removed':True}
    (job/'checkpoint-inputs.json').write_text(json.dumps(receipt,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','apply']);p.add_argument('job',type=Path)
    a=p.parse_args();prepare(a.action,a.job)
