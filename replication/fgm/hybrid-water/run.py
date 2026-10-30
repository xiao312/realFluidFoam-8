"""Allocated physical chemical tails and explicit approximate manifold derivation."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('raw-dir','settings','mechanism'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--plan',action='store_true')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--source-commit')
    parser.add_argument('--environment-sha256')
    args = parser.parse_args()
    settings = json.loads(args.settings.read_text())
    assert settings['schema'] == 'hybrid-water-experiment/v1'
    for key in ('pressure_pa','seed_target_temperature_k','end_time_s','max_time_step_s','rtol','atol','per_tail_wall_s'):
        assert type(settings[key]) in (float,int) and 0 < settings[key] < float('inf'), key
    assert settings['end_time_s'] <= .002 and settings['per_tail_wall_s'] <= 30
    assert settings['progress_species'] == ['CO2','CO','H2O']
    for key in ('eta_points','heldout_eta_points'):
        assert type(settings[key]) is int and 3 <= settings[key] <= 401, key
    for name,key in [('receipt.json','input_receipt_sha256'),('trajectory.npz','input_trajectory_sha256'),('phase-metadata.json','input_metadata_sha256')]:
        assert sha(args.raw_dir/name) == settings[key], 'Input identity mismatch: '+name
    assert sha(args.mechanism) == settings['mechanism_sha256']
    with np.load(args.raw_dir/'trajectory.npz') as archive:
        raw = {name: archive[name] for name in archive.files}
    original = json.loads((args.raw_dir/'receipt.json').read_text())
    assert len(raw['Z']) == 129 and raw['Z'][0] == 0 and raw['Z'][-1] == 1
    assert np.isfinite(raw['Y']).all() and np.isfinite(raw['T_K']).all()
    assert settings['pressure_pa'] == float(raw['pressure_pa']) == original['case']['pressure_pa']
    if args.plan:
        print(json.dumps({'read_only':True,'training_Z':65,'heldout_Z':64,'settings':settings,
            'original_source':original['source_commit'],'new_physical_tails':127,'table_replacement':False},indent=2))
        return 0
    assert os.environ.get('SLURM_JOB_ID'), 'Physical tails require an admitted allocation'
    assert re.fullmatch('[0-9a-f]{40}',args.source_commit or '')
    assert re.fullmatch('[0-9a-f]{64}',args.environment_sha256 or '')
    assert args.out is not None and not args.out.exists()
    args.out.mkdir(parents=True)
    import cantera as ct
    assert ct.__version__ == '3.2.0'
    assert sha(Path(ct._cantera.__file__)) == settings['cantera_extension_sha256']
    gas = ct.Solution(str(args.mechanism),transport_model=None)
    assert gas.thermo_model == 'ideal-gas' and gas.species_names == raw['species'].tolist()
    model = StateModel(gas,settings)
    receipt = {'schema':'physical-family-table/v1','status':'physical_tails_running',
        'source_commit':args.source_commit,'environment_sha256':args.environment_sha256,
        'job_id':os.environ['SLURM_JOB_ID'],'case':original['case'],
        'mechanism_sha256':settings['mechanism_sha256'],'metadata_sha256':settings['input_metadata_sha256'],
        'cantera_extension_sha256':settings['cantera_extension_sha256'],'settings_sha256':sha(args.settings),
        'source_files':{p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},
        'input_receipt_sha256':settings['input_receipt_sha256'],'input_trajectory_sha256':settings['input_trajectory_sha256'],
        'original_source_commit':original['source_commit'],'progress_species':settings['progress_species'],
        'model':'Explicit approximate quench plus fresh homogeneous HP chemical branches; ideal-gas GRI/unity-Le ancestry',
        'scientific_acceptance':False,'automatic_table_replacement':False,'cases':[]}
    write_json(args.out/'receipt.json',receipt)
    shutil.copyfile(args.raw_dir/'phase-metadata.json',args.out/'phase-metadata.json')
    branches,reports = {},{}
    start = time.monotonic()
    for j,z in enumerate(raw['Z']):
        output = args.out/f'z-{j:03d}'
        output.mkdir()
        try:
            if j in (0,128):
                row,audit = model.at_ty(raw['T_K'][0,j],raw['Y'][0,j],close_zero=True)
                branch = row[None,:]
                report = {'status':'pure_boundary','numerically_complete':True,'seed_Cwater':0,
                    'Z':float(z),'cap_source_kg_m3_s':float(row[SC]),'representation':audit}
                np.savez_compressed(output/'branch.npz',states=branch)
                write_json(output/'tail-receipt.json',report)
            else:
                branch,report = build_branch(model,raw,j,settings,output,ct)
            branches[j],reports[j] = branch,report
            result = {'Z_index':j,'Z':float(z),'role':'training' if j%2==0 else 'held-out',
                'status':report['status'],'numerically_complete':report['numerically_complete'],
                'cap_Cwater':float(branch[-1,C]),'cap_Scwater':float(branch[-1,SC]),
                'branch_sha256':sha(output/'branch.npz'),'receipt_sha256':sha(output/'tail-receipt.json')}
        except Exception as exception:
            (output/'traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
            result = {'Z_index':j,'Z':float(z),'status':'failed','error':repr(exception),
                      'traceback_sha256':sha(output/'traceback.txt')}
        receipt['cases'].append(result)
        write_json(args.out/'receipt.json',receipt)
        print(json.dumps(result),flush=True)
    missing_training = [j for j in range(0,129,2) if j not in branches]
    missing_heldout = [j for j in range(1,129,2) if j not in branches]
    receipt.update(missing_training_Z_indices=missing_training,missing_heldout_Z_indices=missing_heldout)
    if missing_training:
        receipt.update(status='incomplete_physical_family',elapsed_s=time.monotonic()-start)
        write_json(args.out/'receipt.json',receipt)
        return 2
    write_json(args.out/'profile-set.json',{'input_trajectory_sha256':settings['input_trajectory_sha256'],
                                         'physical_branches':receipt['cases']})
    try:
        axis,eta,limits,values,diagnostics = build(model,branches,reports,raw['Z'],settings,args.out)
        write_table(args.out/'physical.tbl',model,axis,eta,limits,values,args.source_commit,sha(args.out/'profile-set.json'))
        receipt.update(status='diagnostic_table_exported_not_accepted',elapsed_s=time.monotonic()-start,
            all_source_caps_inward=not diagnostics['outward_upper_nodes'] and not diagnostics['outward_lower_nodes'],
            full_progress_coverage_qualified=False,heldout_scope='64 independently integrated odd Z nodes; 65 even Z training nodes')
    except Exception as exception:
        (args.out/'tabulation-traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
        receipt.update(status='tabulation_failed',error=repr(exception),elapsed_s=time.monotonic()-start)
    receipt['artifacts'] = {p.name:sha(p) for p in args.out.iterdir() if p.is_file() and p.name!='receipt.json'}
    write_json(args.out/'receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'all_source_caps_inward':receipt.get('all_source_caps_inward'),
                      'elapsed_s':receipt['elapsed_s'],'scientific_acceptance':False}),flush=True)
    return 0 if receipt['status']=='diagnostic_table_exported_not_accepted' else 3


if __name__ == '__main__':
    raise SystemExit(main())
