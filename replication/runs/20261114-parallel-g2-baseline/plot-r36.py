"""Replay the retained R36b limited-linear DF comparison; no CFD or publication."""
from pathlib import Path
import argparse,csv,json,sys,hashlib,os
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('export',type=Path);parser.add_argument('output',type=Path);parser.add_argument('references',type=Path);parser.add_argument('--plan',action='store_true');args=parser.parse_args()
root=args.export.resolve();p=args.output.resolve();references=args.references.resolve()
runtime=json.loads((root/'build/contact-srk-r20/build-qualification.json').read_text());assert runtime['source']=='c6d486e9136180fcbc781d4889b83b3785bdbce3'
qualification=json.loads((root/'build/contact-muscl-r36/solver-qualification.json').read_text());assert qualification['source']=='70cc5f57161896cabc8413d2a93436f1c9ed8f3b'
for fig in [5,6]:assert (references/f'schmitt-fig{fig}-nonconservative-vector-traces.csv').is_file()
if args.plan:
 print(json.dumps({'readOnly':True,'source':qualification['source'],'job':'128042346','figures':[5,6],'time_s':.02,'output':str(p),'scientificAcceptance':False}));raise SystemExit(0)
p.mkdir(parents=True,exist_ok=False)
os.environ.setdefault('MPLCONFIGDIR',str(p.parent/'.r36-plot-cache'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/figures'));from foam_fields import field
app={'sha256':qualification['solverSha256']};sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
plt.rcParams.update({'font.family':'Times New Roman','font.size':9,'axes.labelsize':10,'xtick.labelsize':7.2,'ytick.labelsize':7.2,'legend.fontsize':7.2,'axes.linewidth':.6,'figure.dpi':180,'mathtext.fontset':'cm'})
comparisons=[]
for fig,kind,nxs in [(5,'oxygen',['2','4','6']),(6,'mixture',['0.00001','2','4'])]:
 paper=list(csv.DictReader((references/f'schmitt-fig{fig}-nonconservative-vector-traces.csv').open()))
 computed={};input_hashes={};startup={}
 for nx in nxs:
  case=root/f'cases/contact-muscl-r36b-full-{kind}-{nx}'
  if not case.exists():continue
  receipt=json.loads((case/'double-flux-startup-check.json').read_text());assert receipt['endTime_s']==.02
  xy=list(csv.DictReader((case/'initial-thermo.csv').open()));x=np.array([float(a['x'])for a in xy]);assert len(x)==400 and np.max(abs(np.diff(x)-.01))<1e-10
  fields={n:field(case/'0.02'/n,400,vector=n=='U')for n in ['T','rho','p','U','H2','O2']}
  computed[nx]=dict(x_m=x,rho_kg_m3=fields['rho'],T_K=fields['T'],p_MPa=fields['p']/1e6,U_m_s=fields['U'][:,0],Y_O2=fields['O2'],Y_H2=fields['H2']);startup[nx]=receipt
  input_hashes[nx]={n:sha(case/'0.02'/n)for n in fields}
  raw=p/f'contact-muscl-r36b-{kind}-{nx}-profiles.csv'
  with raw.open('w',newline='',encoding='utf8')as f:
   wr=csv.writer(f);wr.writerow(computed[nx]);wr.writerows(zip(*computed[nx].values()))
 quantities=['rho_kg_m3','T_K','p_MPa','U_m_s'];yl=['Density [kg m⁻³]','Temperature [K]','Pressure [MPa]','Velocity [m s⁻¹]'];lims=[(0,1200),(100,300)if fig==5 else(60,140),(5.96,6.02),(9.2,10.5)]
 for selected in [nxs,*[[nx]for nx in computed]]:
  f,axs=plt.subplots(2,2,figsize=(8.75,5.18));f.subplots_adjust(left=.08,right=.99,bottom=.08,top=.98,wspace=.25,hspace=.21)
  for ax,q,ylabel,lim in zip(axs.flat,quantities,yl,lims):
   for nx,color,marker in zip(nxs,['black','red','blue'],['o','s','^']):
    if nx not in selected:continue
    ref=[a for a in paper if a['panelQuantity']==q and float(a['nx'])==float(nx)];rx=np.array([float(a['x_m'])for a in ref]);ry=np.array([float(a['value'])for a in ref])
    label='$n_x=\\epsilon$'if float(nx)==1e-5 else '$n_x='+nx+'$'
    ax.plot(rx,ry,color=color,lw=.75,label='Paper '+label)
    if nx not in computed:continue
    data=computed[nx]
    step=1 if fig==5 or q in quantities[:2]else 4
    ax.plot(data['x_m'][::step],data[q][::step],ls='none',color=color,marker=marker,markerfacecolor='none',markeredgewidth=.6,markersize=3.4,label='Ours '+label)
    if selected==nxs:
     overlap=(rx>=data['x_m'].min())&(rx<=data['x_m'].max());error=np.interp(rx[overlap],data['x_m'],data[q])-ry[overlap]
     comparisons.append(dict(figure=fig,nx=float(nx),quantity=q,matchedReferencePoints=int(overlap.sum()),uncoveredReferencePoints=int((~overlap).sum()),RMS_absolute=float(np.sqrt(np.mean(error**2))),maximum_absolute=float(np.max(abs(error))),normalization='Units from quantity column; no relative division by near-zero reference',rawGraphicalReference=True))
   ax.set_xlim((.05,.6)if fig==5 or q in quantities[:2]else(-1,3));ax.set_ylim(lim);ax.set_xlabel('x [m]',labelpad=1);ax.set_ylabel(ylabel,labelpad=2);ax.tick_params(direction='in',top=True,right=True,length=2.5,pad=2)
   ax.set_yticks({'rho_kg_m3':[0,300,600,900,1200],'T_K':[100,150,200,250,300]if fig==5 else[60,80,100,120,140],'p_MPa':[5.96,5.98,6,6.02],'U_m_s':[9.5,10,10.5]}[q])
  handles,labels=axs[0,0].get_legend_handles_labels()
  order=[i for i,l in enumerate(labels)if l.startswith('Paper')]+[i for i,l in enumerate(labels)if l.startswith('Ours')]
  axs[0,0].legend([handles[i]for i in order],[labels[i]for i in order],loc='upper right',frameon=False,ncol=2,handlelength=1.6,columnspacing=.7)
  suffix='all'if selected==nxs else'nx-'+selected[0]
  f.savefig(p/f'schmitt-fig{fig}-contact-muscl-r36b-{suffix}.png');plt.close(f)
 provenance=dict(completedWidths=list(computed),missingFinalTimeWidths=[n for n in nxs if n not in computed],fullBatchPassed=len(computed)==3 and all(r['numericalStartupPassed']for r in startup.values()),job='128042346',caseSource=runtime['source'],binarySource=qualification['source'],binarySHA256=app['sha256'],runtimeProducts=runtime['products'],figure=fig,time_s=.02,startTime_s=0,method='OpenFOAM8 isolated inviscid MC-limited MUSCL HLLC double-flux SSPRK3, executing SRK library',paper='AVBP TTGC/nonconservative artificial viscosity; plotted continuous reference traces',paperReference=sha(references/f'schmitt-fig{fig}-nonconservative-vector-traces.csv'),startupChecks=startup,rawFieldHashes=input_hashes,scientificAcceptance=False,limitations=['Methods differ; this is not the reacting FGM G2 solver','Quasi-conservative energy defect is reported in startup receipt; not exact energy conservation','Fig6 paper pressure/velocity cover x[-1,3], our computed domain[-2,2]; no extrapolation'],plotPolicy='Paper lines; ours raw cell markers. No smoothing or fit. Reference graphical stroke uncertainty retained in CSV.')
 (p/f'schmitt-fig{fig}-contact-muscl-r36b-evidence.json').write_text(json.dumps(provenance,indent=2)+'\n')
(p/'schmitt-contact-muscl-r36b-comparison-metrics.json').write_text(json.dumps(comparisons,indent=2)+'\n')
print(json.dumps(comparisons,indent=2))
