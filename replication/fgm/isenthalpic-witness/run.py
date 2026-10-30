"""Two fresh constant-pressure witnesses with identical requested h/Z/Cwater."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'hybrid-water'))
from states import StateModel,sha,write_json
from tails import integrate
from inputs import load_inputs
from analysis import initialize,pair_report,observables


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['mixing','primary','mechanism']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--mixing-receipt-sha256',required=True)
    parser.add_argument('--source-commit');parser.add_argument('--environment-sha256')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--plan',action='store_true');parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    old,primary,originals,target_h,hashes=load_inputs(args.mixing,args.mixing_receipt_sha256,args.primary,args.mechanism)
    plan={'schema':'isenthalpic-composition-witness/v1','input_hashes':hashes,
        'original_mixing_job_id':old['job_id'],'primary_job_id':primary['job_id'],
        'case_names':[s['recipe']['name'] for s in originals],'common_requested_h_J_kg':target_h,
        'new_fresh_integrations':2,'nominal_Z':originals[0]['recipe']['Z'],'horizon_s':.02,
        'pressure_Pa':primary['extension_settings']['pressure_pa'],'progress_species':['CO2','CO','H2O'],
        'table_modified':False,'scientific_acceptance':False}
    if args.plan:print(json.dumps(plan,indent=2));return 0
    if args.out is None or args.out.exists():raise ValueError('Require a new --out directory')
    if not args.audit_only:
        if not os.environ.get('SLURM_JOB_ID') or not re.fullmatch('[0-9a-f]{40}',args.source_commit or '') or not re.fullmatch('[0-9a-f]{64}',args.environment_sha256 or ''):
            raise ValueError('Physical integration requires allocation and exact source/environment identities')
    import cantera as ct
    if ct.__version__!='3.2.0':raise ValueError('Require Cantera3.2.0')
    runtime_hash=sha(Path(ct._cantera.__file__))
    if not args.audit_only and runtime_hash!=old['cantera_extension_sha256']:raise ValueError('Physical runtime differs from original witness')
    settings=dict(primary['extension_settings'],end_time_s=.02,max_time_step_s=1e-5,max_steps=200000,per_tail_wall_s=30)
    model=StateModel(ct.Solution(str(args.mechanism),transport_model=None),settings)
    if model.gas.species_names!=originals[0]['species_names']:raise ValueError('Mechanism species order differs from original state')
    models={'phase':model.gas.name,'thermo_model':model.gas.thermo_model,
        'kinetics_model':model.gas.kinetics_model,'transport_model':model.gas.transport_model,
        'interpretation':'Ideal-gas GRI bulk kinetics with pressure-derived concentrations; not SRK full chemistry'}
    if models['thermo_model']!='ideal-gas' or models['kinetics_model']!='bulk':
        raise ValueError('Unexpected thermodynamic/kinetic model for the retained witnesses')
    args.out.mkdir(parents=True)
    record={**plan,'job_id':os.environ.get('SLURM_JOB_ID'),'source_commit':args.source_commit,
        'environment_sha256':args.environment_sha256,'cantera_extension_sha256':runtime_hash,
        'runtime_matches_original':runtime_hash==old['cantera_extension_sha256'],'audit_only':args.audit_only,
        'models':models,'settings':settings,'source_hashes':{p.name:sha(p) for p in HERE.glob('*.py')},
        'dependency_hashes':{name:sha(HERE.parent/'hybrid-water'/name) for name in ['states.py','tails.py']},
        'status':'initializing','cases':[]}
    seeds=[];reports=[]
    try:
        for original in originals:
            folder=args.out/original['recipe']['name'];folder.mkdir()
            seed,report=initialize(model,original,target_h)
            write_json(folder/'initial-state.json',report)
            seeds.append(seed);reports.append(report)
        pair=pair_report(model,seeds,reports,plan['nominal_Z'])
        write_json(args.out/'same-coordinate-audit.json',pair)
        if not pair['qualified_equal_coordinates']:raise ValueError('Prepared pair failed same-coordinate checks')
    except Exception as error:
        record.update(status='initialization_failed',error=repr(error))
        (args.out/'traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
        write_json(args.out/'receipt.json',record);return 2
    for original,seed,report in zip(originals,seeds,reports):
        name=original['recipe']['name'];folder=args.out/name
        item={'name':name,'initial_state_sha256':sha(folder/'initial-state.json'),
            'T_K':report['new_T_K'],'h_J_kg':report['achieved_h_J_kg'],'temperature_adjustment_K':report['temperature_adjustment_K'],
            'status':'initial_state_audited'}
        if not args.audit_only:
            try:
                times,rows,metrics=integrate(ct,model,seed,settings,folder)
                metrics.update(observables(times,rows),trajectory_sha256=sha(folder/'chemical-tail.npz'))
                write_json(folder/'physical-receipt.json',metrics)
                item.update(status=metrics['status'],numerically_complete=metrics['numerically_complete'],
                    final_time_s=float(times[-1]),physical_receipt_sha256=sha(folder/'physical-receipt.json'))
            except Exception as error:
                (folder/'traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
                item.update(status='failed',error=repr(error))
        record['cases'].append(item);write_json(args.out/'receipt.json',record)
        print(json.dumps(item),flush=True)
    complete=all(c['status']==('initial_state_audited' if args.audit_only else 'completed') and
                 (args.audit_only or c.get('numerically_complete')) for c in record['cases'])
    record['status']='completed_initial_audit' if args.audit_only and complete else ('completed_diagnostic' if complete else 'failed_diagnostic')
    record['artifacts']={str(p.relative_to(args.out)):sha(p) for p in args.out.rglob('*') if p.is_file() and p.name!='receipt.json'}
    write_json(args.out/'receipt.json',record)
    return 0 if complete else 2


if __name__=='__main__':raise SystemExit(main())
