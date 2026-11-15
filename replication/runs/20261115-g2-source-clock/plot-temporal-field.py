from pathlib import Path
import argparse,json
parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
record=json.loads(args.collection.read_text());entry=next(e for e in record['entries']if e['condition']=='cavalieri');root=args.collection.parent
if not args.apply:
 print(json.dumps({'readOnly':True,'field':str(root/'cavalieri-fixedTime.npz'),'out':str(args.out),'time_s':entry['time_s'],'scientificAcceptance':False}));raise SystemExit(0)
import os
os.environ['MPLCONFIGDIR']=str((args.out.parent/'matplotlib-cache').resolve())
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
a=np.load(root/'cavalieri-fixedTime.npz',allow_pickle=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11});fig,axes=plt.subplots(2,1,figsize=(11,6.8),layout='constrained');norm=plt.Normalize(80,3600)
for ax,lim,title in zip(axes,[(0,200,0,25),(0,20,0,6)],['Whole chamber','Near-injector detail']):
 c=PolyCollection(list(a['polygons_mm']),array=a['T_K'],cmap='inferno',norm=norm,edgecolors='none',rasterized=True);ax.add_collection(c);ax.set(xlim=lim[:2],ylim=lim[2:],xlabel='Axial position x (mm)',ylabel='Radius r (mm)',title=title);ax.set_aspect('equal');ax.set_facecolor('#ededed')
fig.colorbar(c,ax=list(axes),label='Temperature (K)',shrink=.82,pad=.02)
fig.suptitle(f"Cavalieri G2 | fresh {1000*entry['time_s']:g} ms | fixed relaxation 10 µs | max timestep 0.5 µs",fontsize=13)
fig.supxlabel(f"Actual finite-volume cells; no smoothing. Tmax {a['T_K'].max():.0f} K. Startup field; developed mean and conservation qualification pending.",fontsize=9)
fig.savefig(args.out,dpi=180);plt.close(fig)
