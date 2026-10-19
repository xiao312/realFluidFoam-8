"""Check selected ideal model, analytical density and finite endpoint fields."""
import csv
import json
import math
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'validation/flames/adaptive'))
from fields import inspect,times,scalar


def density_check(case):
    cfg=json.loads((case/'paper-case.json').read_text())
    text=(case/'constant/thermo.inputData_GRI').read_text()
    weights={n:float(re.search(r'(?m)^'+n+r'\s*\{\s*specie\s*\{\s*molWeight\s+([^;]+)',text)[1])
             for n in ['CH4','O2','N2']}
    moles={'CH4':cfg['phi'],'O2':2,'N2':2*79/21}
    mean_weight=sum(weights[n]*x for n,x in moles.items())/sum(moles.values())
    expected=10132500*mean_weight/(8314.46261815324*298)
    rows=list(csv.DictReader((case/'inlet-densities.csv').open()))
    errors={r['patch']:abs(float(r['rho_kg_m3'])/expected-1) for r in rows if r['patch'] in ('left','right')}
    if len(errors)!=2 or max(errors.values())>2e-5:raise ValueError('Ideal density identity failed')
    return {'expected_ideal_density_kg_m3':expected,'relative_errors':errors,'probe':rows}


def check(job,mode):
    case=job/'case';cfg=json.loads((case/'paper-case.json').read_text())
    result=density_check(case)
    log=(job/'solver.log').read_text()
    if not all(s in log for s in ['idKineticMixture','perfectGas','idKineticStandard','seulex']):
        raise ValueError('Ideal runtime selection not evidenced in log')
    steps=[float(v) for v in re.findall(r'^Time = (\S+)',log,re.M)]
    if not re.search(r'^End\s*$',log,re.M) or abs(steps[-1]-cfg['end_time_s'])>cfg['max_delta_t_s']*.51:
        raise ValueError('Solver endpoint not reached')
    latest=times(case,8)[-1]
    fields,_=inspect(case,8,latest)
    rows=list(csv.DictReader((case/'processor0/flame-speed.csv').open()))
    if not rows or not {'integrated_species_solve','instantaneous_end_step'}<=set(r['stage'] for r in rows):
        raise ValueError('Missing diagnostics')
    heat=[]
    for rank in range(8):heat+=scalar(case/f'processor{rank}'/latest/'Qdot',1000)
    if not all(math.isfinite(v) for v in heat):raise ValueError('Nonfinite Qdot')
    result.update(fields=fields,endpoint_s=steps[-1],rows=len(rows),
        valid_rows=sum(r['status']=='valid' for r in rows),Qdot_max_W_m3=max(heat),
        Qdot_net_W=sum(heat)*5e-17,scientific_acceptance=False)
    if mode=='smoke':
        # Compare all common fields, excluding only newly exported diagnostics.
        mismatches=[];count=0
        for other in (job/'diagnostics-off').glob('processor*/'+latest+'/*'):
            if not other.is_file():continue
            path=case/other.relative_to(job/'diagnostics-off')
            body=lambda p:re.sub(r'FoamFile\s*\{.*?\}','',p.read_text(),flags=re.S)
            if not path.exists() or body(other)!=body(path):mismatches.append(str(other))
            count+=1
        if count<500 or mismatches:raise ValueError('Diagnostic equivalence failed: '+str(mismatches[:4]))
        result.update(compared_fields=count,mismatches=mismatches)
    (job/'endpoint-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    check(Path(sys.argv[1]),sys.argv[2])
