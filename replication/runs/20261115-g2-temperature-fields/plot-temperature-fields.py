from pathlib import Path
import re,json,hashlib
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import argparse
parser=argparse.ArgumentParser(description='Render hashed retained G2 temperatures; never advances CFD.')
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--plan',action='store_true')
args=parser.parse_args()
p=args.root.resolve()
if args.plan:
 print(json.dumps({'readOnly':True,'root':str(p),'receipts':[str(p/(name+'-collection.json'))for name in ['schmitt','cavalieri']]}));raise SystemExit(0)

def text(f):
 s=f.read_text();assert 'format      ascii' in s or re.search(r'format\s+ascii',s)
 return re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
def body(f):
 s=text(f);m=re.search(r'\n\s*(\d+)\s*\n\(',s);assert m,f
 return int(m[1]),s[m.end():s.rfind(')')]
def labels(f):
 n,s=body(f);v=np.fromstring(s,sep=' ',dtype=int);assert len(v)==n;return v
def temperature(f,n):
 s=text(f);m=re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;',s,re.S)
 if m:v=np.fromstring(m[2],sep=' ');assert len(v)==int(m[1])==n
 else:
  m=re.search(r'internalField\s+uniform\s+([^;]+);',s);assert m;v=np.full(n,float(m[1]))
 assert np.isfinite(v).all()and(v>0).all();return v

results=[];meshes=[]
for label in ['schmitt','cavalieri']:
 rec=json.loads((p/(label+'-collection.json')).read_text());root=Path(rec['localRoot'])/'cases'/rec['case'];mesh=root/'constant/polyMesh'
 for n,h in rec['inputHashes'].items():assert hashlib.sha256((Path(rec['localRoot'])/n).read_bytes()).hexdigest()==h
 n,s=body(mesh/'points');points=np.array([[float(v)for v in row.split()]for row in re.findall(r'\(([^()]+)\)',s)]);assert points.shape==(n,3)
 nf,s=body(mesh/'faces');faces=[list(map(int,m[1].split()))for m in re.finditer(r'\d+\(([^()]*)\)',s)];assert len(faces)==nf
 owner=labels(mesh/'owner');neighbour=labels(mesh/'neighbour');assert len(owner)==nf;nc=int(max(owner.max(),neighbour.max())+1)
 T=np.full(nc,np.nan);seen=np.zeros(nc,int)
 for rank in range(32):
  ids=labels(root/f'processor{rank}/constant/polyMesh/cellProcAddressing');assert(ids>=0).all()and(ids<nc).all();seen[ids]+=1;T[ids]=temperature(root/f'processor{rank}/0.005/T',len(ids))
 assert (seen==1).all()and np.isfinite(T).all(),np.unique(seen,return_counts=True)
 vertices=[set()for _ in range(nc)]
 for i,face in enumerate(faces):
  vertices[owner[i]].update(face)
  if i<len(neighbour):vertices[neighbour[i]].update(face)
 polygons=[];centers=[]
 for ids in vertices:
  q=points[list(ids)];q=np.unique(np.round(np.column_stack((q[:,0],np.hypot(q[:,1],q[:,2]))),12),axis=0);c=q.mean(axis=0);q=q[np.argsort(np.arctan2(q[:,1]-c[1],q[:,0]-c[0]))];area=.5*np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1));assert area>0 and len(q)>=3;polygons.append(q*1000);centers.append(c*1000)
 centers=np.array(centers);np.savez_compressed(p/(label+'-cell-temperature.npz'),T_K=T,center_x_r_mm=centers,polygons_mm=np.array(polygons,dtype=object))
 i=int(T.argmax());r=dict(case=label,sourceJob=rec['sourceJob'],time_s=.005,CFDStartTime_s=0,cells=nc,Tmin_K=float(T.min()),Tmax_K=float(T.max()),hottestCell=i,hottestCellCenter_x_r_mm=centers[i].tolist(),sourceArchiveSha256=rec['archiveSha256'],mappedCellsExactlyOnce=True,method='Piecewise-constant finite-volume cell temperatures on actual mesh projected to axial/radial polygons; no interpolation, smoothing, triangulation or reconstructed solution.',isInstantaneous=True,isTimeMean=False,scientificAcceptance=False);results.append(r);meshes.append((label,polygons,T));print(json.dumps(r))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.labelsize':11,'axes.titlesize':12})
fig,axs=plt.subplots(2,1,figsize=(12,7),layout='constrained');norm=plt.Normalize(80,3600)
for ax,(label,poly,T),r in zip(axs,meshes,results):
 coll=PolyCollection(poly,array=T,cmap='inferno',norm=norm,edgecolors='none',rasterized=True);ax.add_collection(coll);ax.set(xlim=(0,100),ylim=(0,25),xlabel='Axial position x (mm)',ylabel='Radius r (mm)',title=f"{label.capitalize()} settings | job {r['sourceJob']} | t = 5 ms | instantaneous");ax.set_aspect('equal');ax.set_facecolor('#eeeeee')
fig.colorbar(coll,ax=list(axs),label='Temperature (K)',shrink=.88,pad=.02,extend='both'if any(r['Tmax_K']>3600 or r['Tmin_K']<80 for r in results)else'neither');fig.suptitle('Current G2 temperature fields: actual finite-volume cell data',fontsize=15);fig.savefig(p/'g2-temperature-fields-5ms.png',dpi=180);plt.close(fig)
for label,poly,T in meshes:
 fig,axs=plt.subplots(2,1,figsize=(13,6),layout='constrained',gridspec_kw={'height_ratios':[1,3]})
 for ax,xmax in zip(axs,[400,100]):
  coll=PolyCollection(poly,array=T,cmap='inferno',norm=norm,edgecolors='none',rasterized=True);ax.add_collection(coll);ax.set(xlim=(0,xmax),ylim=(0,25),xlabel='Axial position x (mm)',ylabel='Radius r (mm)');ax.set_aspect('equal');ax.set_facecolor('#eeeeee')
 fig.colorbar(coll,ax=list(axs),label='Temperature (K)',shrink=.85,pad=.02);fig.suptitle(label.capitalize()+' settings | 5 ms instantaneous temperature | full domain and near field',fontsize=14);fig.savefig(p/(label+'-temperature-field-5ms.png'),dpi=180);plt.close(fig)
# A reflected meridional display is labelled explicitly; it adds no CFD cells.
for label,poly,T in meshes:
 fig,ax=plt.subplots(figsize=(12,5),layout='constrained')
 reflected=[q*np.array([1,-1])for q in poly]
 coll=PolyCollection(poly+reflected,array=np.concatenate([T,T]),cmap='inferno',norm=norm,edgecolors='none',rasterized=True)
 ax.add_collection(coll);ax.set(xlim=(0,120),ylim=(-25,25),xlabel='Axial position x (mm)',ylabel='Radial position (mm)');ax.set_aspect('equal')
 ax.set_title(label.capitalize()+' settings | 5 ms instantaneous temperature\nAxisymmetric reflection of the simulated upper half',fontsize=12)
 fig.colorbar(coll,ax=ax,label='Temperature (K)',pad=.02)
 fig.savefig(p/(label+'-temperature-nearfield-5ms.png'),dpi=180);plt.close(fig)
out=dict(plottingCodeSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),at=__import__('datetime').datetime.now().astimezone().isoformat(),cases=results,sharedColorRange_K=[80,3600],image='g2-temperature-fields-5ms.png',imageSha256=hashlib.sha256((p/'g2-temperature-fields-5ms.png').read_bytes()).hexdigest(),scope='Postprocessing existing completed runs only. No new Slurm job or CFD step. Upper radial half-domain, physical aspect ratio. Sampled centerline maximum is not global field maximum.',scientificAcceptance=False);(p/'temperature-field-evidence.json').write_text(json.dumps(out,indent=2)+'\n')
