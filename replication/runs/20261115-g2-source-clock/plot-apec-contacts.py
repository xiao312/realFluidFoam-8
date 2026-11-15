from pathlib import Path
import argparse,csv,json,hashlib,sys
parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
if not args.apply:
 print(json.dumps({'readOnly':True,'collection':str(args.collection),'reference':str(args.reference),'out':str(args.out),'figures':6}));raise SystemExit(0)
import os
os.environ['MPLCONFIGDIR']=str((args.out/'matplotlib-cache').resolve())
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/figures'))
from foam_fields import field
record=json.loads(args.collection.read_text());root=Path(record['directory']);out=args.out;out.mkdir(parents=True,exist_ok=True);paper=list(csv.DictReader(args.reference.open()));computed={}
plt.rcParams.update({'font.family':'Times New Roman','font.size':9,'axes.labelsize':10,'xtick.labelsize':7.2,'ytick.labelsize':7.2,'legend.fontsize':7.2,'axes.linewidth':.6,'figure.dpi':180,'mathtext.fontset':'cm'})
for entry in record['rows']:
 case=root/entry['case'];xy=list(csv.DictReader((case/'initial-thermo.csv').open()));n=len(xy);x=np.array([float(a['x']) for a in xy]);f={k:field(case/entry['timeName']/k,n,vector=k=='U') for k in ['rho','T','p','U']};computed[entry.get('label','nx'+str(entry['nx']))]={'x_m':x,'rho_kg_m3':f['rho'],'T_K':f['T'],'p_MPa':f['p']/1e6,'U_m_s':f['U'][:,0],'entry':entry}
quantities=['rho_kg_m3','T_K','p_MPa','U_m_s'];labels=['Density [kg m⁻³]','Temperature [K]','Pressure [MPa]','Velocity [m s⁻¹]'];limits=[(0,1200),(100,300),(5.96,6.02),(9.2,10.5)]
metrics=[]
for key,data in computed.items():
 nx=data['entry']['nx']
 for full in [False,True]:
  fig,axes=plt.subplots(2,2,figsize=(8.75,5.18));fig.subplots_adjust(left=.09,right=.98,bottom=.13,top=.92,wspace=.3,hspace=.3)
  for ax,q,label,lim in zip(axes.flat,quantities,labels,limits):
   ref=[a for a in paper if a['panelQuantity']==q and float(a['nx'])==nx];rx=np.array([float(a['x_m'])for a in ref]);ry=np.array([float(a['value'])for a in ref]);ax.plot(rx,ry,'k-',lw=.8,label='Paper, 20 ms');ax.plot(data['x_m'],data[q],ls='none',marker='o',mfc='none',mec='#276683',mew=.6,ms=3.4,label=f"APEC, {1000*data['entry']['time_s']:.0f} ms")
   ax.set(xlim=(float(data['x_m'].min()),float(data['x_m'].max())) if full else (.05,.6),xlabel='x [m]',ylabel=label);ax.tick_params(direction='in',top=True,right=True,length=2.5,pad=2)
   if not full:ax.set_ylim(lim)
   else:
    values=np.r_[ry,data[q]];lo=values.min();hi=values.max();pad=max((hi-lo)*.07,1e-3);ax.set_ylim(lo-pad,hi+pad)
   if not full and data['entry']['time_s']==.02:
    mask=(rx>=data['x_m'].min())&(rx<=data['x_m'].max());error=np.interp(rx[mask],data['x_m'],data[q])-ry[mask];metrics.append(dict(nx=nx,quantity=q,RMS_absolute=float(np.sqrt(np.mean(error**2))),sameTime=True))
  axes[0,0].legend(frameon=False,loc='upper right');rc=data['entry']['result']['solverExit'];state='completed' if rc==0 else ('last written partial; payload timeout' if rc==124 else 'last written partial; case failed')
  fig.suptitle(f'Schmitt Fig. 5 | APEC oxygen nx={nx}, cells={len(data["x_m"])} | {state}',fontsize=10)
  fig.text(.09,.025,'Full-range companion exposes excursions.'if full else 'Paper axis limits; see full-range companion for excursions.',fontsize=8)
  name=f"{args.out.name.replace('-plots','')}-{key}-{'full-range'if full else'paper-limits'}.png";fig.savefig(out/name);plt.close(fig)
 for q in quantities:data[q]=data[q].tolist()
 data['x_m']=data['x_m'].tolist()
(out/'profiles.json').write_text(json.dumps(computed,indent=2)+'\n',encoding='utf8');(out/'comparison-metrics.json').write_text(json.dumps({'metrics':metrics,'scientificAcceptance':False,'partialTimesExcludedFromRMS':True,'referenceSha256':hashlib.sha256(args.reference.read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf8');print(json.dumps({'figures':2*len(computed),'metrics':metrics}))
