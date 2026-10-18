"""Validate a decomposed mapped initial state or completed fine-grid qualification."""
import json
import re
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'validation/flames/adaptive'))
from fields import inspect,times

case=Path(sys.argv[1]);mode=sys.argv[2]
assert mode in ['initial','endpoint']
time='0' if mode=='initial' else times(case,32)[-1]
report,_=inspect(case,32,time,require_rho=mode=='endpoint')
assert report['cells'] in [816000,888000]
if mode=='endpoint':assert abs(float(time)-1e-5)<1e-12
if mode=='initial':
    pilot=json.loads((case/'pilot.json').read_text())
    assert pilot['velocities_finalized']
    owners={'fuel':[],'oxidizer':[]}
    for rank in range(32):
        proc=case/('processor'+str(rank))
        mesh=(proc/'constant/polyMesh/boundary').read_text()
        velocity=(proc/'0/U').read_text()
        for patch,sign in [('fuel',1),('oxidizer',-1)]:
            block=re.search(r'\b'+patch+r'\s*\{([^{}]*)\}',mesh,re.S)[1]
            if int(re.search(r'nFaces\s+(\d+)',block)[1])==0:continue
            boundary=re.search(r'\b'+patch+r'\s*\{([^{}]*)\}',velocity,re.S)[1]
            values=re.search(r'value\s+uniform\s*\(([^)]*)\)',boundary)[1]
            vector=list(map(float,values.split()))
            expected=sign*pilot['inlet_speed_m_s'][patch]
            assert abs(vector[0])+abs(vector[1])<1e-12 and math.isclose(vector[2],expected,rel_tol=1e-10)
            owners[patch].append(rank)
    assert all(owners.values())
    report['finalized_velocity_ranks']=owners
report['qualification']='finite normalized fields only; mapped warm start is not conservative or converged'
print(json.dumps(report,indent=2))
