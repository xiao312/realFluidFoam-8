"""Check replay output equality, finite source terms and spatial coverage."""
import csv
import json
import math
from pathlib import Path
import re
import sys

job=Path(sys.argv[1]);inputs=json.loads((job/'checkpoint-inputs.json').read_text())
end=inputs['off0']['end_time'];off=job/'off0';on=job/'on0';count=0
body=lambda p:re.sub(r'FoamFile\s*\{.*?\}','',p.read_text(),flags=re.S)
for p in off.glob('processor*/'+end+'/*'):
    if not p.is_file():continue
    other=on/p.relative_to(off)
    if not other.exists() or body(p)!=body(other):raise ValueError('Changed field '+str(p.relative_to(off)))
    count+=1
if count<1300:raise ValueError('Missing replay fields')
profiles=[]
for case in sorted(job.glob('on[0-3]')):
    files=sorted((case/'processor0').glob('spatial-*.csv'))
    if len(files)!=3:raise ValueError('Expected checkpoint and two replay stages')
    for path in files:
        rows=list(csv.DictReader(path.open()))
        if len(rows)!=8000 or any(not math.isfinite(float(v)) for r in rows for v in r.values()):
            raise ValueError('Incomplete or nonfinite spatial data')
        x=[float(r['x_m']) for r in rows]
        if any(b<=a for a,b in zip(x,x[1:])):raise ValueError('Nonmonotone spatial coordinates')
        profiles.append(str(path.relative_to(job)))
result={'compared_original_fields':count,'field_mismatches':[], 'profiles':profiles,
        'scope':'isolated checkpoint evaluations and one-step replays; donor unchanged'}
(job/'spatial-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
