"""Copy selected checkpoint inputs and compare short replay outputs."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

mode, job_arg = sys.argv[1:]
job=Path(job_arg).resolve()
assert str(job).startswith('/work/jobs/')
cases=[('one-step',124672685,'author-cases/one-step','0.12',8,1e-6),
       ('oxy-1',124672685,'author-cases/gri30','0.001',8,1e-6),
       ('oxy-200',124674723,'paper-cases/gri30','0',8,1e-6),
       ('air-100',124674728,'paper-cases/gri30','0',8,1e-6),
       ('premixed',124674599,'paper-cases/premixed','8e-05',4,1e-8)]
if mode=='prepare':
    manifests=[]
    for key,origin,sub,time,ranks,dt in cases:
        source=Path('/work/jobs')/str(origin)/sub
        for variant in (['timed','baseline'] if key in ('oxy-1','premixed') else ['timed']):
            dest=job/(key+'-'+variant);dest.mkdir()
            for name in ('system','constant'):
                shutil.copytree(source/name,dest/name)
            for rank in range(ranks):
                target=dest/('processor'+str(rank));target.mkdir()
                for name in ('constant',time):
                    shutil.copytree(source/('processor'+str(rank))/name,target/name)
            p=dest/'system/controlDict';s=p.read_text()
            end=float(time)+5*dt
            for name,value in [('startFrom','startTime'),('startTime',time),('endTime',format(end,'.12g')),('writeControl','timeStep'),('writeInterval','5'),('runTimeModifiable','no')]:
                pattern=r'\b'+name+r'\s+[^;]+;'
                if re.search(pattern,s):s=re.sub(pattern,name+' '+value+';',s)
                else:s+='\n'+name+' '+value+';\n'
            p.write_text(s)
            manifests.append(dict(key=key,variant=variant,origin=origin,checkpoint=time,end=end,ranks=ranks,path=str(dest)))
    (job/'replays.json').write_text(json.dumps(manifests,indent=2))
elif mode=='verify':
    results=[]
    for key in ('oxy-1','premixed'):
        a,b=job/(key+'-timed'),job/(key+'-baseline')
        latest=max((p for p in (a/'processor0').iterdir() if p.is_dir() and p.name!='constant'),key=lambda p:float(p.name)).name
        mismatches=[];count=0
        for p in a.glob('processor*/'+latest+'/*'):
            if not p.is_file():continue
            other=b/p.relative_to(a)
            # Headers contain case locations, so compare the numerical body.
            body=lambda f: re.sub(r'FoamFile\s*\{.*?\}', '',f.read_text(),flags=re.S)
            if body(p)!=body(other):mismatches.append(str(p.relative_to(a)))
            count+=1
        results.append(dict(case=key,fields=count,mismatches=mismatches))
    (job/'equivalence.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results));assert all(not r['mismatches'] for r in results)
else:raise ValueError(mode)
