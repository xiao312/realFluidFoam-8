"""Read and validate saved decomposed ASCII fields, without numpy."""
import math
from pathlib import Path
import re

def times(case, ranks):
    common=None
    for rank in range(ranks):
        found={p.name for p in (case/('processor'+str(rank))).iterdir()
               if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+',p.name)}
        common=found if common is None else common & found
    if not common:raise ValueError('No common saved processor time')
    return sorted(common,key=float)

def scalar(path,count):
    text=path.read_text()
    m=re.search(r'internalField\s+uniform\s+([^;]+);',text)
    if m:return [float(m[1])]*count
    m=re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
    if not m:raise ValueError('Invalid scalar field: '+str(path))
    values=list(map(float,m[2].split()))
    if int(m[1])!=count or len(values)!=count:raise ValueError('Field size mismatch: '+str(path))
    return values

def species(case):
    for p in (case/'constant').iterdir():
        if p.is_file():
            m=re.search(r'\bspecies\s+53\s*\((.*?)\)\s*;',p.read_text(),re.S)
            if m:
                names=m[1].split()
                assert len(names)==53
                return names
    raise ValueError('Expected GRI30 species list in constant input')

def inspect(case,ranks,time):
    names=species(case);total=0;error=0;fields={k:[] for k in ['T','p','rho','CH4','OH']}
    for rank in range(ranks):
        proc=case/('processor'+str(rank))
        address=(proc/'constant/polyMesh/cellProcAddressing').read_text()
        count=int(re.search(r'\n\s*(\d+)\s*\(',address)[1]);total+=count
        sums=[0.0]*count
        for name in names:
            values=scalar(proc/time/name,count)
            if not all(math.isfinite(v) and -1e-12<=v<=1+1e-8 for v in values):
                raise ValueError('Invalid species '+name)
            sums=[a+b for a,b in zip(sums,values)]
            if name in fields:fields[name].extend(values)
        error=max(error,max(abs(s-1) for s in sums))
        for name in ['T','p','rho']:
            values=scalar(proc/time/name,count)
            if not all(math.isfinite(v) and v>0 for v in values):raise ValueError('Invalid '+name)
            fields[name].extend(values)
        text=(proc/time/'U').read_text()
        m=re.search(r'internalField\s+(?:uniform\s+(\([^;]+\))|nonuniform\s+List<vector>\s+\d+\s*\((.*?)\)\s*);',text,re.S)
        if not m:raise ValueError('Invalid velocity')
        if not all(math.isfinite(float(v)) for v in re.findall(r'[-+0-9.eE]+',(m[1] or m[2]))):raise ValueError('Nonfinite velocity')
    if error>1e-8:raise ValueError('Species sum error '+str(error))
    return dict(time_s=float(time),cells=total,species_sum_error=error,
                fields={k:dict(min=min(v),max=max(v)) for k,v in fields.items()}),fields
