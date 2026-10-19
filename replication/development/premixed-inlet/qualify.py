"""Require identical solver source, configuration and equilibrium seed for full runs."""
import hashlib
import json
from pathlib import Path
import re
import sys
release=Path(sys.argv[1]);key=sys.argv[2];smoke=Path(sys.argv[3])
module=release/'replication/development/premixed-inlet'
meta=json.loads((smoke/'case/case.json').read_text())
assert meta['key']==key and meta['mode']=='smoke' and meta['runtime_finalized']
assert meta['config']==json.loads((module/'cases.json').read_text())[key]
assert meta['seed_sha256']==hashlib.sha256((module/'seeds'/(key+'.json')).read_bytes()).hexdigest()
assert json.loads((smoke/'baseline-comparison.json').read_text())['matched_field_bodies']>200
revision=re.search(r'^source=(.+)$',(smoke/'validation-inputs.txt').read_text(),re.M)[1]
matches=[p.parent for p in (smoke.parent.parent/'releases').glob('*/SOURCE_REVISION') if p.read_text().strip()==revision]
assert len(matches)==1,'Cannot identify unique smoke source release'
for relative in ['development/premixed-inlet/prepare.py','development/premixed-inlet/runtime.py',
                 'validation/flames/generate_premixed.py','validation/flames/generate_counterflow.py',
                 'validation/inputs/thermo.inputData_GRI','validation/inputs/reactionsGRI']:
    assert (release/'replication'/relative).read_bytes()==(matches[0]/'replication'/relative).read_bytes(),relative
source=release/'replication/development/solver'
for file in source.rglob('*'):
    if not file.is_file() or file.name=='README.md':continue
    assert file.read_bytes()==(smoke/'solver-source'/file.relative_to(source)).read_bytes(),str(file)
print('PASS: matching startup case, seed and solver source with upstream field equivalence')
