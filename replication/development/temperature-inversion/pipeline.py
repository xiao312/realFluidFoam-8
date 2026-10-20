"""Submit a bounded fresh-start sweep behind build, property and smoke gates."""
import argparse,json,re,subprocess
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['plan','apply'])
p.add_argument('root',type=Path);p.add_argument('release',type=Path)
p.add_argument('library_job')
a=p.parse_args();root=a.root.resolve(strict=True);release=a.release.resolve(strict=True)
if not str(root).endswith('/FlamePilot/trials/realfluidfoam') or root/'releases' not in release.parents:
    raise ValueError('Use a source release under the controlled trial root')
if not a.library_job.isdigit():raise ValueError('Numeric library job required')
sha=(release/'SOURCE_REVISION').read_text().strip()
if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('Missing immutable source SHA')
module=release/'replication/development/temperature-inversion'
conditions=['phi%03d'%v for v in range(90,141,5)]
plan=dict(source=sha,library_job=a.library_job,conditions=conditions,
    initialization='generated_original_zero',end_time_s=0.0003,
    gates=['library build','SRK/PR small increments','SRK/PR property inversion',
           'ideal-mixture small increments and 8-rank 100-ns smoke'],
    smoke_ranks=[8,32],sweep_ranks=8,sweep_hours_per_job=12,
    maximum_sweep_core_hours=11*8*12,
    note='32-rank smoke is diagnostic only; no 32-rank production permission')
print(json.dumps(plan,indent=2))
ledger=root/'results'/('temperature-pipeline-'+sha[:12]+'-'+a.library_job+'.json')
if ledger.exists():raise ValueError('Already submitted; inspect '+str(ledger))
if a.action=='plan':raise SystemExit(0)
plan['jobs']={}
def submit(name,cpus,minutes,dependencies,script,args):
    command=['sbatch','--parsable','--partition=kshcnormal','--nodes=1','--ntasks=1',
      '--cpus-per-task='+str(cpus),'--time='+str(minutes),'--kill-on-invalid-dep=yes',
      '--dependency=afterok:'+':'.join(dependencies),'--chdir='+str(root),
      '--job-name='+name,'--output='+str(root/'logs'/('%x-%j.out')),
      '--error='+str(root/'logs'/('%x-%j.err')),str(script),*map(str,args)]
    result=subprocess.run(command,capture_output=True,text=True,check=True)
    job=result.stdout.strip().split(';')[0]
    if not job.isdigit():raise ValueError('Unexpected sbatch response: '+result.stdout)
    plan['jobs'][name]=dict(job_id=job,dependencies=dependencies,command=command)
    ledger.write_text(json.dumps(plan,indent=2)+'\n')
    print(name,job,flush=True)
    return job
image=root/'images/openfoam8-rootfs-7d4e96e0b1a9'
tests=[]
for stage in ['properties-increments','properties']:
    tests.append(submit('rf-T-'+stage,2,20,[a.library_job],
       release/'replication/environment/job.sh',[root,image,release,'validation',a.library_job,stage]))
smokes={}
for ranks in [8,32]:
    smokes[ranks]=submit('rf-T-smoke-'+str(ranks),ranks,60,tests,module/'gated-job.sh',
        [root,release,a.library_job,ranks,'phi110','build','none',*tests])
for key in conditions:
    submit('rf-T-full-'+key,8,720,[smokes[8]],module/'gated-job.sh',
        [root,release,a.library_job,8,key,'full',smokes[8],*tests])
print('Ledger:',ledger)
