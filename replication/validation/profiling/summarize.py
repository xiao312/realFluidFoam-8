"""Summarize per-rank timestep timers, excluding startup and the forced write."""
import csv
import json
from pathlib import Path
import statistics
import sys

job=Path(sys.argv[1])
result={}
for case in sorted(job.glob('*-timed')):
    files=list(case.glob('processor*/rf-profile.csv'))
    if not files:
        continue
    ranks={}
    for file in files:
        rows=list(csv.reader(file.open()))
        times=sorted(set(float(r[0]) for r in rows))
        assert len(times)==5,(file,times)
        middle=set(times[1:-1])
        sections={}
        for t,section,seconds in rows:
            if float(t) in middle:
                sections.setdefault(section,[]).append(float(seconds))
        ranks[file.parent.name]={k:statistics.mean(v) for k,v in sections.items()}
    means={k:statistics.mean(r[k] for r in ranks.values()) for k in next(iter(ranks.values()))}
    result[case.name]=dict(ranks=len(ranks),mean_seconds=means,
        percent_of_rank_time={k:100*v/means['step'] for k,v in means.items()},
        rank_seconds=ranks,
        note='Steps 2-4 only; nested sections overlap parents; wall times include MPI waits.')
print(json.dumps(result,indent=2))
