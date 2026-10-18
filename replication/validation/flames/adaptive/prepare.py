"""Discover or copy a stopped checkpoint with adaptive time controls."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from fields import inspect,times

action,root_arg,key,destination,mode=sys.argv[1:]
assert action in ('plan','apply') and mode in ('smoke','full')
root=Path(root_arg).resolve();dest=Path(destination).resolve()
assert str(dest).startswith(str(root/'jobs')+'/') and not dest.exists()
config=json.loads(Path(__file__).with_name('cases.json').read_text())[key]
source=(root/'jobs'/str(config['origin'])/config['subdir']).resolve()
assert str(source).startswith(str(root/'jobs')+'/') and source.is_dir()
checkpoint=times(source,config['ranks'])[-1]
end=config['end_time'] if mode=='full' else float(checkpoint)+(1e-4 if config['ranks']==8 else 2e-6)
assert end>float(checkpoint)
receipt=dict(key=key,mode=mode,source=str(source),checkpoint=checkpoint,
             destination=str(dest),config=config,end_time=end)
print(json.dumps(receipt))
if action=='plan':sys.exit(0)
validation,_=inspect(source,config['ranks'],checkpoint)
assert validation['cells']==config['cells']
dest.mkdir()
for name in ['system','constant']:
    shutil.copytree(source/name,dest/name)
for rank in range(config['ranks']):
    target=dest/('processor'+str(rank));target.mkdir()
    for name in ['constant',checkpoint]:
        shutil.copytree(source/target.name/name,target/name)
p=dest/'system/controlDict';s=p.read_text()
changes=dict(startFrom='startTime',startTime=checkpoint,stopAt='endTime',endTime=format(end,'.12g'),
             deltaT=config['initial_dt'],adjustTimeStep='yes',maxCo=config['max_co'],maxDeltaT=config['max_dt'],
             writeControl='adjustableRunTime',writeInterval=(config['write_interval'] if mode=='full' else end-float(checkpoint)),
             purgeWrite=0,writePrecision=12,timePrecision=12,runTimeModifiable='true')
for name,value in changes.items():
    pattern=r'\b'+name+r'\s+[^;]+;'
    if re.search(pattern,s):s=re.sub(pattern,name+' '+str(value)+';',s)
    else:s+='\n'+name+' '+str(value)+';\n'
p.write_text(s)
receipt['changes']=changes;receipt['checkpoint_validation']=validation
receipt['input_hashes']={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in dest.rglob('*') if p.is_file()}
(dest/'restart.json').write_text(json.dumps(receipt,indent=2))
