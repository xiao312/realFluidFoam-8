"""Generate original initial fields; refuse intermediate-state continuation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def entry(text,key):
    values=re.findall(r'\b'+key+r'\s+([^;]+);',text)
    if len(values)!=1: raise ValueError('Expected one '+key)
    return values[0].strip()


def verify(family,case):
    control=(case/'system/controlDict').read_text()
    if entry(control,'startFrom')!='startTime' or float(entry(control,'startTime'))!=0:
        raise ValueError('Owner policy requires startFrom=startTime and startTime=0')
    ranks=int(entry((case/'system/decomposeParDict').read_text(),'numberOfSubdomains'))
    if ranks not in (8,32):raise ValueError('Unqualified MPI rank count')
    expected={'processor'+str(i) for i in range(ranks)}
    actual={p.name for p in case.glob('processor[0-9]*') if p.is_dir()}
    if actual!=expected:raise ValueError('Processor directories differ from declared decomposition')
    for directory in [case]+[case/('processor'+str(i)) for i in range(ranks)]:
        if not (directory/'0').is_dir(): raise ValueError('Missing original zero fields: '+str(directory))
        for p in directory.iterdir():
            if not p.is_dir(): continue
            try: time=float(p.name)
            except ValueError: continue
            if time!=0: raise ValueError('Saved-time directory is forbidden: '+str(p))
        for field in ('T','p','U','CH4','O2','N2','OH'):
            if not (directory/'0'/field).is_file(): raise ValueError('Missing initial field '+field)
    config=json.loads((case/'fresh-start-inputs.json').read_text())
    if config['initialization']!='generated_original_zero' or config['family']!=family:
        raise ValueError('Initial-state provenance mismatch')
    if abs(float(entry(control,'endTime'))-config['end_time_s'])>1e-12:
        raise ValueError('Endpoint differs between controls and provenance')
    hashes={str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest()
            for name in ('0','constant','system') for p in sorted((case/name).rglob('*')) if p.is_file()}
    physics=dict(hashes)
    normalized=re.sub(r'\bapplication\s+[^;]+;','application SOLVER;',control)
    physics['system/controlDict']=hashlib.sha256(normalized.encode()).hexdigest()
    config.update(initial_file_sha256=hashes,
        physical_input_sha256=hashlib.sha256(json.dumps(physics,sort_keys=True).encode()).hexdigest(),
        verified_start_time_s=0,positive_time_directories=0,mpi_ranks=ranks)
    (case/'fresh-start-inputs.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(config,indent=2))


def prepare(action,family,key,case,end_us=200):
    seeds=json.loads((HERE.parent/'ideal-baseline/seeds.json').read_text())
    if key not in seeds or end_us not in (200,300,400): raise ValueError('Unsupported case or endpoint')
    if case.exists(): raise ValueError('Refusing existing case')
    config=dict(family=family,key=key,phi=seeds[key]['phi'],initialization='generated_original_zero',
                start_time_s=0,end_time_s=end_us*1e-6,restart_authorization=None)
    print(json.dumps(config,indent=2))
    if action=='plan': return
    subprocess.run([sys.executable,'-B',str(HERE.parent/'ideal-baseline/prepare.py'),
                    'apply',key,str(case),'full'],check=True)
    anchor=next(r for r in json.loads((HERE.parents[1]/'docs/ideal-temperature-anchors-20261019.json').read_text())['conditions']
                if abs(r['phi']-config['phi'])<1e-9)
    solver='rfTrackedReactingFoam' if family=='native' else 'rfEnergyReactingFoam'
    path=case/'system/controlDict';control=path.read_text()
    if entry(control,'startFrom')!='startTime' or float(entry(control,'startTime'))!=0:
        raise ValueError('Generator no longer provides original initialization')
    control=re.sub(r'\bapplication\s+[^;]+;','application '+solver+';',control)
    control=re.sub(r'\bendTime\s+[^;]+;','endTime '+format(config['end_time_s'],'.10g')+';',control)
    path.write_text(control)
    temperatures=[anchor['temperature_anchor_K']]+anchor['sensitivity_temperatures_K']
    (case/'constant/frontTrackingProperties').write_text(
        'FoamFile {version 2.0; format ascii; class dictionary; object frontTrackingProperties;}\n'
        'enabled true; interval 10; windowSeconds 5e-6; freshTemperature 298;\n'
        'ohLevels (1e-5 2e-5 3e-5); temperatureLevels ('+
        ' '.join(format(t,'.16g') for t in temperatures)+');\n')
    path=case/'constant/flameSpeedProperties'
    path.write_text(re.sub(r'\binterval\s+[^;]+;','interval 10;',path.read_text()))
    config['temperature_anchor']=anchor
    (case/'fresh-start-inputs.json').write_text(json.dumps(config,indent=2)+'\n')
    plan=dict(config,checkpoint='0',cases=['case'],controls={'startTime':'0','endTime':format(config['end_time_s'],'.10g')})
    (case/'tracking-inputs.json').write_text(json.dumps(plan,indent=2)+'\n')
    (case.parent/'tracking-plan.json').write_text(json.dumps(plan,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply','verify'])
    parser.add_argument('family',choices=['native','energy'])
    parser.add_argument('key_or_case')
    parser.add_argument('case',nargs='?',type=Path)
    parser.add_argument('--end-us',type=int,choices=[200,300,400],default=200)
    args=parser.parse_args()
    if args.action=='verify': verify(args.family,Path(args.key_or_case))
    else:
        if args.case is None: parser.error('NEW_CASE is required')
        prepare(args.action,args.family,args.key_or_case,args.case,args.end_us)
