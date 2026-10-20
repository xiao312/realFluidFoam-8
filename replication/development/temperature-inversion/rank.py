"""Pin one MPI rank to one verified allocated CPU, then replace this process."""
import json
import os
from pathlib import Path
import sys

receipt=Path(sys.argv[1])
cpus=json.loads((receipt/'allocation-cpus.json').read_text())
rank=int(os.environ['OMPI_COMM_WORLD_LOCAL_RANK'])
size=int(os.environ['OMPI_COMM_WORLD_LOCAL_SIZE'])
if size!=len(cpus) or not 0<=rank<size or len(set(cpus))!=size:
    raise ValueError('MPI rank count differs from the recorded CPU allocation')
available=os.sched_getaffinity(0)
if not set(cpus)<=available:raise ValueError('MPI changed the permitted CPU allocation')
os.sched_setaffinity(0,{cpus[rank]})
if os.sched_getaffinity(0)!={cpus[rank]}:raise RuntimeError('CPU assignment verification failed')
(receipt/f'rank-{rank}-cpu.json').write_text(json.dumps(dict(rank=rank,cpu=cpus[rank],pid=os.getpid()))+'\n')
os.execv(sys.argv[2],sys.argv[2:])
