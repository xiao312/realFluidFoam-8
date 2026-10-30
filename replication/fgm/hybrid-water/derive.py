"""Postprocess retained physical branches with the existing explicit roundoff policy."""
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
from tabulate import build,write_table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['input','settings','mechanism']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--input-receipt-sha256',required=True)
    parser.add_argument('--endpoint-policy',choices=['existing-bounded-roundoff-v1'],required=True)
    parser.add_argument('--source-commit')
    parser.add_argument('--environment-sha256')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--plan',action='store_true')
    args = parser.parse_args()
    assert sha(args.input/'receipt.json') == args.input_receipt_sha256
    original = json.loads((args.input/'receipt.json').read_text())
    assert original['status'] == 'tabulation_failed'
    assert not original['missing_training_Z_indices'] and not original['missing_heldout_Z_indices']
    settings = json.loads(args.settings.read_text())
    assert sha(args.settings) == original['settings_sha256']
    assert sha(args.mechanism) == original['mechanism_sha256']
    assert sha(args.input/'phase-metadata.json') == original['metadata_sha256']
    branches,reports,identities = {},{},{}
    for case in original['cases']:
        j = case['Z_index']
        folder = args.input/f'z-{j:03d}'
        identities[str(j)] = {name:sha(folder/name) for name in ['branch.npz','tail-receipt.json']}
        assert identities[str(j)]['branch.npz'] == case['branch_sha256']
        assert identities[str(j)]['tail-receipt.json'] == case['receipt_sha256']
        with np.load(folder/'branch.npz') as archive:
            branches[j] = archive['states'].copy()
        reports[j] = json.loads((folder/'tail-receipt.json').read_text())
        assert reports[j]['numerically_complete']
    assert sorted(branches) == list(range(129))
    z = np.asarray([case['Z'] for case in original['cases']])
    assert np.all(np.diff(z)>0) and z[0]==0 and z[-1]==1
    plan = {'postprocess_only':True,'new_integrations':0,'original_job_id':original['job_id'],
            'original_source':original['source_commit'],'input_receipt_sha256':args.input_receipt_sha256,
            'endpoint_policy':args.endpoint_policy,'branch_identities':identities}
    if args.plan:
        print(json.dumps(plan,indent=2));return 0
    assert os.environ.get('SLURM_JOB_ID'), 'Exact Linux runtime derivation requires an admitted allocation'
    assert re.fullmatch('[0-9a-f]{40}',args.source_commit or '')
    assert re.fullmatch('[0-9a-f]{64}',args.environment_sha256 or '')
    assert args.out is not None and not args.out.exists()
    args.out.mkdir(parents=True)
    import cantera as ct
    assert ct.__version__=='3.2.0' and sha(Path(ct._cantera.__file__))==settings['cantera_extension_sha256']
    model = StateModel(ct.Solution(str(args.mechanism),transport_model=None),settings)
    corrections = []
    start = time.monotonic()
    receipt = dict(original)
    receipt.update(status='postprocess_running',source_commit=args.source_commit,
        job_id=os.environ['SLURM_JOB_ID'],environment_sha256=args.environment_sha256,
        physical_source_commit=original['source_commit'],physical_job_id=original['job_id'],
        original_receipt_sha256=args.input_receipt_sha256,postprocess_only=True,new_integrations=0,
        endpoint_policy=args.endpoint_policy,scientific_acceptance=False,automatic_table_replacement=False)
    receipt.pop('error',None)
    receipt.pop('artifacts',None)
    receipt['source_files'] = {p.name:sha(p) for p in Path(__file__).parent.glob('*.py')}
    write_json(args.out/'receipt.json',receipt)
    write_json(args.out/'derivation-inputs.json',plan)
    shutil.copyfile(args.input/'phase-metadata.json',args.out/'phase-metadata.json')
    try:
        for j,branch in branches.items():
            for side,index in [('lower',0),('upper',-1)]:
                before = branch[index].copy()
                if before[model.ys].min() >= 0:
                    continue
                after,audit = model.at_ty(before[T],before[model.ys])
                assert abs(after[C]-before[C])<=1e-12, 'Representation changed the progress coordinate'
                correction = {'Z_index':j,'Z':float(z[j]),'endpoint':side,**audit,
                    'species_names':model.gas.species_names,
                    'Y_before':before[model.ys].tolist(),'Y_after':after[model.ys].tolist(),
                    'element_names':model.gas.element_names,
                    'elements_before':(before[model.ys]@model.elements).tolist(),
                    'elements_after':(after[model.ys]@model.elements).tolist(),
                    'before':dict(zip(['Cwater','T_K','h_J_kg','rho_kg_m3','Scwater_kg_m3_s','Qformation_W_m3'],before[:6].tolist())),
                    'after':dict(zip(['Cwater','T_K','h_J_kg','rho_kg_m3','Scwater_kg_m3_s','Qformation_W_m3'],after[:6].tolist()))}
                corrections.append(correction)
                branch[index] = after
        write_json(args.out/'endpoint-representation.json',{'policy':args.endpoint_policy,
            'unchanged_negative_limit':settings['roundoff_negative_limit'],
            'unchanged_change_limit':settings['roundoff_change_limit'],'states':corrections})
        axis,eta,limits,values,diagnostics = build(model,branches,reports,z,settings,args.out)
        write_table(args.out/'physical.tbl',model,axis,eta,limits,values,args.source_commit,sha(args.out/'derivation-inputs.json'))
        receipt.update(status='diagnostic_table_exported_not_accepted',
            all_source_caps_inward=not diagnostics['outward_upper_nodes'] and not diagnostics['outward_lower_nodes'],
            full_progress_coverage_qualified=False,
            heldout_scope='64 independently integrated odd Z nodes; 65 even Z training nodes')
    except Exception as exception:
        (args.out/'tabulation-traceback.txt').write_text(traceback.format_exc(),encoding='utf8')
        receipt.update(status='tabulation_failed',error=repr(exception))
    receipt['elapsed_s'] = time.monotonic()-start
    receipt['artifacts'] = {p.name:sha(p) for p in args.out.iterdir() if p.is_file() and p.name!='receipt.json'}
    write_json(args.out/'receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'elapsed_s':receipt['elapsed_s'],'new_integrations':0}))
    return 0 if receipt['status']=='diagnostic_table_exported_not_accepted' else 3


if __name__ == '__main__':
    raise SystemExit(main())
