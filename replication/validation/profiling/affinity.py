"""Inspect or repair rank CPU affinity inside one existing Slurm allocation."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket

SOLVERS={'rfEnergyReactingFoam','rfTrackedReactingFoam','rfCanteraBridgeFoam','rfCanteraTransportFoam'}


def discover(job,ranks):
    found=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            if proc.stat().st_uid!=os.geteuid():continue
            arguments=(proc/'cmdline').read_bytes().split(b'\0')
            if not arguments or Path(os.fsdecode(arguments[0])).name not in SOLVERS:continue
            if b'-case' not in arguments:continue
            case=arguments[arguments.index(b'-case')+1].decode()
            if case!=f'/work/jobs/{job}/case':continue
            environment=(proc/'environ').read_bytes().split(b'\0')
            selected=[row.split(b'=',1)[1] for row in environment if row.startswith(b'OMPI_COMM_WORLD_LOCAL_RANK=')]
            if len(selected)!=1:raise ValueError('Missing unique local MPI rank')
            rank=int(selected[0])
            threads={int(t.name):sorted(os.sched_getaffinity(int(t.name))) for t in (proc/'task').iterdir()}
            found.append(dict(pid=int(proc.name),rank=rank,start_ticks=(proc/'stat').read_text().split()[21],threads=threads))
        except (FileNotFoundError,ProcessLookupError):continue
    if sorted(row['rank'] for row in found)!=list(range(ranks)):
        raise ValueError('Live solver ranks do not match the declared decomposition')
    return sorted(found,key=lambda row:row['rank'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply']);parser.add_argument('root',type=Path);parser.add_argument('job')
    args=parser.parse_args()
    if not args.job.isdigit() or os.environ.get('SLURM_JOB_ID')!=args.job:
        raise ValueError('Run in a control step of the named existing Slurm job')
    root=args.root.resolve(strict=True);case=(root/'jobs'/args.job/'case').resolve(strict=True);case.relative_to(root)
    match=re.search(r'\bnumberOfSubdomains\s+(\d+)\s*;',(case/'system/decomposeParDict').read_text())
    if not match or int(match[1]) not in (8,32):raise ValueError('Only declared 8/32-rank cases are supported')
    ranks=int(match[1]);before=discover(args.job,ranks)
    cpus=sorted({cpu for row in before for mask in row['threads'].values() for cpu in mask})
    if len(cpus)!=ranks:raise ValueError('Observed CPU union differs from rank count; refusing to guess allocation')
    assignments=[dict(pid=row['pid'],rank=row['rank'],cpu=cpus[row['rank']]) for row in before]
    if args.action=='apply':
        # Complete discovery/validation precedes every mutation. Check process
        # identity again so a recycled PID cannot receive this job's assignment.
        for row in before:
            proc=Path('/proc')/str(row['pid'])
            if (proc/'stat').read_text().split()[21]!=row['start_ticks']:
                raise ValueError('Process identity changed after discovery')
        for row in before:
            for tid in row['threads']:os.sched_setaffinity(tid,{cpus[row['rank']]})
        after=discover(args.job,ranks)
        if any(mask!=[cpus[row['rank']]] for row in after for mask in row['threads'].values()):
            raise ValueError('Affinity verification failed; inspect the affected live job')
    else:after=None
    print(json.dumps(dict(action=args.action,job=args.job,host=socket.gethostname(),
        observed_utc=datetime.now(timezone.utc).isoformat(),cpu_union=cpus,before=before,
        assignments=assignments,after=after,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        fields_or_time_modified=False),indent=2))


if __name__=='__main__':main()
