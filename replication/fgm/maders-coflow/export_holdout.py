"""Export marked physical snapshots as a separate interpolation reference."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--family',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--plan',action='store_true')
    a=p.parse_args()
    root=a.family.resolve();manifest=root/'manifest.json'
    family=json.loads(manifest.read_text())
    if family.get('schema')!='maders-quenching-family/v1':
        raise ValueError('Require a physical quenching-family manifest')
    rows=[r for r in family['profiles'] if r.get('held_out')]
    if not rows:raise ValueError('No marked temporal hold-outs; never infer them from training')
    plan={'manifest':str(manifest),'manifestSha256':sha(manifest),
          'profiles':[r['profile']for r in rows],'out':str(a.out),
          'kind':'withheld physical temporal interpolation states',
          'originalSteadyReferenceChanged':False,'scientificAcceptance':False}
    if a.plan:print(json.dumps(plan,indent=2));return
    fields={k:[]for k in ['Z','C','T','Y','Sc_kg_m3_s']}
    species=None;weights=None;inputs={}
    for row in rows:
        file=(root/row['profile']).resolve()
        if not file.is_relative_to(root) or sha(file)!=row['sha256']:
            raise ValueError('Changed or escaping physical hold-out '+row['profile'])
        if not row['finite'] or row.get('solver_error') is not None:
            raise ValueError('Failed physical hold-out '+row['profile'])
        with np.load(file)as data:
            if species is None:
                species=data['species'].copy();weights=data['progress_weights'].copy()
            if (not np.array_equal(species,data['species']) or
                not np.array_equal(weights,data['progress_weights'])):
                raise ValueError('Physical reference definitions differ')
            for key in fields:
                values=data[key].copy()
                if not np.isfinite(values).all():raise ValueError('Nonfinite physical '+key)
                fields[key].append(values)
        inputs[row['profile']]=row['sha256']
    values={key:np.concatenate(value,axis=0)for key,value in fields.items()}
    a.out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(a.out/'reference.npz',**values,species=species,progress_weights=weights)
    receipt={**plan,'inputs':inputs,'queries':len(values['Z']),
             'referenceSha256':sha(a.out/'reference.npz'),'scriptSha256':sha(Path(__file__))}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
