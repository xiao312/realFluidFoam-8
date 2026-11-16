"""Plot measured homogeneous-root Hs discontinuities; never bridge the jump."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path);a=p.parse_args()
 datasets=[];inputs={}
 for kind in ['c03','c05']:
  point_file=a.results/(kind+'-point.json');point=json.loads(point_file.read_text());inputs[point_file.name]=hashlib.sha256(point_file.read_bytes()).hexdigest();curves={}
  for pressure in ['captured','nominal']:
   file=a.results/(kind+'-'+pressure+'-cold-properties.csv');raw=file.read_bytes();inputs[file.name]=hashlib.sha256(raw).hexdigest();rows=list(csv.DictReader(raw.decode().splitlines()));T=np.array([float(r['T_K'])for r in rows]);H=np.array([float(r['Hs_J_kg'])for r in rows]);recovered=np.array([float(r['T_recovered_K'])for r in rows]);order=np.argsort(T)
   if not np.isfinite(np.r_[T,H,recovered]).all()or np.max(abs(T-recovered))>1e-9:raise ValueError('Property samples not finite/original-temperature queries')
   curves[pressure]=(T[order],H[order])
  datasets.append((kind,point,curves))
 report={'schema':'captured-Hs-root-gap-plot/v1','inputs':inputs,'source_fit':False,'CFD_steps':0,'scientificAcceptance':False,'jump_bridge':'none','results':[]}
 if a.out is None:print(json.dumps({'readOnly':True,**report},indent=2));return
 a.out.mkdir(parents=True,exist_ok=False)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.linewidth':.8,'lines.linewidth':1.5,'savefig.dpi':180})
 fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
 for (kind,point,curves),pair in zip(datasets,axes):
  t0=point['temperature_K'];target=point['storedHs_J_kg'];left,right=pair
  for pressure,color,label in [('captured','#bf483b','Captured pressure'),('nominal','#2476a8','Nominal 5.61 MPa')]:
   T,H=curves[pressure];jumps=(abs(np.diff(H))>2e4)&(np.diff(T)<1e-3);yp=H.copy()/1000;yp[1:][jumps]=np.nan
   left.plot(T,yp,'-',color=color,label=label);left.plot(T,H/1000,'.',color=color,ms=3)
  T,H=curves['captured'];sel=abs(T-t0)<=1.01e-5;delta=(T[sel]-t0)*1e6
  right.plot(delta,H[sel]/1000,'o',color='#bf483b',ms=5,label='Actual library samples')
  for ax in pair:
   ax.axhline(target/1000,color='#202830',ls='--',label='Stored Hs = Ha − Hf');ax.set_ylabel('Sensible enthalpy [kJ/kg]');ax.grid(alpha=.2);ax.legend(fontsize=9,loc='best')
  left.set_xlabel('Temperature [K]');left.set_title(kind.upper()+': same composition, two pressures')
  right.set_xlabel('T − captured T [µK]');right.set_xlim(-15,15);right.set_title(f"Captured p={point['pressure_Pa']/1e6:.4f} MPa, T={t0:.6f} K")
  idx=np.flatnonzero(sel);jump=float(np.max(H[idx])-np.min(H[idx]));report['results'].append({'case':kind,'capturedPressure_Pa':point['pressure_Pa'],'capturedT_K':t0,'sampledHsSpanWithin10microK_J_kg':jump,'targetHs_J_kg':target,'originalStateRestartAllowed':False})
 fig.suptitle('G2 rejected-state replay · selected homogeneous SRK root · no CFD restart',fontsize=14)
 for suffix in ['png','svg']:fig.savefig(a.out/('captured-Hs-gaps.'+suffix))
 plt.close(fig);report['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in a.out.iterdir()};(a.out/'evidence.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
