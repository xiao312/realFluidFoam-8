"""Prepare a declared sweep using nearest saved ideal profiles as numerical guesses."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply'])
    for name in ['mechanism','species','output']:p.add_argument(name,type=Path)
    p.add_argument('profiles',type=Path,nargs='+',help='Prefer earlier directories for exact ties')
    p.add_argument('--phis',type=float,nargs='+',default=[.92,.95,1.,1.05,1.1,1.15,1.2,1.25,1.3,1.35,1.4,1.44])
    a=p.parse_args()
    if a.output.exists():raise ValueError('Output exists')
    candidates=[]
    for rank,folder in enumerate(a.profiles):
        for path in sorted(folder.glob('phi*.csv')):
            m=re.fullmatch(r'phi(\d{3})',path.stem)
            if m:candidates.append((int(m[1])/100,rank,path))
    if not candidates:raise ValueError('No saved ideal profiles')
    plan=[]
    for phi in a.phis:
        seed=min(candidates,key=lambda item:(abs(item[0]-phi),item[1]))
        plan.append({'phi':phi,'guess_phi':seed[0],'profile':str(seed[2].resolve()),
                     'output':str((a.output/f'phi{round(phi*100):03d}').resolve())})
    if len({r['output'] for r in plan})!=len(plan):raise ValueError('Duplicate condition keys')
    print(json.dumps(plan,indent=2),flush=True)
    commands=[]
    for row in plan:
        cmd=[sys.executable,'-B',str(Path(__file__).with_name('prepare.py')),'plan',str(a.mechanism),str(a.species),row['profile'],row['output'],'--phi',str(row['phi'])]
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL);commands.append(cmd)
    if a.action=='plan':return
    a.output.mkdir(parents=True)
    (a.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    for cmd in commands:
        cmd[3]='apply';subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)


if __name__=='__main__':main()
