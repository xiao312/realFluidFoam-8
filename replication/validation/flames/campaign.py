"""Validate or generate a bounded convergence case using unchanged pilot physics."""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from generate_counterflow import header


def validate(config):
    allowed={'case','radial_cells','axial_cells','delta_t_s','end_time_s','write_interval_steps','ranks','wall_minutes','phi','length_m','kernel_width_m','restart_job','initialization','linear_relative_tolerance'}
    if set(config)-allowed:raise ValueError('Unknown configuration fields: '+str(set(config)-allowed))
    for key in ('axial_cells','ranks','wall_minutes','write_interval_steps'):
        if type(config.get(key)) is not int or config[key]<1:raise ValueError('Positive integer required: '+key)
    for key in ('delta_t_s','end_time_s'):
        if not isinstance(config.get(key),(int,float)) or not math.isfinite(config[key]) or config[key]<=0:raise ValueError('Positive finite value required: '+key)
    if 'restart_job' in config and (type(config['restart_job']) is not int or config['restart_job']<=0):raise ValueError('Positive restart job ID required')
    if config['delta_t_s']>config['end_time_s']:raise ValueError('Timestep exceeds duration')
    if config['case'] not in ('oxy-1','oxy-200','air-100','premixed'):raise ValueError('Unsupported case')
    if config['case']=='premixed':
        if not .9<=config.get('phi',0)<=1.4:raise ValueError('Phi outside paper sweep')
        if not 0<config.get('kernel_width_m',0)<config.get('length_m',0):raise ValueError('Kernel must fit inside domain')
        cells=config['axial_cells']
    else:
        if type(config.get('radial_cells')) is not int or config['radial_cells']<1:raise ValueError('Positive radial cell count required')
        cells=config['radial_cells']*config['axial_cells']
    if config['axial_cells']%config['ranks']:raise ValueError('Axial cells must divide evenly among ranks')
    if 'linear_relative_tolerance' in config:
        value=config['linear_relative_tolerance']
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<1:raise ValueError('Linear relative tolerance must be in [0, 1)')
    if 'initialization' in config:
        init=config['initialization']
        if config['case']=='premixed' or 'restart_job' in config:raise ValueError('Localized counterflow initialization requires a fresh counterflow case')
        if set(init)!={'mode','mixing_width_fraction','ignition_width_fraction','ignition_temperature_K','strain_flow'} or init['mode']!='localized':raise ValueError('Invalid initialization schema')
        for name in ['mixing_width_fraction','ignition_width_fraction']:
            if not 0<init[name]<.25:raise ValueError('Initialization width must be in (0, .25)')
        if not 1000<init['ignition_temperature_K']<3000 or type(init['strain_flow']) is not bool:raise ValueError('Invalid ignition temperature or flow flag')
    return cells


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply']);parser.add_argument('config',type=Path)
    parser.add_argument('inputs',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();cfg=json.loads(args.config.read_text());cells=validate(cfg)
    print(json.dumps(dict(configuration=cfg,cells=cells,maximum_allocated_core_hours=cfg['ranks']*cfg['wall_minutes']/60,
                         output=str(args.output.resolve()),scientific_status='planned; not validated'),indent=2))
    if args.action=='plan':return
    case=args.output.resolve()
    if case.exists():raise ValueError('Refusing existing case: '+str(case))
    script='generate_premixed.py' if cfg['case']=='premixed' else 'generate_counterflow.py'
    selector=str(cfg['phi']) if cfg['case']=='premixed' else cfg['case']
    subprocess.run([sys.executable,'-B',str(Path(__file__).with_name(script)),str(args.inputs),str(case),selector],check=True)
    def write(name,text):
        with (case/name).open('w',newline='\n') as stream:stream.write(text)
    mesh=(case/'system/blockMeshDict').read_text()
    if cfg['case']=='premixed':
        length=cfg['length_m'];half=length/2;kernel=cfg['kernel_width_m']
        mesh=mesh.replace('convertToMeters 0.001','convertToMeters 1')
        mesh=mesh.replace('(2 ',f'({length} ').replace('0.01','0.00001')
        mesh=mesh.replace('(200 1 1)',f"({cfg['axial_cells']} 1 1)")
        field=(case/'system/setFieldsDict').read_text()
        field=field.replace('0.0009',str(half-kernel/2)).replace('0.0011',str(half+kernel/2))
        write('system/setFieldsDict',field)
        write('0/p',(case/'0/p').read_text().replace('lInf 0.002',f'lInf {length}'))
        decomposition=f"({cfg['ranks']} 1 1)"
    else:
        mesh=mesh.replace('(8 1 40)',f"({cfg['radial_cells']} 1 {cfg['axial_cells']})")
        decomposition=f"(1 1 {cfg['ranks']})"
    write('system/blockMeshDict',mesh)
    control=(case/'system/controlDict').read_text()
    for key,value in [('endTime',cfg['end_time_s']),('deltaT',cfg['delta_t_s']),('writeInterval',cfg['write_interval_steps'])]:
        control,n=re.subn(r'\b'+key+r'\s+[^;]+;',f'{key} {value};',control)
        if n!=1:raise ValueError('Ambiguous control: '+key)
    write('system/controlDict',control)
    if 'linear_relative_tolerance' in cfg:
        solution=(case/'system/fvSolution').read_text()
        if solution.count('relTol 0.1;')!=2:raise ValueError('Unexpected baseline linear solver settings')
        write('system/fvSolution',solution.replace('relTol 0.1;',f"relTol {cfg['linear_relative_tolerance']};"))
    write('system/decomposeParDict',header('decomposeParDict')+f"numberOfSubdomains {cfg['ranks']};\nmethod simple;\nsimpleCoeffs {{ n {decomposition}; delta 0.001; }}\n")
    metadata=json.loads((case/'pilot.json').read_text());metadata.update(cells=cells,status='convergence development; scientific validation pending')
    if cfg['case']=='premixed':metadata.update(length_m=length,spacing_m=length/cells,kernel_width_m=kernel)
    write('pilot.json',json.dumps(metadata,indent=2)+'\n');write('campaign.json',json.dumps(cfg,indent=2)+'\n')

if __name__=='__main__':main()
