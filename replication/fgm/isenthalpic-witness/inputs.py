"""Read the immutable two-state source chain without integrating chemistry."""
import json
import math
from pathlib import Path
import numpy as np

from states import sha,H

NAMES=['same-ZC-rich-path','same-ZC-lean-path']


def load_inputs(mixing,receipt_hash,primary,mechanism):
    if sha(mixing/'receipt.json')!=receipt_hash:
        raise ValueError('Changed physical mixing receipt')
    old=json.loads((mixing/'receipt.json').read_text())
    if old['schema']!='physical-mixing-witness/v1' or old['status']!='completed_diagnostic' or old['audit_only']:
        raise ValueError('Require the completed physical mixing witnesses')
    if sha(primary/'receipt.json')!=old['input_receipt_sha256']:
        raise ValueError('Primary physical table receipt differs from mixing ancestry')
    source=json.loads((primary/'receipt.json').read_text())
    if source['status']!='diagnostic_table_exported_not_accepted' or source['progress_species']!=['CO2','CO','H2O']:
        raise ValueError('Unexpected primary manifold identity')
    if old['input_table_sha256']!=source['artifacts']['table.npz'] or str(old['source_job_id'])!=str(source['job_id']):
        raise ValueError('Primary table/job identity differs from retained mixing ancestry')
    if sha(mechanism)!=source['mechanism_sha256']:
        raise ValueError('Mechanism changed')
    if source['cantera_extension_sha256']!=old['cantera_extension_sha256']:
        raise ValueError('Original witnesses use different Cantera runtime identities')
    hashes={str(p):sha(p) for p in [mixing/'receipt.json',primary/'receipt.json',mechanism]}
    seeds=[]
    for name in NAMES:
        matches=[case for case in old['cases'] if case['name']==name]
        if len(matches)!=1 or not matches[0]['numerically_complete']:
            raise ValueError('Missing original completed witness: '+name)
        path=mixing/name/'initial-state.json'
        if sha(path)!=matches[0]['initial_state_sha256']:
            raise ValueError('Changed original initial state: '+name)
        seed=json.loads(path.read_text())
        row=np.asarray(seed['state'],dtype=float)
        if not np.isfinite(row).all() or seed['recipe']['name']!=name:
            raise ValueError('Invalid original seed')
        hashes[str(path)]=sha(path)
        seeds.append(seed)
    if seeds[0]['recipe']['Z']!=seeds[1]['recipe']['Z'] or seeds[0]['species_names']!=seeds[1]['species_names']:
        raise ValueError('Original pair does not share nominal Z/species order')
    enthalpy=math.fsum(seed['state'][H] for seed in seeds)/2
    return old,source,seeds,enthalpy,hashes
