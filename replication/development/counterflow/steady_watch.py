"""Run a bounded MPI continuation and request checkpointed stops."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from replay import digest
from steady_metrics import compare,inspect,species
from fields import times


def save(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\n');temporary.replace(path)


def request_stop(case,receipt,reason):
    control=case/'system/controlDict';before=control.read_bytes()
    text,count=re.subn(r'\bstopAt\s+[^;]+;','stopAt writeNow;',before.decode())
    if count!=1:raise ValueError('Expected one stopAt entry')
    temporary=control.with_suffix('.next');temporary.write_text(text);temporary.replace(control)
    save(receipt,{'reason':reason,'requested_at_epoch_s':time.time(),
                  'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':digest(control)})


def freeze_reference(case,checkpoint,destination,ranks=32):
    if destination.exists():raise ValueError('Refusing existing convergence reference')
    names=['T','U','rho','p',*species(case)];hashes={}
    for rank in range(ranks):
        proc='processor'+str(rank);target=destination/proc/checkpoint;target.mkdir(parents=True)
        for name in names:
            source=case/proc/checkpoint/name;before=digest(source);shutil.copy2(source,target/name)
            if digest(target/name)!=before or digest(source)!=before:raise ValueError('Reference changed while copying')
            hashes[proc+'/'+checkpoint+'/'+name]=before
    save(destination/'hashes.json',hashes)


def run(job,executable):
    cfg=json.loads((job/'continuation.json').read_text());case=job/'paper-cases/gri30'
    reference=job.parent/str(cfg['source_job'])/'paper-cases/gri30';old=cfg['checkpoint']
    last_checked=float(old);passes=0;reason=None;last=None;started=time.monotonic()
    save(job/'steady-monitor.json',{'state':'waiting_for_physical_window','reference_time_s':float(old),
                                 'minimum_window_s':.01,'required_passes':3,'check_separation_s':.001})
    with (job/'solver.log').open('w') as output,(job/'solver-stderr.log').open('w') as errors:
        process=subprocess.Popen(['mpirun','--mca','btl','self,vader,tcp','-np','32',str(executable),'-case',str(case),'-parallel'],stdout=output,stderr=errors)
        try:
            while process.poll() is None:
                elapsed=time.monotonic()-started
                if reason is None and elapsed>=cfg['wall_stop_hours']*3600:
                    reason='wall_time_boundary';request_stop(case,job/'stop-request.json',reason)
                saved=times(case,32)
                # Skip the newest directory: another rank may still be writing it.
                candidate=saved[-2] if len(saved)>1 else saved[0]
                if reason is None and float(candidate)-float(old)>=.01-1e-12 and float(candidate)-last_checked>=.001-1e-12:
                    last=compare(case,reference,old,candidate);last_checked=float(candidate)
                    passes=passes+1 if last['candidate'] else 0
                    last['consecutive_passes']=passes
                    save(job/('steady-check-'+candidate+'.json'),last)
                    save(job/'steady-monitor.json',last)
                    if passes>=3:
                        reason='steady_candidate';request_stop(case,job/'stop-request.json',reason)
                    elif not last['candidate']:
                        reference=job/'convergence-reference'/candidate
                        freeze_reference(case,candidate,reference);old=candidate
                time.sleep(30)
            if process.returncode!=0:raise RuntimeError('MPI solver failed with exit '+str(process.returncode))
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=60)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            raise
    checkpoint=times(case,32)[-1];health,_=inspect(case,32,checkpoint)
    final=compare(case,reference,old,checkpoint)
    candidate=reason=='steady_candidate' and final['candidate']
    summary={'state':'steady_candidate' if candidate else 'checkpointed_not_converged',
             'stop_reason':reason or 'physical_time_ceiling','elapsed_solver_wall_s':time.monotonic()-started,
             'checkpoint':checkpoint,'health':health,'convergence':final,'consecutive_passes':passes,
             'qualification':'Numerical steady candidate is not scientific acceptance'}
    save(job/'steady-result.json',summary)
    (job/'result.txt').write_text(('PASS: steady candidate; further scientific validation required' if candidate else
                                 'PARTIAL: saved continuation checkpoint; steady convergence not established')+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':run(Path(sys.argv[1]),Path(sys.argv[2]))
