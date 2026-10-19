"""Check observational equivalence and endpoint health; not flame convergence."""
import csv
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import times,inspect


def field_equality(first,second):
    time=times(first,8)[-1];count=0
    body=lambda p:re.sub(r'FoamFile\s*\{.*?\}','',p.read_text(),flags=re.S)
    for path in first.glob('processor*/'+time+'/*'):
        if not path.is_file():continue
        other=second/path.relative_to(first)
        if not other.exists() or body(path)!=body(other):raise ValueError('Changed field '+str(path))
        count+=1
    if count<1300:raise ValueError('Insufficient common fields')
    return count


def check(job,mode):
    plan=json.loads((job/'tracking-plan.json').read_text());report={'plan':plan,'scientific_acceptance':False}
    cases=['on','off','reference'] if mode=='qualify' else ['case']
    for name in cases:
        log=(job/(name+'.log')).read_text()
        ts=[float(t) for t in re.findall(r'^Time = (\S+)',log,re.M)]
        if not ts or not re.search(r'^End\s*$',log,re.M) or abs(ts[-1]-float(plan['controls']['endTime']))>2.6e-8:
            raise ValueError('Endpoint not reached '+name)
    if mode=='qualify':
        report['old_new_common_fields']=field_equality(job/'reference',job/'on')
        report['on_off_common_fields']=field_equality(job/'off',job/'on')
        if (job/'off/processor0/front-tracking.csv').exists():raise ValueError('Disabled observer wrote history')
    case=job/('on' if mode=='qualify' else 'case')
    rows=list(csv.DictReader((case/'processor0/front-tracking.csv').open()))
    if not rows or {r['marker'] for r in rows}!={'T','OH'}:raise ValueError('Missing tracking markers')
    for r in rows:
        if r['status'] in ('valid','warmup') and not all(math.isfinite(float(r[k])) for k in ['x_m','rho_local','U_local']):
            raise ValueError('Nonfinite tracked state')
        if r['status']=='valid' and not math.isfinite(float(r['density_weighted_m_s'])):
            raise ValueError('Nonfinite tracked speed')
    if mode=='full' and not any(r['status']=='valid' and r['marker']=='T' and r['primary']=='1' for r in rows):
        raise ValueError('No valid primary temperature tracking window')
    source=list(csv.DictReader((case/'processor0/flame-speed.csv').open()))
    if {r['stage'] for r in source}!={'integrated_species_solve'}:raise ValueError('Unexpected source stages')
    latest=times(case,8)[-1];fields,_=inspect(case,8,latest)
    report.update(fields=fields,tracking_rows=len(rows),valid_tracking_rows=sum(r['status']=='valid' for r in rows),source_rows=len(source))
    (job/'tracking-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':check(Path(sys.argv[1]),sys.argv[2])
