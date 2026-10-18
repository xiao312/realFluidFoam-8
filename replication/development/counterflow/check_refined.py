"""Validate a decomposed mapped initial state or completed fine-grid qualification."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'validation/flames/adaptive'))
from fields import inspect,times

case=Path(sys.argv[1]);mode=sys.argv[2]
assert mode in ['initial','endpoint']
time='0' if mode=='initial' else times(case,32)[-1]
report,_=inspect(case,32,time,require_rho=mode=='endpoint')
assert report['cells'] in [816000,888000]
if mode=='endpoint':assert abs(float(time)-1e-5)<1e-12
report['qualification']='finite normalized fields only; mapped warm start is not conservative or converged'
print(json.dumps(report,indent=2))
