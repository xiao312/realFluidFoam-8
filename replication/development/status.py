"""Read-only Slurm and evidence snapshot for all recorded development jobs."""
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

root=Path(sys.argv[1]).resolve()
ledger=root/'results/development-reservations.tsv'
if not ledger.is_file():raise SystemExit('Missing development reservation ledger: '+str(ledger))
rows=[line.split('\t') for line in ledger.read_text().splitlines()]
ids=','.join(row[0] for row in rows)
account=subprocess.check_output(['sacct','-j',ids,'-X','-n','-P','-o','JobID,State,Elapsed,Timelimit,ExitCode'],universal_newlines=True)
states={parts[0]:dict(zip(['state','elapsed','limit','exit_code'],parts[1:5])) for line in account.splitlines() if (parts:=line.split('|'))}
output={'observed_at':datetime.datetime.now().astimezone().isoformat(),'maximum_reserved_core_hours':sum(float(row[1]) for row in rows),'jobs':[]}
for job,cost,key,revision in rows:
    directory=root/'jobs'/job
    entry={'job':int(job),'key':key,'source_revision':revision,'maximum_reserved_core_hours':float(cost),'accounting':states.get(job)}
    for name in ['endpoint-check.json','upstream-endpoint-check.json','baseline-comparison.json','runtime-state.json']:
        path=directory/name
        if path.is_file():entry[name[:-5]]=json.loads(path.read_text())
    for name in ['result.txt','solver-product.sha256']:
        path=directory/name
        if path.is_file():entry[name]=path.read_text().strip().split()[0] if name.endswith('sha256') else path.read_text().strip()
    for name in ['solver.log','upstream-solver.log']:
        path=directory/name
        if not path.exists():continue
        with path.open('rb') as stream:
            stream.seek(max(0,path.stat().st_size-131072));tail=stream.read().decode(errors='replace')
        values=re.findall(r'^Time = ([0-9.eE+-]+)',tail,re.M)
        if values:entry[name]={'latest_entered_time_s':float(values[-1]),'end_seen':bool(re.search(r'^End$',tail,re.M))}
    if key=='counterflow-mesh':
        entry['meshes']={}
        for condition in ['oxy-1','oxy-200','air-100']:
            log=directory/(condition+'-checkMesh.log')
            if log.exists():
                text=log.read_text();cells=re.search(r'^\s*cells:\s*(\d+)',text,re.M)
                entry['meshes'][condition]={'mesh_ok':'Mesh OK.' in text,'cells':int(cells[1]) if cells else None}
    output['jobs'].append(entry)
print(json.dumps(output,indent=2))
