"""Plan/create a fresh single-front case; never alter an existing run."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
FLAMES=HERE.parents[1]/'validation/flames'
sys.path.insert(0,str(FLAMES))
from generate_counterflow import header


def configuration(key):
    cfg=json.loads((HERE/'cases.json').read_text())[key]
    assert isinstance(cfg['cells'],int) and cfg['cells']>=8 and cfg['cells']%4==0
    assert all(math.isfinite(v) and v>0 for v in cfg.values())
    assert .9<=cfg['phi']<=1.4 and cfg['initial_dt_s']<=cfg['max_dt_s']
    assert cfg['max_co']<=.2 and cfg['unburned_temperature_K']==298
    return cfg


def write(path,text):
    with path.open('w',encoding='utf-8',newline='\n') as stream:stream.write(text)


def field(name, values, inlet, dimensions, vector=False):
    kind='volVectorField' if vector else 'volScalarField'
    data='uniform '+str(values) if not isinstance(values,list) else 'nonuniform List<scalar>\n'+str(len(values))+'\n(\n'+'\n'.join(f'{v:.16g}' for v in values)+'\n)'
    return header(name,kind)+f'dimensions [{dimensions}];\ninternalField {data};\nboundaryField {{ left {{ {inlet} }} right {{ type zeroGradient; }} sides {{ type empty; }} }}\n'


def apply(key,output,mode,seeds):
    cfg=configuration(key)
    seed_path=seeds/(key+'.json'); seed=json.loads(seed_path.read_text())
    thermo=FLAMES.parent/'inputs/thermo.inputData_GRI'
    assert seed['NASA7_source_sha256']==hashlib.sha256(thermo.read_bytes()).hexdigest()
    assert seed['phi']==cfg['phi'] and seed['pressure_Pa']==cfg['pressure_Pa']
    assert seed['unburned']['temperature_K']==cfg['unburned_temperature_K']
    for state in ['unburned','burned']:
        y=seed[state]['mass_fractions']
        assert len(y)==53 and all(math.isfinite(v) and 0<=v<=1 for v in y.values())
        assert abs(sum(y.values())-1)<1e-10
    subprocess.run([sys.executable,'-B',str(FLAMES/'generate_premixed.py'),str(FLAMES.parent/'inputs'),str(output),str(cfg['phi'])],check=True)
    n=cfg['cells'];half=n//2; u=seed['unburned'];b=seed['burned']
    fixed=lambda v:f'type fixedValue; value uniform {v:.16g};'
    for name in u['mass_fractions']:
        values=[u['mass_fractions'][name]]*half+[b['mass_fractions'][name]]*half
        write(output/'0'/name,field(name,values,fixed(values[0]),'0 0 0 0 0 0 0'))
    write(output/'0/T',field('T',[u['temperature_K']]*half+[b['temperature_K']]*half,fixed(u['temperature_K']),'0 0 0 1 0 0 0'))
    speed=cfg['inlet_speed_m_s']
    write(output/'0/U',field('U',f'({speed} 0 0)',f'type fixedValue; value uniform ({speed} 0 0);','0 1 -1 0 0 0 0',True))
    p=cfg['pressure_Pa']; length=cfg['length_m']
    write(output/'0/p',header('p','volScalarField')+f'''dimensions [1 -1 -2 0 0 0 0]; internalField uniform {p};
boundaryField {{ left {{ type zeroGradient; }} right {{ type waveTransmissive;
phi phi; psi thermo:psi; gamma 1; fieldInf {p}; lInf {length}; value uniform {p}; }} sides {{ type empty; }} }}
''')
    write(output/'system/blockMeshDict',header('blockMeshDict')+f'''convertToMeters 1;
vertices ((0 0 0) ({length} 0 0) ({length} 1e-5 0) (0 1e-5 0)
(0 0 1e-5) ({length} 0 1e-5) ({length} 1e-5 1e-5) (0 1e-5 1e-5));
blocks (hex (0 1 2 3 4 5 6 7) ({n} 1 1) simpleGrading (1 1 1)); edges ();
boundary (left {{ type patch; faces ((0 4 7 3)); }} right {{ type patch; faces ((1 2 6 5)); }}
sides {{ type empty; faces ((0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); }}); mergePatchPairs ();
''')
    end=2e-6 if mode=='smoke' else cfg['end_time_s']
    interval=end if mode=='smoke' else cfg['write_interval_s']
    write(output/'system/controlDict',header('controlDict')+f'''application rfReactingFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {end}; deltaT {cfg['initial_dt_s']};
adjustTimeStep yes; maxCo {cfg['max_co']}; maxDeltaT {cfg['max_dt_s']};
writeControl adjustableRunTime; writeInterval {interval}; writeFormat ascii; writePrecision 12;
timePrecision 12; purgeWrite 0; runTimeModifiable false;
''')
    write(output/'system/decomposeParDict',header('decomposeParDict')+'numberOfSubdomains 4; method simple; simpleCoeffs { n (4 1 1); delta 0.001; }\n')
    (output/'system/setFieldsDict').unlink()
    (output/'pilot.json').unlink()
    meta={'key':key,'mode':mode,'config':cfg,'ranks':4,'end_time_s':end,'runtime_finalized':False,
          'seed':seed,'seed_sha256':hashlib.sha256(seed_path.read_bytes()).hexdigest(),
          'input_hashes':{f.relative_to(output).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(output.rglob('*')) if f.is_file()}}
    write(output/'case.json',json.dumps(meta,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply']);parser.add_argument('key')
    parser.add_argument('output',type=Path);parser.add_argument('mode',choices=['smoke','full'])
    parser.add_argument('--seeds',type=Path,default=HERE/'seeds');args=parser.parse_args()
    cfg=configuration(args.key)
    if args.output.exists():raise ValueError('Refusing existing output')
    print(json.dumps({'key':args.key,'config':cfg,'mode':args.mode,'seed':str(args.seeds/(args.key+'.json')),'output':str(args.output)}))
    if args.action=='apply':apply(args.key,args.output,args.mode,args.seeds)
