"""Configure strict linear solves and inspect original-zero qualification runs."""
import argparse,csv,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import inspect,times
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['configure','check'])
p.add_argument('job',type=Path);p.add_argument('library_job')
p.add_argument('ranks',type=int,choices=[8,32]);p.add_argument('mode',choices=['build','full'])
a=p.parse_args();case=a.job/'case'
if not a.library_job.isdigit():raise ValueError('Numeric library job required')
if a.action=='configure':
    path=case/'system/fvSolution';text=path.read_text()
    text,n=re.subn(r'\btolerance\s+[^;]+;','tolerance 1e-12;',text)
    if n!=2:raise ValueError('Unexpected tolerance declarations')
    text,n=re.subn(r'\brelTol\s+[^;]+;','relTol 0;',text)
    if n!=4:raise ValueError('Unexpected relative tolerance declarations')
    path.write_text(text)
    path=case/'system/controlDict';text=path.read_text()
    text=re.sub(r'\bapplication\s+[^;]+;','application rfThermoReactingFoam;',text)
    if a.mode=='build':
        for key,value in [('endTime','1e-7'),('writeControl','adjustableRunTime'),('writeInterval','1e-7')]:
            text,n=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text)
            if n!=1:raise ValueError('Unexpected control '+key)
        for metadata in [case/'fresh-start-inputs.json',case/'tracking-inputs.json',a.job/'tracking-plan.json']:
            record=json.loads(metadata.read_text());record['end_time_s']=1e-7
            record['qualification_smoke']=True
            if 'controls' in record:record['controls']['endTime']='1e-7'
            metadata.write_text(json.dumps(record,indent=2)+'\n')
    path.write_text(text)
    (a.job/'thermo-inputs.json').write_text(json.dumps(dict(library_job=a.library_job,
        mpi_ranks=a.ranks,mode=a.mode,numerics='strict12',chemistry='native',transport='native',
        current_species_enthalpy=True,initialization='generated_original_zero'),indent=2)+'\n')
else:
    latest=times(case,a.ranks)[-1];data,_=inspect(case,a.ranks,latest)
    rows=list(csv.DictReader((case/'processor0/front-tracking.csv').open()))
    if not rows or min(float(r['time_s']) for r in rows)!=0:raise ValueError('Missing zero-time tracking')
    expected=json.loads((case/'fresh-start-inputs.json').read_text())['end_time_s']
    if abs(float(latest)-expected)>2.6e-8:raise ValueError('Endpoint mismatch')
    receipts=[json.loads((a.job/f'rank-{i}-cpu.json').read_text()) for i in range(a.ranks)]
    if len({r['cpu'] for r in receipts})!=a.ranks:raise ValueError('Overlapping CPU assignments')
    data.update(first_time_s=0,latest_time_s=float(latest),scientific_acceptance=False)
    print(json.dumps(data,indent=2))
