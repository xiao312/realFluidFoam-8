"""Small behavioral checks for convergence thresholds and checkpoint-stop controls."""
import json
from pathlib import Path
import sys
from steady_metrics import compare
from steady_watch import request_stop,freeze_reference

root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=False)
case=root/'case';(case/'constant').mkdir(parents=True);(case/'system').mkdir()
names=['CH4','OH','N2']+['S'+str(i) for i in range(50)]
(case/'constant/species').write_text('species 53 ('+' '.join(names)+');')
(case/'system/controlDict').write_text('stopAt endTime; runTimeModifiable true;')
for rank in range(2):
    mesh=case/('processor'+str(rank))/'constant/polyMesh';mesh.mkdir(parents=True)
    (mesh/'cellProcAddressing').write_text('\n2\n(0 1)\n')
    (mesh/'boundary').write_text('fuel { nFaces 1; } oxidizer { nFaces 1; } outlet { nFaces 1; }')
    for time in ['0','0.02']:
        dest=mesh.parent.parent/time;dest.mkdir()
        for name in names:
            value={'CH4':.1,'OH':.001,'N2':.899}.get(name,0)
            (dest/name).write_text('internalField uniform '+str(value)+';')
        for name,value in [('T',1500),('p',101325),('rho',1)]:
            (dest/name).write_text('internalField uniform '+str(value)+';')
        (dest/'U').write_text('internalField uniform (0 0 0.1);')
        (dest/'phi').write_text('dimensions [1 0 -1 0 0 0 0]; boundaryField { fuel { value uniform -1; } oxidizer { value uniform -1; } outlet { value uniform 2; } }')
assert compare(case,case,'0','.0001',2)['reason'].startswith('Physical')
assert compare(case,case,'0','0.02',2)['candidate']
path=case/'processor0/0.02/T';path.write_text('internalField uniform 1502;')
assert 'T' in compare(case,case,'0','0.02',2)['failed']
path.write_text('internalField uniform 1500;')
path=case/'processor0/0.02/phi';path.write_text(path.read_text().replace('uniform 2;','uniform 2.1;'))
assert 'mass_balance' in compare(case,case,'0','0.02',2)['failed']
freeze_reference(case,'0.02',root/'reference',2)
assert len(json.loads((root/'reference/hashes.json').read_text()))==114
request_stop(case,root/'stop.json','test')
assert 'stopAt writeNow;' in (case/'system/controlDict').read_text()
assert json.loads((root/'stop.json').read_text())['before_sha256']!=json.loads((root/'stop.json').read_text())['after_sha256']
print('PASS: insufficient window, steady fields, temperature drift, mass imbalance, reference copy and atomic stop request')
