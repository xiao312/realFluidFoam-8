"""Four physical mixing seeds and fresh adiabatic full-chemistry witnesses."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import traceback
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hybrid-water'))
from states import StateModel,C,T,H,RHO,SC,Q,sha,write_json
from tails import integrate
from mixing import seeds,compare,lookup


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--input-receipt-sha256',required=True)
    parser.add_argument('--mechanism',required=True,type=Path)
    parser.add_argument('--source-commit')
    parser.add_argument('--environment-sha256')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--plan',action='store_true')
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    assert sha(args.input/'receipt.json')==args.input_receipt_sha256
    original=json.loads((args.input/'receipt.json').read_text())
    assert original['status']=='diagnostic_table_exported_not_accepted'
    assert original['progress_species']==['CO2','CO','H2O']
    assert sha(args.input/'table.npz')==original['artifacts']['table.npz']
    assert sha(args.input/'phase-metadata.json')==original['metadata_sha256']
    assert sha(args.mechanism)==original['mechanism_sha256']
    with np.load(args.input/'table.npz') as archive:data={k:archive[k] for k in archive.files}
    points,recipes=seeds(data)
    plan={'input_receipt_sha256':args.input_receipt_sha256,'input_table_sha256':sha(args.input/'table.npz'),
        'source_job_id':original['job_id'],'recipes':recipes,'new_physical_trajectories':4,
        'maximum_horizon_s':.02,'bounds_modified':False,'scientific_acceptance':False}
    if args.plan:
        print(json.dumps(plan,indent=2));return 0
    assert args.out is not None and not args.out.exists()
    if not args.audit_only:
        assert os.environ.get('SLURM_JOB_ID') and re.fullmatch('[0-9a-f]{40}',args.source_commit or '')
        assert re.fullmatch('[0-9a-f]{64}',args.environment_sha256 or '')
    import cantera as ct
    assert ct.__version__=='3.2.0'
    runtime_hash=sha(Path(ct._cantera.__file__))
    if not args.audit_only:assert runtime_hash==original['cantera_extension_sha256']
    args.out.mkdir(parents=True)
    settings=dict(original['extension_settings'],end_time_s=.02,max_time_step_s=1e-5,per_tail_wall_s=20,max_steps=200000)
    model=StateModel(ct.Solution(str(args.mechanism),transport_model=None),settings)
    record={**plan,'schema':'physical-mixing-witness/v1','source_commit':args.source_commit,
        'environment_sha256':args.environment_sha256,'job_id':os.environ.get('SLURM_JOB_ID'),
        'audit_only':args.audit_only,'cantera_extension_sha256':runtime_hash,
        'physical_runtime_matches_linux':runtime_hash==original['cantera_extension_sha256'],
        'source_files':{p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},
        'dependency_files':{name:sha(Path(__file__).resolve().parents[1]/'hybrid-water'/name) for name in ['states.py','tails.py']},'cases':[]}
    initial=[]
    for recipe in recipes:
        folder=args.out/recipe['name'];folder.mkdir()
        item={**recipe,'status':'initializing'}
        try:
            weights=recipe['weights']
            y=sum(weight*points[key][1][model.ys] for key,weight in weights.items())
            enthalpy=sum(weight*points[key][1][H] for key,weight in weights.items())
            expected_elements=y@model.elements
            expected_c=float(y[model.progress].sum())
            row,audit=model.at_hy(enthalpy,y)
            assert abs(row[C]-expected_c)<1e-12
            assert np.max(np.abs(row[model.ys]@model.elements-expected_elements))<1e-12
            seed={'recipe':recipe,'mass_fraction_sum_before':float(y.sum()),'requested_h_J_kg':float(enthalpy),
                'computed_h_J_kg':float(row[H]),'Cwater':float(row[C]),'T_K':float(row[T]),
                'source_states':{key:{'Z':points[key][0],'state':points[key][1].tolist()} for key in weights},
                'state':row.tolist(),'species_names':model.gas.species_names,'representation':audit,
                'initial_table_comparison':compare(data,recipe['Z'],row[None,:],model.ys)}
            write_json(folder/'initial-state.json',seed)
            initial.append((recipe,row))
            item.update(status='initial_state_audited',T_K=float(row[T]),Cwater=float(row[C]),
                h_J_kg=float(row[H]),initial_source_kg_m3_s=float(row[SC]),
                initial_state_sha256=sha(folder/'initial-state.json'))
            if not args.audit_only:
                times,rows,metrics=integrate(ct,model,row,settings,folder)
                delta=np.diff(rows[:,C])
                metrics.update(progress_min=float(rows[:,C].min()),progress_max=float(rows[:,C].max()),
                    progress_up_steps=int(np.count_nonzero(delta>1e-9)),progress_down_steps=int(np.count_nonzero(delta<-1e-9)),
                    same_coordinate_table_comparison=compare(data,recipe['Z'],rows,model.ys),
                    trajectory_sha256=sha(folder/'chemical-tail.npz'))
                write_json(folder/'physical-receipt.json',metrics)
                item.update(status=metrics['status'],numerically_complete=metrics['numerically_complete'],
                    final_time_s=float(times[-1]),final_Cwater=float(rows[-1,C]),final_T_K=float(rows[-1,T]),
                    physical_receipt_sha256=sha(folder/'physical-receipt.json'))
        except Exception as error:
            (folder/'traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
            item.update(status='failed',error=repr(error))
        record['cases'].append(item)
        write_json(args.out/'receipt.json',record)
        print(json.dumps(item),flush=True)
    if len(initial)==4:
        a,b=initial[2][1],initial[3][1]
        assert abs(a[C]-b[C])<1e-12
        write_json(args.out/'same-ZC-initial-difference.json',{
            'Z':recipes[2]['Z'],'Cwater':float(a[C]),'delta_Cwater':float(a[C]-b[C]),
            'delta_h_J_kg':float(a[H]-b[H]),'delta_T_K':float(a[T]-b[T]),
            'maximum_species_difference':float(np.max(np.abs(a[model.ys]-b[model.ys]))),
            'species_differences':dict(zip(model.gas.species_names,(a[model.ys]-b[model.ys]).tolist())),
            'delta_Scwater_kg_m3_s':float(a[SC]-b[SC]),'delta_Qformation_W_m3':float(a[Q]-b[Q]),
            'scientific_acceptance':False})
    complete=all(c.get('status')==('initial_state_audited' if args.audit_only else 'completed') and
                 (args.audit_only or c.get('numerically_complete')) for c in record['cases'])
    record['status']='completed_diagnostic' if complete else 'failed_diagnostic'
    record['artifacts']={p.name:sha(p) for p in args.out.iterdir() if p.is_file() and p.name!='receipt.json'}
    write_json(args.out/'receipt.json',record)
    return 0 if complete else 2


if __name__=='__main__':
    raise SystemExit(main())
