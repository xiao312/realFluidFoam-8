from pathlib import Path
import csv,json,sys,hashlib,os
import numpy as np
if len(sys.argv) not in (4,5) or (len(sys.argv)==5 and sys.argv[4]!='--plan'):
 raise SystemExit('Use plot-r30.py EXPORT_DIR OUTPUT_DIR REFERENCES_DIR [--plan]')
p=Path(sys.argv[2]).resolve();references=Path(sys.argv[3]).resolve()
w=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(w/'replication/validation/figures'));from foam_fields import field
root=Path(sys.argv[1]).resolve();runtime=json.loads((root/'results/contact-projection-region-r30/solver-qualification.json').read_text());assert runtime['source']=='f91825f462f45a31aff63c79c670eb91431e6c61';assert runtime['parentRuntimeManifestSha256']=='c2d8c7e3f6128da51ca5e3e5fd682ff086ccca46c872197ab97d86beb17b3b25';app={'sha256':runtime['solverSha256']};sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
for figure in (5,6):
 if not (references/f'schmitt-fig{figure}-nonconservative-vector-traces.csv').is_file():
  raise SystemExit(f'Missing paper-reference CSV for figure{figure}')
for kind,widths in [('oxygen',['2','4','6']),('mixture',['0.00001','2','4'])]:
 for nx in widths:
  case=root/f'cases/contact-projection-region-r30-full-{kind}-on-{nx}'
  if case.exists():
   for name in ['T','p','rho','U','H2','O2']:
    if not (case/'0.02'/name).is_file():raise SystemExit(f'Incomplete completed-case field:{case/name}')
if '--plan' in sys.argv:
 print(json.dumps({'readOnly':True,'export':str(root),'output':str(p),'references':str(references),'source':runtime['source'],'scientificAcceptance':False},indent=2));raise SystemExit(0)
p.mkdir(parents=True,exist_ok=True)
os.environ['MPLCONFIGDIR']=str(p/'.mpl-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'Times New Roman','font.size':9,'axes.labelsize':10,'xtick.labelsize':7.2,'ytick.labelsize':7.2,'legend.fontsize':7.2,'axes.linewidth':.6,'figure.dpi':180,'mathtext.fontset':'cm'})
comparisons=[]
for fig,kind,nxs in [(5,'oxygen',['2','4','6']),(6,'mixture',['0.00001','2','4'])]:
 paper=list(csv.DictReader((references/f'schmitt-fig{fig}-nonconservative-vector-traces.csv').open()))
 computed={};input_hashes={};startup={}
 for nx in nxs:
  case=root/f'cases/contact-projection-region-r30-full-{kind}-on-{nx}'
  if not case.exists():continue
  receipt=json.loads((root/f'results/contact-projection-region-r30/full-{kind}-on-{nx}-result.json').read_text());assert receipt['startTime']==0 and receipt['targetTime']==.02 and receipt['solverExit']==0
  xy=list(csv.DictReader((case/'initial-thermo.csv').open()));x=np.array([float(a['x'])for a in xy]);assert len(x)==400 and np.max(abs(np.diff(x)-.01))<1e-10
  fields={n:field(case/'0.02'/n,400,vector=n=='U')for n in ['T','rho','p','U','H2','O2']}
  computed[nx]=dict(x_m=x,rho_kg_m3=fields['rho'],T_K=fields['T'],p_MPa=fields['p']/1e6,U_m_s=fields['U'][:,0],Y_O2=fields['O2'],Y_H2=fields['H2']);startup[nx]=receipt
  input_hashes[nx]={n:sha(case/'0.02'/n)for n in fields}
  raw=p/f'contact-projection-r30-{kind}-{nx}-profiles.csv'
  with raw.open('w',newline='',encoding='utf8')as f:
   wr=csv.writer(f);wr.writerow(computed[nx]);wr.writerows(zip(*computed[nx].values()))
 if not computed:continue
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
  f.savefig(p/f'schmitt-fig{fig}-contact-projection-r30-{suffix}.png')
  if selected==nxs:
   for ax,q,lim in zip(axs.flat,quantities,lims):
    values=np.concatenate([computed[n][q]for n in selected if n in computed]);lo=min(lim[0],float(values.min()));hi=max(lim[1],float(values.max()));pad=(hi-lo)*.04;ax.set_ylim(lo-pad,hi+pad);ax.set_yticks(np.linspace(lo,hi,5))
   f.savefig(p/f'schmitt-fig{fig}-contact-projection-r30-all-unclipped.png')
  plt.close(f)
 provenance=dict(completedWidths=list(computed),missingFinalTimeWidths=[n for n in nxs if n not in computed],fullBatchNormalExit=len(computed)==3,job='128033548',caseSource=runtime['source'],binarySource=runtime['source'],binarySHA256=app['sha256'],runtimeQualification=runtime,figure=fig,time_s=.02,startTime_s=0,method='OpenFOAM8 PIMPLE, author inner energy/density-time correction, named upwind rho interpolation, all-region nonreacting energy projection, executing SRK library',paper='AVBP TTGC/nonconservative artificial viscosity; plotted continuous reference traces',paperReference=sha(references/f'schmitt-fig{fig}-nonconservative-vector-traces.csv'),startupChecks=startup,rawFieldHashes=input_hashes,scientificAcceptance=False,limitations=['Methods differ; this is not the reacting FGM G2 solver','Per-equation energy projection adjustments are logged; no cumulative conservation qualification is claimed','Same property coefficients but different stabilization/transport; all-region projection is nonreacting diagnostic only','Fig6 paper pressure/velocity cover x[-1,3], our computed domain[-2,2]; no extrapolation'],plotPolicy='Paper lines; ours raw cell markers. No smoothing or fit. Reference graphical stroke uncertainty retained in CSV.')
 (p/f'schmitt-fig{fig}-contact-projection-r30-evidence.json').write_text(json.dumps(provenance,indent=2)+'\n')
(p/'schmitt-contact-projection-r30-comparison-metrics.json').write_text(json.dumps(comparisons,indent=2)+'\n')
print(json.dumps(comparisons,indent=2))
