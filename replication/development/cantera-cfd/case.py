"""Configure an original-zero transport experiment and inspect its endpoint."""
import argparse
import csv
import json
from pathlib import Path
import re
import sys

module=Path(__file__).resolve().parent
sys.path.insert(0,str(module.parents[1]/'validation/flames/adaptive'))
from fields import inspect,times

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['configure','check'])
p.add_argument('job',type=Path);p.add_argument('bridge_job');p.add_argument('mode',choices=['build','full'])
p.add_argument('--chemistry-mode',choices=['native','adiabaticCP'],default='native')
p.add_argument('--execution-profile',choices=['uniform8','bands32'],default='uniform8')
a=p.parse_args();case=a.job/'case'
if not a.bridge_job.isdigit():raise ValueError('Numeric bridge job required')
if a.action=='configure':
    (case/'constant/canteraBridge').write_text(
        'FoamFile {version 2.0; format ascii; class dictionary; object canteraBridge;}\n'
        f'libraryPath "/work/jobs/{a.bridge_job}/librfcantera.so";\n'
        'inputDirectory "/work/cache/cantera-liang-20261019/inputs";\n'
        'stage 1; options full;\n'
        f'chemistryMode {a.chemistry_mode};\nchemistryRtol 1e-10; chemistryAtol 1e-18;\n'
        'runtimeProfiling true;\n')
    control=case/'system/controlDict';text=control.read_text()
    text=re.sub(r'\bapplication\s+[^;]+;','application rfCanteraBridgeFoam;',text)
    if a.mode=='build':
        for key,value in [('endTime','1e-7'),('writeControl','adjustableRunTime'),('writeInterval','1e-7')]:
            text,n=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text)
            if n!=1:raise ValueError('Unexpected control '+key)
        for path in [case/'fresh-start-inputs.json',case/'tracking-inputs.json',a.job/'tracking-plan.json']:
            record=json.loads(path.read_text());record['end_time_s']=1e-7
            record['qualification_smoke']=True
            if 'controls' in record:record['controls']['endTime']='1e-7'
            path.write_text(json.dumps(record,indent=2)+'\n')
    control.write_text(text)
    (a.job/'bridge-inputs.json').write_text(json.dumps(dict(bridge_job=a.bridge_job,
        model_stage=1,model_options='full',changed_coefficients=['kappa','Dimix'],
        current_native_species_enthalpy=True,chemistry_changed=a.chemistry_mode!='native',
        chemistry_mode=a.chemistry_mode,chemistry_rtol=1e-10,chemistry_atol=1e-18,
        initialization='generated_original_zero',mode=a.mode,execution_profile=a.execution_profile,
        mpi_ranks=32 if a.execution_profile=='bands32' else 8),indent=2)+'\n')
else:
    ranks=32 if a.execution_profile=='bands32' else 8
    latest=times(case,ranks)[-1];data,_=inspect(case,ranks,latest)
    rows=list(csv.DictReader((case/'processor0/front-tracking.csv').open()))
    if not rows or min(float(row['time_s']) for row in rows)!=0:raise ValueError('Not an original-zero trace')
    expected=json.loads((case/'fresh-start-inputs.json').read_text())['end_time_s']
    metadata=json.loads((a.job/'bridge-inputs.json').read_text())
    if metadata['chemistry_mode']!=a.chemistry_mode:raise ValueError('Chemistry mode mismatch')
    if metadata['execution_profile']!=a.execution_profile:raise ValueError('Execution profile mismatch')
    if a.chemistry_mode=='adiabaticCP' and 'Cantera/native molar formation enthalpies verified' not in (a.job/'case.log').read_text():
        raise ValueError('Missing formation-enthalpy qualification')
    if abs(float(latest)-expected)>2.6e-8:raise ValueError('Endpoint mismatch')
    data.update(first_time_s=0,latest_time_s=float(latest),scientific_acceptance=False)
    print(json.dumps(data,indent=2))
