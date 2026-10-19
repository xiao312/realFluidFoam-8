"""Prepare isolated one-step observer replays and verify fields/source reductions."""
import argparse
import csv
import json
from pathlib import Path
import re
import shutil
import sys
from attach import block
MODULE=Path(__file__).resolve().parent
sys.path.insert(0,str(MODULE.parents[1]/'validation/flames/adaptive'))
from fields import scalar,inspect


def prepare(job):
    original=Path('/work/jobs/124864535/case')
    for mode in ['on','off']:
        case=job/mode;case.mkdir()
        for name in ['0','constant','system']:shutil.copytree(original/name,case/name)
        for rank in range(8):
            for name in ['0','constant']:
                shutil.copytree(original/f'processor{rank}'/name,case/f'processor{rank}'/name)
        path=case/'system/controlDict';text=path.read_text()
        text=re.sub(r'\bendTime\s+[^;]+;','endTime 1e-10;',text)
        text=re.sub(r'\bwriteInterval\s+[^;]+;','writeInterval 1e-10;',text)
        if mode=='on':text+=block(str(job/'monitor-lib/librfHeatReleaseMonitor.so'),1)
        path.write_text(text)


def check(job, native=False):
    mismatches=[];count=0;time='1e-10';on=job/'on';off=job/'off'
    for p in off.glob(f'processor*/{time}/*'):
        if not p.is_file():continue
        other=on/p.relative_to(off)
        body=lambda path:re.sub(r'FoamFile\s*\{.*?\}','',path.read_text(),flags=re.S)
        if not other.exists() or body(p)!=body(other):mismatches.append(str(p.relative_to(off)))
        count+=1
    if count<1000 or mismatches:raise ValueError('Field mismatch or missing fields: '+str(mismatches[:5]))
    history='processor0/flame-speed.csv'
    if (on/history).read_bytes()!=(off/history).read_bytes():
        raise ValueError('Flame-speed diagnostics changed')
    endpoint,_=inspect(on,8,time)
    rows=list(csv.DictReader((on/'processor0/heat-release-used.csv').open()))
    row=rows[-1]
    if abs(float(row['time_s'])-1e-10)>1e-20:raise ValueError('History timestamp mismatch')
    q=[]
    for rank in range(8):q.extend(scalar(on/f'processor{rank}'/time/'Qdot_used',1000))
    if native:
        q_native=[]
        for rank in range(8):q_native.extend(scalar(on/f'processor{rank}'/time/'Qdot',1000))
        if q_native!=q:raise ValueError('Native Qdot differs from independent chemistry observer')
    expected={'net_W':sum(q)*5e-17,'positive_W':sum(max(x,0) for x in q)*5e-17,
        'negative_W':sum(min(x,0) for x in q)*5e-17,'Qdot_max_W_m3':max(q),'Qdot_min_W_m3':min(q)}
    for key,value in expected.items():
        if abs(float(row[key])-value)>1e-9*max(abs(value),1e-20):raise ValueError('Reduction mismatch '+key)
    if abs(float(row['net_W'])-float(row['left_W'])-float(row['right_W']))>1e-15:raise ValueError('Half-domain power mismatch')
    result={'compared_fields':count,'mismatches':mismatches,'endpoint':endpoint,'heat_release':row,
        'independent_saved_field_reductions':expected,'native_Qdot_checked':native,
        'qualification':'source output equivalence only; no flame acceptance'}
    (job/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','check']);p.add_argument('job',type=Path)
    p.add_argument('--native',action='store_true')
    a=p.parse_args();prepare(a.job) if a.action=='prepare' else check(a.job,a.native)
