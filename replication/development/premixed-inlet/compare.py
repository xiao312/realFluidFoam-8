"""Compare every written field body; directory/location header differences excluded."""
import hashlib
import json
from pathlib import Path
import re
import sys
left,right=map(Path,sys.argv[1:])
meta=json.loads((left/'case.json').read_text());end=meta['end_time_s'];count=0
for rank in range(meta['ranks']):
    proc=left/('processor'+str(rank))
    time=next(p.name for p in proc.iterdir() if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+',p.name) and abs(float(p.name)-end)<1e-12)
    for a in sorted((proc/time).iterdir()):
        if not a.is_file():continue
        b=right/('processor'+str(rank))/time/a.name
        body=lambda p:re.sub(r'FoamFile\s*\{.*?\}','',p.read_text(),count=1,flags=re.S)
        if body(a)!=body(b):raise ValueError('Endpoint mismatch: '+str(a.relative_to(left)))
        count+=1
assert count>200
print(json.dumps({'matched_field_bodies':count,'end_time_s':end,'qualification':'rename-only baseline equivalence for this smoke'}))
