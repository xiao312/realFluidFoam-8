"""Finalize runtime-dependent startup, or inspect completed decomposed fields."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'validation/flames/adaptive'))
from fields import inspect,times


def finalize(case,meta):
    if meta['runtime_finalized']:raise ValueError('Already finalized')
    with (case/'inlet-densities.csv').open() as stream:rows={r['patch']:r for r in csv.DictReader(stream)}
    ru=float(rows['left']['rho_kg_m3']);rb=float(rows['right']['rho_kg_m3'])
    gamma=float(rows['right']['Cp_J_kg_K'])/float(rows['right']['Cv_J_kg_K'])
    assert all(math.isfinite(v) and v>0 for v in [ru,rb,gamma]) and gamma>1
    speed=meta['config']['inlet_speed_m_s'];ub=ru*speed/rb;n=meta['config']['cells']
    body='nonuniform List<vector>\n'+str(n)+'\n(\n'+'\n'.join(f'({v:.16g} 0 0)' for v in [speed]*(n//2)+[ub]*(n//2))+'\n)'
    path=case/'0/U';text,count=re.subn(r'internalField\s+uniform\s+[^;]+;','internalField '+body+';',path.read_text())
    assert count==1;path.write_text(text)
    path=case/'0/p';text=path.read_text();assert text.count('gamma 1;')==1
    path.write_text(text.replace('gamma 1;',f'gamma {gamma:.16g};'))
    meta.update(runtime_finalized=True,unburned_density_kg_m3=ru,burned_density_kg_m3=rb,
                initial_product_speed_m_s=ub,outlet_gamma=gamma,mass_flux_kg_m2_s=ru*speed)
    meta['finalized_input_hashes']={f.relative_to(case).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for folder in ['0','constant','system'] for f in sorted((case/folder).rglob('*')) if f.is_file()}
    (case/'case.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({k:meta[k] for k in ['unburned_density_kg_m3','burned_density_kg_m3','initial_product_speed_m_s','mass_flux_kg_m2_s','outlet_gamma']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['finalize','check']);p.add_argument('case',type=Path);args=p.parse_args()
    meta=json.loads((args.case/'case.json').read_text())
    if args.action=='finalize':finalize(args.case,meta)
    else:
        latest=times(args.case,meta['ranks'])[-1]
        assert abs(float(latest)-meta['end_time_s'])<1e-12
        summary,values=inspect(args.case,meta['ranks'],latest)
        assert summary['cells']==meta['config']['cells']
        summary['qualification']='finite normalized endpoint only; flame speed and equilibrium relaxation unqualified'
        (args.case/'endpoint-check.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary))
