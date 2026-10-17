"""Resume a completed same-mesh case into a fresh generated case without modifying the source."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('action',choices=['plan','apply']);parser.add_argument('source',type=Path);parser.add_argument('target',type=Path)
a=parser.parse_args();source=a.source.resolve(strict=True);target=a.target.resolve(strict=True)
if source==target:raise ValueError('Source and target must differ')
old=json.loads((source/'pilot.json').read_text());new=json.loads((target/'pilot.json').read_text())
for key in ['case','cells','pressure_Pa','length_m']:
 if old[key]!=new[key]:raise ValueError('Restart case mismatch: '+key)
for name in ['points','faces','owner','neighbour','boundary']:
 if (source/'constant/polyMesh'/name).read_bytes()!=(target/'constant/polyMesh'/name).read_bytes():raise ValueError('Restart requires byte-identical mesh: '+name)
times=[]
for p in source.iterdir():
 if p.is_dir():
  try:t=float(p.name)
  except ValueError:continue
  if t>0:times.append((t,p))
if not times:raise ValueError('Source has no positive solution time')
time,path=max(times);control=(target/'system/controlDict').read_text()
end=float(re.search(r'\bendTime\s+([^;]+);',control).group(1))
if not time<end:raise ValueError('End time must exceed source time')
if (target/path.name).exists():raise ValueError('Restart time already exists in target')
receipt={'source':str(source),'source_time_s':time,'target':str(target),'end_time_s':end,
         'source_field_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir() if p.is_file()}}
print(json.dumps(receipt,indent=2))
if a.action=='apply':
 shutil.copytree(path,target/path.name)
 control,count=re.subn(r'\bstartTime\s+[^;]+;',f'startTime {time:.16g};',control)
 if count!=1:raise ValueError('Unexpected startTime')
 with (target/'system/controlDict').open('w',newline='\n') as stream:stream.write(control)
 (target/'restart.json').write_text(json.dumps(receipt,indent=2)+'\n')
