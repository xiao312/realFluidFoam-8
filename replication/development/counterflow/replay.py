"""Plan/copy a previously qualified fine-grid initial state into a new job."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply'])
    parser.add_argument('source',type=Path);parser.add_argument('job',type=Path)
    args=parser.parse_args();source=args.source.resolve();job=args.job.resolve()
    if source.parent!=job.parent or source.parent.name!='jobs':raise ValueError('Expected sibling project job directories')
    if not source.name.isdigit() or not job.name.isdigit() or source==job:raise ValueError('Expected distinct numeric jobs')
    case=source/'paper-cases/gri30';target=job/'paper-cases/gri30'
    if target.parent.exists():raise ValueError('Refusing existing paper-cases')
    for name in ['mapped-field-check.json','parallel-inlets-check.json','inlet-settings.json']:
        json.loads((source/name).read_text())
    if not json.loads((case/'pilot.json').read_text())['velocities_finalized']:raise ValueError('Unfinalized inlet')
    executables=list((source/'openfoam-user/platforms').glob('*/bin/rfReactingFoam'))
    if len(executables)!=1:raise ValueError('Expected one named executable')
    executable=executables[0]
    expected=(source/'solver-product.sha256').read_text().split()[0]
    if digest(executable)!=expected:raise ValueError('Executable hash mismatch')
    directories=['0','constant','system']
    for rank in range(32):directories.extend(['processor'+str(rank)+'/0','processor'+str(rank)+'/constant'])
    for directory in directories:
        resolved=(case/directory).resolve()
        if case.resolve() not in resolved.parents or not resolved.is_dir():raise ValueError('Missing/escaped input '+directory)
    report={'source_job':int(source.name),'target_job':int(job.name),'source_time_s':0,
            'reason':'Replay checked mapped state; unsaved reacting progress cannot be recovered',
            'solver_sha256':expected,'source_executable':str(executable),'ranks':32,
            'end_time_s':1e-5,'checkpoint_interval_s':1e-6,'purge_write':2,'runtime_modifiable':True}
    if args.action=='apply':
        hashes={}
        def copy_checked(src,dst):
            src=Path(src);dst=Path(dst)
            if case.resolve() not in src.resolve().parents:raise ValueError('Escaped source file '+str(src))
            before=digest(src);shutil.copy2(src,dst)
            if digest(dst)!=before or digest(src)!=before:raise ValueError('Copy changed: '+str(src))
            hashes[str(src.relative_to(case))]=before
            return str(dst)
        for directory in directories:shutil.copytree(case/directory,target/directory,copy_function=copy_checked)
        copy_checked(case/'pilot.json',target/'pilot.json')
        control=target/'system/controlDict';text=control.read_text()
        for key,value in [('writeInterval','1e-6'),('purgeWrite','2'),('runTimeModifiable','true')]:
            text,count=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text)
            if count!=1:raise ValueError('Unexpected control '+key)
        control.write_text(text)
        report['source_file_sha256']=hashes
        report['modified_control_sha256']=digest(control)
        (job/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
