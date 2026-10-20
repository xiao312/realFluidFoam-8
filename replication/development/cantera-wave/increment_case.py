"""Use the same reported cell-0 state without sweeping the entire CFD mesh."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import scalar,species


def prepare(action,case,output):
    case=case.resolve(strict=True);output=output.resolve()
    if output.exists() or case==output or case in output.parents:
        raise ValueError('Use a new separate probe directory')
    config=json.loads((case/'cantera-wave-inputs.json').read_text())
    if config['initialization']!='generated_original_zero' or config['cells']!=8000:
        raise ValueError('Expected an original-zero 8000-cell wave case')
    names=species(case);values={name:scalar(case/'0'/name,8000)[0] for name in ['T','p',*names]}
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (case/'0').iterdir() if p.is_file()}
    receipt=dict(source_case=str(case),reported_cell=0,probe_cells=1,source_cells=8000,
        temperature_K=values['T'],pressure_Pa=values['p'],
        mass_fractions={name:values[name] for name in names},source_zero_sha256=source_hashes,
        scope='same cell-0 verdict as the full-mesh small-increment probe')
    print(json.dumps(receipt,indent=2))
    if action=='plan':return
    output.mkdir(parents=True)
    for name in ['constant','system']:
        shutil.copytree(case/name,output/name)
    (output/'0').mkdir()
    for name,value in values.items():
        text,count=re.subn(r'internalField\s+(?:uniform\s+[^;]+|nonuniform\s+List<scalar>\s+\d+\s*\(.*?\))\s*;',
            'internalField uniform '+format(value,'.16g')+';',(case/'0'/name).read_text(),flags=re.S)
        if count!=1:raise ValueError('Expected one scalar internal field: '+name)
        (output/'0'/name).write_text(text)
    mesh=output/'system/blockMeshDict';text=mesh.read_text()
    text,count=re.subn(r'\(8000\s+1\s+1\)','(1 1 1)',text)
    if count!=1:raise ValueError('Expected the known 8000-cell block')
    mesh.write_text(text)
    (output/'increment-probe-inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
    for name,digest in source_hashes.items():
        if hashlib.sha256((case/'0'/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Source CFD fields changed during probe preparation')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply'])
    p.add_argument('case',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();prepare(a.action,a.case,a.output)
