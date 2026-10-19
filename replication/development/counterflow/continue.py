"""Plan/copy a successful fine-grid qualification checkpoint for continuation."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from replay import digest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import inspect,times


def prepare(action,source,job):
    source=source.resolve();job=job.resolve();root=source.parent.parent
    if source.parent!=job.parent or source.parent.name!='jobs':raise ValueError('Expected sibling project jobs')
    if not source.name.isdigit() or not job.name.isdigit() or source==job:raise ValueError('Distinct numeric jobs required')
    case=source/'paper-cases/gri30';target=job/'paper-cases/gri30'
    if target.parent.exists():raise ValueError('Refusing existing destination')
    expected,recorded=(source/'solver-product.sha256').read_text().split()
    executable=root/recorded[len('/work/'):]
    if not recorded.startswith('/work/') or root not in executable.resolve().parents:raise ValueError('Escaped executable')
    if digest(executable)!=expected:raise ValueError('Executable hash mismatch')
    ready=(source/'result.txt').exists() and (source/'result.txt').read_text().startswith('PASS:')
    report={'source_job':int(source.name),'target_job':int(job.name),'dependency_ready':ready,
            'expected_checkpoint_s':1e-5,'source_executable':str(executable),'solver_sha256':expected,
            'ranks':32,'end_time_s':.05,'max_co':.2,'max_delta_t_s':1e-6,
            'checkpoint_interval_s':1e-5,'purge_write':3,'wall_stop_hours':46}
    if action=='plan':return report
    if not ready:raise ValueError('Source replay has not passed endpoint qualification')
    checkpoint=times(case,32)[-1]
    if abs(float(checkpoint)-1e-5)>1e-12:raise ValueError('Expected qualified 10-us endpoint')
    validation,_=inspect(case,32,checkpoint)
    if validation['cells'] not in [816000,888000]:raise ValueError('Unexpected cell count')
    uniform=case/'processor0'/checkpoint/'uniform/time'
    match=re.search(r'\bdeltaT\s+([^;]+);',uniform.read_text()) if uniform.exists() else None
    dt=min(float(match[1]),1e-6) if match else 1e-7
    if dt<=0:raise ValueError('Invalid saved timestep')
    hashes={}
    def copy_checked(src,dst):
        src=Path(src);dst=Path(dst)
        if case.resolve() not in src.resolve().parents:raise ValueError('Escaped source file')
        before=digest(src);shutil.copy2(src,dst)
        if digest(dst)!=before or digest(src)!=before:raise ValueError('Source/copy changed '+str(src))
        hashes[str(src.relative_to(case))]=before
        return str(dst)
    for directory in ['constant','system']:
        shutil.copytree(case/directory,target/directory,copy_function=copy_checked)
    copy_checked(case/'pilot.json',target/'pilot.json')
    for rank in range(32):
        for directory in ['constant',checkpoint]:
            rel='processor'+str(rank)+'/'+directory
            shutil.copytree(case/rel,target/rel,copy_function=copy_checked)
    control=target/'system/controlDict';text=control.read_text()
    changes={'startFrom':'startTime','startTime':checkpoint,'endTime':'.05','stopAt':'endTime',
             'deltaT':format(dt,'.12g'),'writeInterval':'1e-5','purgeWrite':'3','runTimeModifiable':'true'}
    for key,value in changes.items():
        text,count=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text)
        if count!=1:raise ValueError('Unexpected control '+key)
    control.write_text(text)
    report.update(checkpoint=checkpoint,checkpoint_validation=validation,input_hashes=hashes,
                  control_changes=changes,modified_control_sha256=digest(control))
    (job/'continuation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply'])
    parser.add_argument('source',type=Path);parser.add_argument('job',type=Path)
    args=parser.parse_args();print(json.dumps(prepare(args.action,args.source,args.job),indent=2))
