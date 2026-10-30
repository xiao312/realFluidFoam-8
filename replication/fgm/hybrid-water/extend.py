"""Fresh long-horizon reactors only for actual positive source caps; no CFD restarts."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import time
import traceback

import numpy as np
from states import StateModel,C,T,H,RHO,SC,Q,sha,write_json
from tails import build_branch
from tabulate import build,write_table
from endpoints import represent


def checkpoints(folder):
    with np.load(folder/'chemical-tail.npz') as archive:
        times,states=archive['time_s'],archive['states']
    result=[]
    for request in [.0002,.002,.02]:
        index=int(np.searchsorted(times,request))
        if index>=len(times):
            result.append({'requested_time_s':request,'available':False});continue
        row=states[index]
        result.append({'requested_time_s':request,'actual_accepted_time_s':float(times[index]),
            'available':True,'Cwater':float(row[C]),'T_K':float(row[T]),
            'h_J_kg':float(row[H]),'Scwater_kg_m3_s':float(row[SC]),'Qformation_W_m3':float(row[Q])})
    return result


def compare_steps(coarse,fine,model):
    with np.load(coarse/'chemical-tail.npz') as archive:
        tc,vc=archive['time_s'],archive['states']
    with np.load(fine/'chemical-tail.npz') as archive:
        tf,vf=archive['time_s'],archive['states']
    end=min(tc[-1],tf[-1],.02)
    times=np.r_[0,np.geomspace(1e-12,end,400)]
    fields=[C,T,H,SC,Q]+list(range(model.ys.start,model.ys.stop))
    names=['Cwater','T_K','h_J_kg','Scwater_kg_m3_s','Qformation_W_m3']+['Y_'+n for n in model.gas.species_names]
    a=np.stack([np.interp(times,tc,vc[:,k]) for k in fields],axis=1)
    b=np.stack([np.interp(times,tf,vf[:,k]) for k in fields],axis=1)
    result={'scope':'Same fresh seed, retained accepted physical trajectories interpolated in time; no scientific pass threshold',
            'coarse_max_step_s':1e-5,'fine_max_step_s':2.5e-6,'comparison_end_s':float(end),'fields':{}}
    for k,name in enumerate(names):
        difference=a[:,k]-b[:,k];peak=float(np.max(np.abs(b[:,k])))
        result['fields'][name]={'max_absolute':float(np.max(np.abs(difference))),
            'rms':float(np.sqrt(np.mean(difference**2))),'fine_global_peak':peak,
            'rms_over_fine_global_peak':float(np.sqrt(np.mean(difference**2))/peak) if peak else None,
            'final_difference':float(difference[-1])}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','raw-dir','settings','mechanism']:
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--input-receipt-sha256',required=True)
    parser.add_argument('--source-commit')
    parser.add_argument('--environment-sha256')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--plan',action='store_true')
    args=parser.parse_args()
    assert sha(args.input/'receipt.json')==args.input_receipt_sha256
    original=json.loads((args.input/'receipt.json').read_text())
    settings=json.loads(args.settings.read_text())
    assert sha(args.settings)==original['settings_sha256']
    assert sha(args.mechanism)==settings['mechanism_sha256']
    assert original['status']=='tabulation_failed' and len(original['cases'])==129
    assert sha(args.raw_dir/'trajectory.npz')==settings['input_trajectory_sha256']
    assert sha(args.raw_dir/'receipt.json')==settings['input_receipt_sha256']
    assert sha(args.input/'phase-metadata.json')==original['metadata_sha256']
    with np.load(args.raw_dir/'trajectory.npz') as archive:
        raw={name:archive[name] for name in archive.files}
    branches,reports,inputs={}, {},{}
    for case in original['cases']:
        j=case['Z_index'];folder=args.input/f'z-{j:03d}'
        assert sha(folder/'branch.npz')==case['branch_sha256']
        assert sha(folder/'tail-receipt.json')==case['receipt_sha256']
        inputs[str(j)]={'branch_sha256':case['branch_sha256'],'receipt_sha256':case['receipt_sha256']}
        with np.load(folder/'branch.npz') as archive: branches[j]=archive['states'].copy()
        reports[j]=json.loads((folder/'tail-receipt.json').read_text())
        assert reports[j]['numerically_complete']
    selected=[case['Z_index'] for case in original['cases'] if case['cap_Scwater']>0]
    assert selected and all(0<j<128 for j in selected)
    spot=107
    assert spot in selected
    long_settings=dict(settings,end_time_s=.02,max_time_step_s=1e-5,per_tail_wall_s=20,max_steps=200000)
    plan={'physical_source':original['source_commit'],'physical_job_id':original['job_id'],
        'input_receipt_sha256':args.input_receipt_sha256,'selected_positive_cap_indices':selected,
        'spot_comparison_Z_index':spot,'end_time_s':.02,'intermediate_audit_s':.002,
        'rtol':settings['rtol'],'atol':settings['atol'],'max_step_s':1e-5,'spot_max_step_s':2.5e-6,
        'initialization':'Each integration starts fresh at the unchanged original physical quench seed',
        'input_branches':inputs,'CFD_restart':False,'scientific_acceptance':False}
    if args.plan:
        print(json.dumps(plan,indent=2));return 0
    assert os.environ.get('SLURM_JOB_ID') and re.fullmatch('[0-9a-f]{40}',args.source_commit or '')
    assert re.fullmatch('[0-9a-f]{64}',args.environment_sha256 or '')
    assert args.out is not None and not args.out.exists()
    args.out.mkdir(parents=True)
    import cantera as ct
    assert ct.__version__=='3.2.0' and sha(Path(ct._cantera.__file__))==settings['cantera_extension_sha256']
    model=StateModel(ct.Solution(str(args.mechanism),transport_model=None),long_settings)
    receipt=dict(original)
    for key in ['error','artifacts','cases']: receipt.pop(key,None)
    receipt.update(status='fresh_long_tails_running',source_commit=args.source_commit,
        job_id=os.environ['SLURM_JOB_ID'],environment_sha256=args.environment_sha256,
        previous_physical_source_commit=original['source_commit'],previous_physical_job_id=original['job_id'],
        original_receipt_sha256=args.input_receipt_sha256,extension_settings=long_settings,
        new_fresh_integrations=len(selected)+1,cases=[],scientific_acceptance=False)
    start=time.monotonic()
    write_json(args.out/'inputs.json',plan)
    shutil.copyfile(args.input/'phase-metadata.json',args.out/'phase-metadata.json')
    failed=[]
    for case in original['cases']:
        j=case['Z_index'];result=dict(case)
        result['physical_source_commit']=original['source_commit']
        result['physical_job_id']=original['job_id']
        result['physical_relative_path']=f'z-{j:03d}'
        result['retained_original_branch']=j not in selected
        if j in selected:
            folder=args.out/f'z-{j:03d}';folder.mkdir()
            try:
                branch,report=build_branch(model,raw,j,long_settings,folder,ct)
                assert report['seed_index']==reports[j]['seed_index'], 'Fresh seed selection changed'
                branches[j],reports[j]=branch,report
                result.update(status=report['status'],numerically_complete=report['numerically_complete'],
                    physical_source_commit=args.source_commit,physical_job_id=os.environ['SLURM_JOB_ID'],
                    cap_Cwater=float(branch[-1,C]),cap_Scwater=float(branch[-1,SC]),
                    checkpoints=checkpoints(folder),branch_sha256=sha(folder/'branch.npz'),receipt_sha256=sha(folder/'tail-receipt.json'))
            except Exception as error:
                (folder/'traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
                result.update(status='failed',error=repr(error));failed.append(j)
        receipt['cases'].append(result)
        write_json(args.out/'receipt.json',receipt)
        if j in selected: print(json.dumps(result),flush=True)
    # One independently fresh tighter-step physical trajectory, not a synthetic test.
    spot_folder=args.out/'spot-tighter-step';spot_folder.mkdir()
    try:
        fine_settings=dict(long_settings,max_time_step_s=2.5e-6)
        _,spot_report=build_branch(model,raw,spot,fine_settings,spot_folder,ct)
        assert spot_report['seed_index']==reports[spot]['seed_index']
        comparison=compare_steps(args.out/f'z-{spot:03d}',spot_folder,model)
        comparison['status']='completed';comparison['Z_index']=spot
        write_json(args.out/'step-comparison.json',comparison)
    except Exception as error:
        (spot_folder/'traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
        write_json(args.out/'step-comparison.json',{'status':'failed','error':repr(error),'scientific_acceptance':False})
    receipt['failed_extension_Z_indices']=failed
    if failed:
        receipt.update(status='incomplete_physical_extension',elapsed_s=time.monotonic()-start)
        write_json(args.out/'receipt.json',receipt);return 2
    try:
        representation=represent(model,branches,raw['Z'])
        write_json(args.out/'endpoint-representation.json',representation)
        axis,eta,limits,values,diagnostics=build(model,branches,reports,raw['Z'],settings,args.out)
        write_table(args.out/'physical.tbl',model,axis,eta,limits,values,args.source_commit,sha(args.out/'inputs.json'))
        receipt.update(status='diagnostic_table_exported_not_accepted',
            all_source_caps_inward=not diagnostics['outward_upper_nodes'] and not diagnostics['outward_lower_nodes'],
            full_progress_coverage_qualified=False)
    except Exception as error:
        (args.out/'tabulation-traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
        receipt.update(status='tabulation_failed',error=repr(error))
    receipt.update(elapsed_s=time.monotonic()-start,
        artifacts={p.name:sha(p) for p in args.out.iterdir() if p.is_file() and p.name!='receipt.json'})
    write_json(args.out/'receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'elapsed_s':receipt['elapsed_s'],'scientific_acceptance':False}))
    return 0 if receipt['status']=='diagnostic_table_exported_not_accepted' else 3


if __name__=='__main__':
    raise SystemExit(main())
