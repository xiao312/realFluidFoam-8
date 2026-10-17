"""Measure counterflow history and optional same-mesh serial/MPI field differences."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'figures'))
from foam_fields import centres,field

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('case',type=Path);parser.add_argument('--compare',type=Path)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();case=args.case.resolve(strict=True);xyz=centres(case);count=len(xyz)
radial=np.hypot(xyz[:,0],xyz[:,1]);idx=np.flatnonzero(np.isclose(radial,radial.min(),atol=1e-9,rtol=0));idx=idx[np.argsort(xyz[idx,2])]
times=[]
for path in case.iterdir():
 if path.is_dir():
  try:time=float(path.name)
  except ValueError:continue
  if time>0:times.append((time,path))
times.sort();history=[];last=None
for time,path in times:
 t=field(path/'T',count);oh=field(path/'OH',count);rho=field(path/'rho',count)
 local_peak=int(np.argmax(t[idx]));peak_cell=idx[local_peak]
 row={'time_s':time,'T_max_K':float(t.max()),'T_min_K':float(t.min()),'axis_T_max_K':float(t[idx].max()),
      'axis_T_range_K':float(np.ptp(t[idx])),'axis_peak_z_m':float(xyz[peak_cell,2]),'OH_max':float(oh.max()),
      'rho_min_kg_m3':float(rho.min()),'rho_max_kg_m3':float(rho.max())}
 if last is not None:row['T_relative_linf_change']=float(np.max(np.abs(t-last))/max(float(t.max()),1))
 history.append(row);last=t
if not times:raise ValueError('No positive saved solution times')
result={'case':str(case),'cells':count,'nearest_axis_r_m':float(radial.min()),'history':history,
        'qualification':'Temporal changes alone do not establish steady flame or grid convergence.'}
if args.compare:
 reference=args.compare.resolve(strict=True);otherxyz=centres(reference)
 if xyz.shape!=otherxyz.shape or not np.allclose(xyz,otherxyz,rtol=0,atol=1e-12):raise ValueError('Same-mesh comparison required')
 target=reference/times[-1][1].name
 if not target.is_dir():raise ValueError('Reference lacks matching saved time')
 differences={}
 for name in ['T','p','rho','CH4','O2','CO2','H2O','OH','U']:
  a=field(times[-1][1]/name,count,vector=name=='U');b=field(target/name,count,vector=name=='U')
  differences[name]={'absolute_linf':float(np.max(np.abs(a-b))),'relative_linf':float(np.max(np.abs(a-b))/max(float(np.max(np.abs(b))),1e-12))}
 result['same_mesh_comparison']=differences
 result['temperature_relative_linf_below_1e-5']=differences['T']['relative_linf']<1e-5
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps(result,indent=2))
