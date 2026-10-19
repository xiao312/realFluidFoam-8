"""Copy stable ideal checkpoints into isolated diagnostic/continuation cases."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

DONORS={'phi090':'124878341','phi095':'124878481','phi100':'124878268',
        'phi105':'124878510','phi110':'124878193','phi115':'124878594',
        'phi120':'124878305','phi125':'124878625','phi130':'124878627',
        'phi135':'124878634','phi140':'124878676'}
HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(text,key,value):
    text,count=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+str(value)+';',text)
    if count!=1:raise ValueError('Missing or repeated entry '+key)
    return text


def choose_checkpoint(donor,mode):
    if mode=='qualify':return '2.00180632513e-05'
    common=None
    for rank in range(8):
        names=set()
        for p in (donor/f'processor{rank}').iterdir():
            try:value=float(p.name)
            except ValueError:continue
            if p.is_dir() and value>0:names.add(p.name)
        common=names if common is None else common&names
    ordered=sorted(common,key=float)
    if len(ordered)<2:raise ValueError('Need two saved times to avoid active write')
    return ordered[-2]


def prepare(action,job,key,mode,root,restart_authorization=None):
    if not restart_authorization:
        raise ValueError('Intermediate-state restart requires explicit owner authorization; use fresh-start for time-0 runs')
    root=root.resolve();job=job.resolve()
    if job.parent!=root/'jobs':raise ValueError('Expected ROOT/jobs/JOB')
    donor=root/'jobs'/DONORS[key]/'case'
    time=choose_checkpoint(donor,mode)
    anchor=next(r for r in json.loads((HERE.parents[1]/'docs/ideal-temperature-anchors-20261019.json').read_text())['conditions']
                if round(r['phi']*100)==int(key[3:]))
    configs=json.loads((donor/'paper-case.json').read_text())
    if abs(configs['phi']-anchor['phi'])>1e-10:raise ValueError('Anchor/donor phi mismatch')
    thermo=(donor/'constant/thermophysicalProperties').read_text()
    if not all(s in thermo for s in ['idKineticMixture','perfectGas','janaf','sutherlandKinetic']):
        raise ValueError('Expected qualified ideal-gas runtime family')
    duration=1e-7 if mode=='qualify' else max(2e-4-float(time),2e-5)
    end=float(time)+duration
    names=['on','off','reference'] if mode=='qualify' else ['case']
    directories=[Path('constant'),Path('system')]
    for rank in range(8):
        directories.extend([Path(f'processor{rank}/constant'),Path(f'processor{rank}')/time])
        for field in ['T','p','U','rho','OH','CH4','Qdot']:
            if not (donor/f'processor{rank}'/time/field).is_file():raise ValueError('Incomplete checkpoint '+field)
    files=[]
    for directory in directories:
        for path in sorted((donor/directory).rglob('*')):
            if path.is_symlink() or root not in path.resolve().parents:raise ValueError('Unreviewed path')
            if path.is_file():files.append(path)
    controls={'startFrom':'startTime','startTime':time,'endTime':format(end,'.14g'),
        'deltaT':'5e-8','adjustTimeStep':'no' if mode=='qualify' else 'yes',
        'writeControl':'timeStep' if mode=='qualify' else 'runTime',
        'writeInterval':'1' if mode=='qualify' else '1e-5','runTimeModifiable':'no'}
    for name in names:
        if (job/name).exists():raise ValueError('Refusing existing '+name)
    plan={'restart_authorization':restart_authorization,'donor_job':DONORS[key],'checkpoint':time,'cases':names,'controls':controls,
          'phi':anchor['phi'],'temperature_anchor':anchor,'copied_files':len(files),
          'donor_case_source':'128d13ddb4e40c8a539053f22a90fb452738597e'}
    print(json.dumps(plan))
    if action=='plan':return
    for name in names:
        case=job/name;original={}
        for source in files:
            rel=source.relative_to(donor);target=case/rel;target.parent.mkdir(parents=True,exist_ok=True)
            before=digest(source);shutil.copy2(source,target)
            if before!=digest(source) or before!=digest(target):raise ValueError('Donor changed during copy')
            original[str(rel)]=before
        path=case/'system/controlDict';text=path.read_text()
        text=re.sub(r'\nfunctions\s*\{.*\}\s*$', '\n',text,flags=re.S)
        if re.search(r'\bfunctions\b|#include',text):raise ValueError('Unreviewed runtime actions')
        for k,v in controls.items():text=replace(text,k,v)
        path.write_text(text)
        path=case/'constant/flameSpeedProperties'
        path.write_text(replace(path.read_text(),'interval',1 if mode=='qualify' else 10))
        temps=[anchor['temperature_anchor_K']]+anchor['sensitivity_temperatures_K']
        text=('FoamFile { version 2.0; format ascii; class dictionary; object frontTrackingProperties; }\n'
              'enabled '+('false' if name=='off' else 'true')+';\n'
              'interval '+('1' if mode=='qualify' else '10')+'; windowSeconds 5e-6; freshTemperature 298;\n'
              'ohLevels (1e-5 2e-5 3e-5); temperatureLevels ('+' '.join(format(t,'.16g') for t in temps)+');\n')
        (case/'constant/frontTrackingProperties').write_text(text)
        record=dict(plan,original_sha256=original,modified_sha256={str(p.relative_to(case)):digest(p) for p in
            [case/'system/controlDict',case/'constant/flameSpeedProperties',case/'constant/frontTrackingProperties']})
        (case/'tracking-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    (job/'tracking-plan.json').write_text(json.dumps(plan,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','apply'])
    p.add_argument('job',type=Path);p.add_argument('key',choices=list(DONORS));p.add_argument('mode',choices=['qualify','full'])
    p.add_argument('--root',type=Path,default=Path('/work'))
    p.add_argument('--restart-authorization',help='Record the actual explicit owner permission for this restart; never invent it')
    a=p.parse_args();prepare(a.action,a.job,a.key,a.mode,a.root,a.restart_authorization)
