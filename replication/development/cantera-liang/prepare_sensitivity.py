"""Prepare independent steady-domain and initial-guess checks; no CFD restart."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil


def prepare(action,base,output,mode):
    if output.exists():raise ValueError('Refusing an existing output directory')
    with (base/'guess.csv').open(newline='',encoding='utf8') as stream:
        reader=csv.DictReader(stream);columns=reader.fieldnames
        rows=[{k:float(v) for k,v in row.items()} for row in reader]
    names=[line.split()[0] for line in (base/'species.txt').read_text().splitlines()]
    if len(names)!=53 or len(rows)<10 or columns[5:]!=names:
        raise ValueError('Expected the declared 53-species guess schema')
    x=[row['x_m'] for row in rows];width=x[-1]-x[0]
    if x[0]!=0 or width<=0 or any(b<=a for a,b in zip(x,x[1:])):
        raise ValueError('Expected increasing coordinates from zero')
    for row in rows:
        if not all(math.isfinite(v) for v in row.values()):raise ValueError('Nonfinite guess')
        y=[row[name] for name in names]
        if min(y)<-1e-9 or abs(sum(y)-1)>1e-7:raise ValueError('Invalid guess composition')
    if mode=='extended-domain':
        shift=width/2
        transformed=[dict(rows[0],x_m=shift*j/20) for j in range(20)]
        transformed += [dict(row,x_m=row['x_m']+shift) for row in rows]
        transformed += [dict(rows[-1],x_m=width+shift+shift*j/20) for j in range(1,21)]
    elif mode=='shifted-guess':
        shift=width/8
        transformed=[dict(rows[0],x_m=0)]
        transformed += [dict(row,x_m=row['x_m']+shift) for row in rows if row['x_m']+shift<width]
        transformed += [dict(rows[-1],x_m=width)]
        for row in transformed:row['U_m_s']*=1.25
    else:raise ValueError('Unknown sensitivity mode')
    files=[base/name for name in ['ideal.yaml','srk.yaml','species.txt','guess.csv']]
    receipt=dict(purpose='steady numerical sensitivity, not a transient restart',mode=mode,
        old_width_m=width,new_width_m=transformed[-1]['x_m'],shift_m=shift,
        old_points=len(rows),new_points=len(transformed),
        velocity_guess_factor=1.25 if mode=='shifted-guess' else 1,
        source_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    print(json.dumps(receipt,indent=2))
    if action=='plan':return
    output.mkdir(parents=True)
    for path in files[:-1]:shutil.copy2(path,output/path.name)
    with (output/'guess.csv').open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows(transformed)
    (output/'sensitivity.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply'])
    parser.add_argument('base',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('mode',choices=['extended-domain','shifted-guess'])
    args=parser.parse_args();prepare(args.action,args.base,args.output,args.mode)
