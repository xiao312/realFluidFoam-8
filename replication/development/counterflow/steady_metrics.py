"""Conservative full-field steady-candidate diagnostics on identical decomposition."""
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import inspect,scalar,species


def vectors(path,count):
    text=path.read_text()
    m=re.search(r'internalField\s+uniform\s*\(([^)]*)\)',text)
    if m:
        values=list(map(float,m[1].split()))
        if len(values)!=3:raise ValueError('Invalid uniform vector')
        return values*count
    m=re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
    if not m:raise ValueError('Invalid vector '+str(path))
    values=list(map(float,m[2].replace('(',' ').replace(')',' ').split()))
    if int(m[1])!=count or len(values)!=3*count:raise ValueError('Vector size mismatch')
    return values


def mass_balance(case,time,ranks):
    flux={name:0.0 for name in ['fuel','oxidizer','outlet']}
    for rank in range(ranks):
        proc=case/('processor'+str(rank));text=(proc/time/'phi').read_text()
        if not re.search(r'dimensions\s*\[1 0 -1 0 0 0 0\]',text):raise ValueError('Expected mass-flux phi')
        mesh=(proc/'constant/polyMesh/boundary').read_text()
        for patch in flux:
            m=re.search(r'\b'+patch+r'\s*\{([^{}]*)\}',mesh,re.S)
            count=int(re.search(r'nFaces\s+(\d+)',m[1])[1])
            if count==0:continue
            block=re.search(r'\b'+patch+r'\s*\{([^{}]*)\}',text,re.S)[1]
            uniform=re.search(r'value\s+uniform\s+([^;]+);',block)
            if uniform:values=[float(uniform[1])]*count
            else:
                m=re.search(r'value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;',block,re.S)
                if not m:raise ValueError('Missing phi values on '+patch)
                values=list(map(float,m[2].split()))
                if int(m[1])!=count or len(values)!=count:raise ValueError('Boundary phi size mismatch')
            if not all(math.isfinite(v) for v in values):raise ValueError('Invalid boundary flux')
            flux[patch]+=sum(values)
    inflow=-(flux['fuel']+flux['oxidizer'])
    if inflow<=0 or flux['outlet']<=0:raise ValueError('Unexpected inlet/outlet mass-flux signs')
    return {'patch_mass_flow_kg_s':flux,'relative_imbalance':abs(sum(flux.values()))/inflow}


def compare(case,reference,old,new,ranks=32):
    span=float(new)-float(old)
    if span<.01-1e-12:return {'reference_time_s':float(old),'time_s':float(new),'span_s':span,'candidate':False,'reason':'Physical observation window shorter than 0.01 s'}
    health,_=inspect(case,ranks,new)
    names=['T','U','rho','p',*species(case)]
    differences={name:0.0 for name in names};peaks={name:0.0 for name in names}
    for rank in range(ranks):
        proc='processor'+str(rank)
        address=(case/proc/'constant/polyMesh/cellProcAddressing').read_text()
        count=int(re.search(r'\n\s*(\d+)\s*\(',address)[1])
        for name in names:
            reader=vectors if name=='U' else scalar
            a=reader(reference/proc/old/name,count);b=reader(case/proc/new/name,count)
            if not all(math.isfinite(v) for v in a+b):raise ValueError('Nonfinite comparison '+name)
            peaks[name]=max(peaks[name],max(abs(v) for v in a))
            differences[name]=max(differences[name],max(abs(x-y) for x,y in zip(a,b)))
    limits={name:max(1e-8,.001*peaks[name]) for name in names}
    limits.update(T=1.0,U=.001,rho=.001*peaks['rho'],p=1e-5*peaks['p'])
    mass=mass_balance(case,new,ranks)
    failed=[name for name in names if differences[name]>limits[name]]
    if mass['relative_imbalance']>.001:failed.append('mass_balance')
    if health['fields']['T']['max']<=1000:failed.append('burning_state')
    return {'reference_time_s':float(old),'time_s':float(new),'span_s':span,'candidate':not failed,
            'failed':failed,'max_absolute_changes':differences,'limits':limits,'mass_balance':mass,
            'health':health,'qualification':'Steady candidate only; energy balance, paper agreement and mesh/time sensitivity remain separate'}


if __name__=='__main__':
    case,reference,old,new=sys.argv[1:]
    print(json.dumps(compare(Path(case),Path(reference),old,new),indent=2))
