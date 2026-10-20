"""Generate new zero-time paired flames from a screened Cantera reference."""
import argparse
import bisect
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'validation/flames/adaptive'))
from fields import scalar


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(key,profile,results):
    seeds=json.loads((HERE.parent/'ideal-baseline/seeds.json').read_text())
    if key not in seeds:raise ValueError('Unsupported operating condition')
    records=json.loads(results.read_text(encoding='utf-8-sig'))['results']
    matches=[r for r in records if r['stage']==1 and abs(r['phi']-seeds[key]['phi'])<1e-9]
    if len(matches)!=1:raise ValueError('Expected one ideal reference for this condition')
    record=matches[0]
    if record.get('screen_passed') is not True:raise ValueError('Unscreened reference')
    if record.get('pressure_atm',100)!=100:raise ValueError('Only the 100-atm protocol is supported')
    if record['output_sha256']['profile.csv']!=digest(profile):raise ValueError('Reference profile hash mismatch')
    with profile.open(newline='') as stream:
        reader=csv.DictReader(stream);header=reader.fieldnames
        rows=[{k:float(v) for k,v in row.items()} for row in reader]
    names=[k[2:] for k in header if k.startswith('Y_')]
    if len(names)!=53 or set(names)!=set(seeds[key]['unburned']['mass_fractions']):
        raise ValueError('Expected the supported 53-species mechanism')
    if len(rows)<20 or any(not math.isfinite(v) for row in rows for v in row.values()):
        raise ValueError('Incomplete or nonfinite profile')
    if abs(rows[0]['T_K']-298)>1e-6:raise ValueError('Reference must start at 298 K')
    for a,b in zip(rows,rows[1:]):
        if b['x_m']<=a['x_m']:raise ValueError('Nonmonotone reference coordinates')
    for row in rows:
        ys=[row['Y_'+n] for n in names]
        if min(ys)<-1e-9 or max(ys)>1+1e-9 or abs(sum(ys)-1)>1e-7:
            raise ValueError('Invalid reference species')
    flux=[r['rho_kg_m3']*r['U_m_s'] for r in rows]
    if min(flux)<=0 or (max(flux)-min(flux))/flux[0]>1e-3:
        raise ValueError('Reference mass flux is not positive and uniform')
    temperature=.5*(rows[0]['T_K']+rows[-1]['T_K'])
    crossings=[]
    for a,b in zip(rows,rows[1:]):
        if a['T_K']<=temperature<b['T_K']:
            fraction=(temperature-a['T_K'])/(b['T_K']-a['T_K'])
            crossings.append(a['x_m']+fraction*(b['x_m']-a['x_m']))
    if len(crossings)!=1:raise ValueError('Ambiguous half-temperature contour')
    return rows,names,record,crossings[0]


def interpolate(rows,xs,x):
    j=max(0,min(len(rows)-2,bisect.bisect_right(xs,x)-1))
    a,b=rows[j],rows[j+1]
    fraction=max(0.,min(1.,(x-a['x_m'])/(b['x_m']-a['x_m'])))
    return {k:a[k]+fraction*(b[k]-a[k]) for k in a}


def replace_field(path,values,vector=False):
    kind='vector' if vector else 'scalar'
    entries=['('+format(v,'.16g')+' 0 0)' if vector else format(v,'.16g') for v in values]
    field='internalField nonuniform List<'+kind+'>\n'+str(len(values))+'\n(\n'+'\n'.join(entries)+'\n);'
    text,count=re.subn(r'internalField\s+(?:uniform\s+[^;]+|nonuniform\s+List<'+kind+r'>\s+\d+\s*\(.*?\))\s*;',field,path.read_text(),flags=re.S)
    if count!=1:raise ValueError('Expected exactly one internal field: '+str(path))
    path.write_text(text,encoding='utf-8')


def verify(case):
    record=json.loads((case/'cantera-wave-inputs.json').read_text())
    n=record['cells'];names=record['species'];length=record['length_m']
    control=(case/'system/controlDict').read_text()
    def setting(key):
        found=re.findall(r'\b'+key+r'\s+([^;]+);',control)
        if len(found)!=1:raise ValueError('Expected one control '+key)
        return found[0].strip()
    if setting('startFrom')!='startTime' or float(setting('startTime'))!=0:
        raise ValueError('Original-zero start policy is required')
    if abs(float(setting('endTime'))-record['end_time_s'])>1e-12:
        raise ValueError('Endpoint differs from initialization manifest')
    if digest(Path(record['profile_path']))!=record['profile_sha256']:
        raise ValueError('Reference profile changed after preparation')
    for directory in [case,*case.glob('processor[0-9]*')]:
        for path in directory.iterdir():
            if path.is_dir() and re.fullmatch(r'[0-9.eE+-]+',path.name) and float(path.name)!=0:
                raise ValueError('Positive-time directory is forbidden: '+str(path))
    fields={name:scalar(case/'0'/name,n) for name in ['T',*names]}
    for name,values in fields.items():
        if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite '+name)
        limit=1e-8 if name=='T' else 1e-12
        if max(abs(a-b) for a,b in zip(values,reversed(values)))>limit:
            raise ValueError('Asymmetric '+name)
    error=max(abs(sum(fields[name][i] for name in names)-1) for i in range(n))
    if error>1e-12 or min(v for name in names for v in fields[name])<0:
        raise ValueError('Invalid species normalization')
    text=(case/'0/U').read_text()
    body=re.search(r'internalField\s+nonuniform\s+List<vector>\s+\d+\s*\((.*?)\)\s*;',text,re.S)
    velocities=[float(m[0]) for m in re.findall(r'\(([^\s()]+)\s+([^\s()]+)\s+([^\s()]+)\)',body[1])]
    if len(velocities)!=n or not all(math.isfinite(v) for v in velocities) or max(abs(a+b) for a,b in zip(velocities,reversed(velocities)))>1e-12:
        raise ValueError('Velocity is not antisymmetric')
    level=record['half_temperature_K'];crossings=[];temperature=fields['T']
    for i in range(n-1):
        if temperature[i]<=level<temperature[i+1] or temperature[i]>=level>temperature[i+1]:
            crossings.append((i+.5+(level-temperature[i])/(temperature[i+1]-temperature[i]))*length/n)
    expected=[length/2-record['radius_m'],length/2+record['radius_m']]
    if len(crossings)!=2 or any(abs(a-b)>length/n for a,b in zip(crossings,expected)):
        raise ValueError('Unexpected front locations: '+str(crossings))
    print(json.dumps(dict(passed=True,cells=n,species=53,maximum_species_sum_error=error,
        front_locations_m=crossings,initialization='generated_original_zero',scientific_acceptance=False)))


def prepare(args):
    if args.case.exists():raise ValueError('Use a new case directory')
    rows,names,source,anchor=reference(args.key,args.profile,args.results)
    n=8000;length=.004;radius=.0001;xs=[r['x_m'] for r in rows]
    centre=interpolate(rows,xs,anchor+radius)
    record=dict(key=args.key,reference_job=source['job'],reference=source,
        profile_path=str(args.profile.resolve()),profile_sha256=digest(args.profile),
        result_manifest_sha256=digest(args.results),cells=n,length_m=length,radius_m=radius,
        species=names,velocity_recipe=args.velocity,pressure_Pa=10132500,Tu_K=298,
        end_time_s=args.end_us*1e-6,initialization='generated_original_zero',
        reference_speed_m_s=rows[0]['U_m_s'],centre_rest_wave_speed_m_s=centre['U_m_s'],
        half_temperature_K=.5*(rows[0]['T_K']+rows[-1]['T_K']),
        reference_roundoff_negative_species_clipped=True)
    print(json.dumps(record,indent=2))
    if args.action=='plan':return
    spec=importlib.util.spec_from_file_location('fresh_prepare',HERE.parent/'fresh-start/prepare.py')
    fresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(fresh)
    fresh.prepare('apply','energy',args.key,args.case,300)
    values={name:[] for name in ['T','U',*names]}
    for i in range(n//2):
        distance=length/2-(i+.5)*length/n
        state=interpolate(rows,xs,anchor+radius-distance)
        ys=[max(0.,state['Y_'+name]) for name in names];total=sum(ys)
        values['T'].append(state['T_K'])
        values['U'].append(state['U_m_s']-centre['U_m_s'] if args.velocity=='travelling' else 0.)
        for name,value in zip(names,ys):values[name].append(value/total)
    for name,left in values.items():
        full=left+[-v if name=='U' else v for v in reversed(left)]
        replace_field(args.case/'0'/name,full,name=='U')
    for path in [args.case/'fresh-start-inputs.json',args.case/'tracking-inputs.json',args.case.parent/'tracking-plan.json']:
        data=json.loads(path.read_text());data['end_time_s']=record['end_time_s']
        data['initialization_recipe']='screened_cantera_paired_profiles'
        if 'controls' in data:data['controls']['endTime']=format(record['end_time_s'],'.10g')
        path.write_text(json.dumps(data,indent=2)+'\n')
    path=args.case/'system/controlDict';text=path.read_text()
    for key,value in [('endTime',format(record['end_time_s'],'.10g')),('writeInterval','5e-6')]:
        text,count=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text)
        if count!=1:raise ValueError('Unexpected control '+key)
    path.write_text(text)
    (args.case/'cantera-wave-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    (args.case/'initialization-check.json').write_text(json.dumps(record,indent=2)+'\n')
    path=args.case/'paper-case.json';data=json.loads(path.read_text())
    data.update(end_time_s=record['end_time_s'],initialization_recipe='screened_cantera_paired_profiles',
        status='travelling-wave solver diagnostic; not the paper hot-ignition case')
    path.write_text(json.dumps(data,indent=2)+'\n')
    path=args.case/'pilot.json';data=json.loads(path.read_text())
    data.pop('initial_velocity_m_s',None)
    data.update(kernel_shape='mirrored Cantera reference profiles',initial_velocity_recipe=args.velocity,
        kernel_temperature_K=max(values['T']),kernel_width_m=2*radius)
    path.write_text(json.dumps(data,indent=2)+'\n')
    verify(args.case)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='action',required=True)
    check=commands.add_parser('verify');check.add_argument('case',type=Path)
    for action in ['plan','apply']:
        command=commands.add_parser(action);command.add_argument('key')
        for name in ['profile','results','case']:command.add_argument(name,type=Path)
        command.add_argument('--velocity',choices=['travelling','zero'],default='travelling')
        command.add_argument('--end-us',type=int,choices=[20,50,100],default=20)
    args=parser.parse_args()
    if args.action=='verify':verify(args.case)
    else:prepare(args)
