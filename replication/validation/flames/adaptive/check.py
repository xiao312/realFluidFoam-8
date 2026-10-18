"""Check a saved endpoint and quantify changes from the restart state."""
import json
import math
from pathlib import Path
import sys
from fields import inspect,times

case=Path(sys.argv[1]);meta=json.loads((case/'restart.json').read_text())
ranks=meta['config']['ranks'];latest=times(case,ranks)[-1]
summary,final=inspect(case,ranks,latest)
assert abs(float(latest)-meta['end_time'])<1e-10
assert summary['cells']==meta['config']['cells']
_,initial=inspect(case,ranks,meta['checkpoint'],require_rho=False)
summary['change_from_restart']={k:dict(max_abs=max(abs(a-b) for a,b in zip(final[k],initial[k])),
    rms=math.sqrt(sum((a-b)**2 for a,b in zip(final[k],initial[k]))/len(final[k]))) for k in ['T','CH4','OH']}
summary['qualification']='finite normalized endpoint only; temporal accuracy and convergence not established'
(case/'endpoint-check.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary))
