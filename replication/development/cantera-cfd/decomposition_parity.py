"""Read-only global-field comparison across two completed decompositions."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import scalar,species,times


def addresses(case):
    text=(case/'system/decomposeParDict').read_text()
    match=re.search(r'\bnumberOfSubdomains\s+(\d+)\s*;',text)
    if not match or int(match[1]) not in (8,32):raise ValueError('Expected 8 or 32 ranks')
    ranks=int(match[1]);result=[]
    actual={p.name for p in case.glob('processor[0-9]*') if p.is_dir()}
    if actual!={f'processor{i}' for i in range(ranks)}:raise ValueError('Processor directories differ from declaration')
    for rank in range(ranks):
        raw=(case/f'processor{rank}/constant/polyMesh/cellProcAddressing').read_text()
        match=re.search(r'\n\s*(\d+)\s*\((.*?)\)',raw,re.S)
        if not match:raise ValueError('Invalid cell addressing')
        values=list(map(int,match[2].split()))
        if len(values)!=int(match[1]):raise ValueError('Address count mismatch')
        result.append(values)
    if sorted(i for row in result for i in row)!=list(range(8000)):
        raise ValueError('Addressing must cover every one of 8000 cells exactly once')
    return result


def vector(path,count):
    raw=path.read_text();match=re.search(r'internalField\s+uniform\s*\(([^)]+)\)\s*;',raw)
    if match:values=[list(map(float,match[1].split()))]*count
    else:
        match=re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;',raw,re.S)
        if not match or int(match[1])!=count:raise ValueError('Invalid vector field')
        values=[list(map(float,row.split())) for row in re.findall(r'\(([^)]+)\)',match[2])]
    if len(values)!=count or any(len(row)!=3 for row in values):raise ValueError('Vector count mismatch')
    return values


def global_field(case,address,time,name):
    width=3 if name=='U' else 1;result=[None]*(8000*width)
    for rank,indices in enumerate(address):
        path=case/f'processor{rank}'/time/name
        if time=='0' and not path.exists() and name in species(case):path=path.with_name('Ydefault')
        values=vector(path,len(indices)) if width==3 else [[v] for v in scalar(path,len(indices))]
        for index,row in zip(indices,values):
            for component,value in enumerate(row):result[index*width+component]=value
    if any(v is None or not math.isfinite(v) for v in result):raise ValueError('Incomplete/nonfinite global field')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference',type=Path);parser.add_argument('candidate',type=Path)
    args=parser.parse_args();cases=[args.reference,args.candidate]
    address=[addresses(case) for case in cases]
    if species(cases[0])!=species(cases[1]):raise ValueError('Species order mismatch')
    saved=[times(case,len(mapping)) for case,mapping in zip(cases,address)]
    if any('0' not in row for row in saved) or float(saved[0][-1])!=float(saved[1][-1]):
        raise ValueError('Initial or endpoint time mismatch')
    names=species(cases[0]);failures=[];initial={};endpoint={}
    for name in names+['T','p','U']:
        a,b=[global_field(case,mapping,'0',name) for case,mapping in zip(cases,address)]
        initial[name]=max(abs(x-y) for x,y in zip(a,b))
        if initial[name]!=0:failures.append('initial '+name)
    # Predeclared absolute limits in SI, plus a relative Qdot limit because its
    # magnitude changes strongly during ignition. These are smoke-only screens.
    limits={'T':1e-4,'p':.1,'rho':1e-5,'U':1e-6,'HE':.1,'Qdot':1.}
    for name in names+list(limits):
        a,b=[global_field(case,mapping,row[-1],name) for case,mapping,row in zip(cases,address,saved)]
        delta=[abs(x-y) for x,y in zip(a,b)];largest=max(delta);scale=max(map(abs,a))
        limit=limits.get(name,1e-8)
        if name=='Qdot':limit+=1e-6*scale
        endpoint[name]=dict(maximum_absolute_difference=largest,reference_scale=scale,
                            limit=limit,worst_cell=delta.index(largest)//(3 if name=='U' else 1))
        if largest>limit:failures.append('endpoint '+name)
    report=dict(reference=str(cases[0]),candidate=str(cases[1]),ranks=list(map(len,address)),
                time_s=float(saved[0][-1]),initial_maximum_differences=initial,
                endpoint=endpoint,passed=not failures,failures=failures,
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scientific_acceptance=False)
    print(json.dumps(report,indent=2))
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
