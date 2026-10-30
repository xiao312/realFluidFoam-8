"""Fresh full-chemistry constant-pressure diagnostic of table endpoint coverage."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import time

import numpy as np
from table_state import load, sample, sha256
from diagnostics import analyse


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def make_reactor(ct, mechanism, state, pressure, settings):
    gas = ct.Solution(str(mechanism), transport_model=None)
    assert gas.thermo_model == 'ideal-gas' and set(gas.species_names) == set(state['Y'])
    gas.TPY = state['T_K'], pressure, state['Y']
    reactor = ct.IdealGasConstPressureReactor(gas, clone=True, energy='on', volume=1.0)
    network = ct.ReactorNet([reactor])
    network.rtol = settings['rtol']; network.atol = settings['atol']
    network.max_time_step = settings['max_time_step_s']
    network.max_steps = settings['max_steps']
    return reactor, network


def observe(reactor, physical_time):
    gas = reactor.phase
    rates = gas.net_production_rates*gas.molecular_weights
    indices = [gas.species_index(name) for name in ('CO2','CO','H2O')]
    y = gas.Y
    row = {'time_s':float(physical_time),'T_K':gas.T,'p_Pa':gas.P,
        'rho_kg_m3':gas.density,'h_J_kg':gas.enthalpy_mass,'CpT_J_kg':gas.cp_mass*gas.T,
        'mass_kg':reactor.mass,'volume_m3':reactor.volume,
        'C':float(y[indices[:2]].sum()),'Cwater':float(y[indices].sum()),
        'Sc_kg_m3_s':float(rates[indices[:2]].sum()),'Scwater_kg_m3_s':float(rates[indices].sum()),
        'Qdot_W_m3':gas.heat_release_rate,'minimum_Y':float(y.min()),'sum_Y':float(y.sum())}
    row.update({'element_'+name:gas.elemental_mass_fraction(name) for name in gas.element_names})
    row.update({'Y_'+name:float(y[i]) for i,name in enumerate(gas.species_names)})
    row.update({'omega_'+name+'_kg_m3_s':float(rates[i]) for i,name in enumerate(gas.species_names)})
    assert all(np.isfinite(value) for value in row.values()), 'Nonfinite chemistry or state'
    return row


def integrate(ct, args, state, settings, directory, mode):
    reactor, network = make_reactor(ct,args.mechanism,state,settings['pressure_Pa'],settings)
    initial = observe(reactor,0)
    rows = [initial]
    started = time.monotonic()
    targets = np.unique(np.r_[np.geomspace(1e-12,settings['end_time_s'],settings['observation_points']), 2e-4, settings['end_time_s']])
    if mode == 'accepted':
        targets = None
    with (directory/(mode+'.csv')).open('w',newline='') as output:
        writer = csv.DictWriter(output,fieldnames=list(initial));writer.writeheader();writer.writerow(initial);output.flush()
        index = 0
        while network.time < settings['end_time_s']:
            if len(rows)>settings['max_steps']:
                raise RuntimeError('Accepted/observed state cap reached; partial CSV retained')
            if time.monotonic()-started>settings['wall_per_integration_s']:
                raise TimeoutError('Integration wall limit; partial CSV retained')
            if mode == 'accepted':
                actual = network.step()
            else:
                actual = network.advance(float(targets[index]));index += 1
            assert actual>rows[-1]['time_s'], 'Nonadvancing CVODE time'
            row = observe(reactor,actual);rows.append(row);writer.writerow(row)
            if len(rows)%25==0:output.flush()
    summary = analyse(rows,settings,initial,state['Cmax'])
    summary.update(mode=mode,wall_s=time.monotonic()-started,solver_stats=network.solver_stats,
        sample_semantics='CVODE accepted internal steps' if mode=='accepted' else 'Cantera ReactorNet.advance requested-time observations',
        NASA_temperature_bounds_K=[reactor.phase.min_temp,reactor.phase.max_temp])
    summary['NASA_extrapolation_observed'] = bool(summary['minimum_temperature_K']<reactor.phase.min_temp or summary['maximum_temperature_K']>reactor.phase.max_temp)
    write_json(directory/(mode+'-summary.json'),summary)
    return rows, summary


def equilibrium(ct, args, state, settings):
    reactor,_ = make_reactor(ct,args.mechanism,state,settings['pressure_Pa'],settings)
    gas = reactor.phase
    h0,p0 = gas.enthalpy_mass,gas.P
    gas.equilibrate('HP',solver='auto',rtol=1e-10,max_steps=5000)
    names = ['CO2','CO','H2O'];y = gas.Y
    return {'constraint':'HP at original table-derived ideal-gas enthalpy',
        'initial_h_J_kg':h0,'initial_p_Pa':p0,'T_K':gas.T,'h_J_kg':gas.enthalpy_mass,
        'enthalpy_error_J_kg':gas.enthalpy_mass-h0,'p_Pa':gas.P,
        'C':sum(y[gas.species_index(n)] for n in names[:2]),
        'Cwater':sum(y[gas.species_index(n)] for n in names),
        'Y':dict(zip(gas.species_names,y.tolist())),
        'Qdot_W_m3':gas.heat_release_rate,'scientific_acceptance':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('settings','table','mechanism'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--plan',action='store_true');parser.add_argument('--out',type=Path)
    parser.add_argument('--source-commit');parser.add_argument('--environment-sha256')
    args=parser.parse_args();settings=json.loads(args.settings.read_text())
    assert settings['schema']=='full-chemistry-progress-diagnostic/v1'
    assert sha256(args.table)==settings['table_sha256'] and sha256(args.mechanism)==settings['mechanism_sha256']
    for key in ['pressure_Pa','end_time_s','max_time_step_s','rtol','atol','wall_per_integration_s']:
        assert type(settings[key]) in (int,float) and 0<settings[key]<float('inf'),key
    assert 2e-4<=settings['end_time_s']<=2e-3
    assert type(settings['max_steps']) is int and settings['max_steps']>0
    assert type(settings['observation_points']) is int and settings['observation_points']>=3
    table=load(args.table);states={}
    for point in settings['states']:
        assert re.fullmatch('[a-z0-9-]+',point['name']) and point['name'] not in states
        states[point['name']]=sample(table,point)
    if args.plan:
        print(json.dumps({'read_only':True,'states':states,'settings':settings,'fresh_start':True,'scientific_acceptance':False},indent=2));return 0
    assert os.environ.get('SLURM_JOB_ID'), 'Physical integration requires admitted Slurm allocation'
    assert re.fullmatch('[0-9a-f]{40}',args.source_commit or '') and re.fullmatch('[0-9a-f]{64}',args.environment_sha256 or '')
    assert args.out is not None and not args.out.exists()
    args.out.mkdir(parents=True)
    import cantera as ct
    assert ct.__version__=='3.2.0'
    receipt={'schema':settings['schema'],'status':'started','source_commit':args.source_commit,
        'environment_sha256':args.environment_sha256,'job_id':os.environ['SLURM_JOB_ID'],
        'cantera':ct.__version__,'numpy':np.__version__,'python':os.sys.version,
        'cantera_extension_sha256':sha256(Path(ct._cantera.__file__)),
        'source_files':{p.name:sha256(p) for p in Path(__file__).parent.glob('*.py')},
        'settings_sha256':sha256(args.settings),'table_sha256':sha256(args.table),'mechanism_sha256':sha256(args.mechanism),
        'model':'closed adiabatic ideal-gas constant-pressure reactor, all GRI species, CVODE',
        'initial_h_policy':'derived from interpolated table T/Y with unchanged Cantera NASA coefficients',
        'fresh_start':True,'scientific_acceptance':False,'states':{}}
    write_json(args.out/'receipt.json',receipt)
    for name,state in states.items():
        directory=args.out/name;directory.mkdir();write_json(directory/'initial-table-state.json',state)
        result={'status':'started'};receipt['states'][name]=result
        try:
            endpoint=equilibrium(ct,args,state,settings);write_json(directory/'equilibrium-HP.json',endpoint)
            traces={};summaries={}
            for mode in ('accepted','observations'):
                traces[mode],summaries[mode]=integrate(ct,args,state,settings,directory,mode)
            comparison={}
            accepted=traces['accepted'];observed=traces['observations'];times=[row['time_s'] for row in accepted]
            for key in ('C','Cwater','T_K','h_J_kg'):
                values=[row[key] for row in accepted]
                comparison[key]=max(abs(row[key]-float(np.interp(row['time_s'],times,values))) for row in observed)
            result.update(status='physical_diagnostic_completed',summaries=summaries,
                cross_trace_linear_interpolation_difference=comparison,
                cross_trace_note='Diagnostic only: linear interpolation of accepted states is not CVODE dense interpolation.',
                numerical_checks_passed=all(s['requested_time_covered'] and s['conservation_passed'] for s in summaries.values()))
        except Exception as error:
            result.update(status='failed',error_type=type(error).__name__,error=str(error))
        write_json(directory/'summary.json',result);write_json(args.out/'receipt.json',receipt)
    receipt['status']='completed' if all(row.get('numerical_checks_passed') for row in receipt['states'].values()) else 'failed_or_unqualified'
    receipt['artifacts']={str(p.relative_to(args.out)):sha256(p) for p in args.out.rglob('*') if p.is_file() and p.name!='receipt.json'}
    write_json(args.out/'receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'states':{k:v['status'] for k,v in receipt['states'].items()},'scientific_acceptance':False}))
    return 0 if receipt['status']=='completed' else 1


if __name__=='__main__':
    raise SystemExit(main())
