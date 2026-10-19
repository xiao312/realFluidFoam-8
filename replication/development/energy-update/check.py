"""Verify unchanged donor inputs and health of the isolated parallel smoke run."""
import json
from pathlib import Path
import re
import sys

action, job = sys.argv[1], Path(sys.argv[2])
if action == 'inputs':
    current = json.loads((job/'case/tracking-inputs.json').read_text())
    baseline = json.loads((job.parent/'124885085/case/tracking-inputs.json').read_text())
    for key in ['checkpoint', 'original_sha256', 'controls', 'temperature_anchor']:
        if current[key] != baseline[key]:
            raise ValueError('Baseline input mismatch: '+key)
    print('PASS: checkpoint, original file hashes, controls and tracking anchors match job 124885085')
elif action == 'prepare-smoke':
    path = job/'smoke/system/controlDict'
    text = path.read_text()
    start = float(re.search(r'\bstartTime\s+([^;]+);', text).group(1))
    for key, value in {'endTime':format(start+1e-7,'.17g'), 'adjustTimeStep':'no',
                       'deltaT':'5e-8', 'writeControl':'timeStep', 'writeInterval':'1'}.items():
        text, count = re.subn(r'\b'+key+r'\s+[^;]+;', key+' '+value+';', text)
        if count != 1:
            raise ValueError('Missing/repeated control '+key)
    path.write_text(text)
elif action == 'smoke':
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
    from fields import times, inspect
    latest = times(job/'smoke',8)[-1]
    fields, _ = inspect(job/'smoke',8,latest)
    report = {'time':latest, 'fields':fields, 'scientific_acceptance':False}
    (job/'smoke-fields.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
else:
    raise ValueError('Expected inputs, prepare-smoke or smoke')
