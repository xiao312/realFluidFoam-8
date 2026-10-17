"""Render a dated, explicitly unvalidated comparison of saved initialization fields."""
import hashlib
import json
import os
import sys
from pathlib import Path
import numpy as np
from foam_fields import centres, field, list_body

root, snapshot, out = [Path(p).resolve() for p in sys.argv[1:4]]
if not all(p.is_relative_to(root) for p in (snapshot, out)):
    raise ValueError('Snapshot and output must stay inside project root')
out.mkdir(parents=True, exist_ok=True)
os.environ['MPLCONFIGDIR'] = str(root / 'cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

font = Path('C:/Windows/Fonts/times.ttf')
if font.exists():
    for p in font.parent.glob('times*.ttf'):
        font_manager.fontManager.addfont(str(p))
plt.rcParams.update({'font.family':'Times New Roman' if font.exists() else 'DejaVu Serif',
    'font.size':6,'axes.labelsize':7,'axes.linewidth':.6,'xtick.direction':'in',
    'ytick.direction':'in','lines.linewidth':.8,'mathtext.fontset':'stix'})
atlas = root / 'output/figure-comparison-20261017'
inventory = {i['id']:i for i in json.loads((atlas/'inventory.json').read_text())}
names = ['T','p','rho','Cp','mu','kappa','U','CH4','O2','CO2','H2O','N2','HE']
cases = {}
summary = {'status':'ONE-STEP INITIALIZATION; NOT GRI30 VALIDATION', 'cases':{}}
for key, job, sub in [('oxy-1',124672685,'author-cases'),('oxy-200',124674723,'paper-cases'),('air-100',124674728,'paper-cases')]:
    case = snapshot / f'jobs/{job}/{sub}/one-step'
    xyz = centres(case)
    radial = np.hypot(xyz[:,0],xyz[:,1])
    idx = np.flatnonzero(np.isclose(radial,radial.min(),atol=1e-9,rtol=0))
    idx = idx[np.argsort(xyz[idx,2])]
    results = {}
    for time in ['0.01','0.02']:
        arrays = {n:np.full((len(xyz),3) if n=='U' else len(xyz),np.nan) for n in names}
        seen = np.zeros(len(xyz),dtype=int)
        for rank in range(8):
            proc = case / f'processor{rank}'
            count, body = list_body(proc/'constant/polyMesh/cellProcAddressing')
            ids = np.fromstring(body,sep=' ',dtype=int)
            assert len(ids)==count and ids.min()>=0 and ids.max()<len(xyz)
            seen[ids] += 1
            for n in names:
                arrays[n][ids] = field(proc/time/n,count,vector=n=='U')
        assert np.all(seen==1) and all(np.isfinite(a).all() for a in arrays.values())
        assert max(abs(sum(arrays[n] for n in ['CH4','O2','CO2','H2O','N2'])-1)) < 1e-8
        results[time] = arrays
    _, body = list_body(case/'constant/polyMesh/points')
    pts = np.fromstring(body.replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3)
    cases[key] = dict(xyz=xyz,r=radial,idx=idx,data=results,points=pts,job=job)
    a,b = results['0.01']['T'],results['0.02']['T']
    summary['cases'][key] = dict(job=job,cells=len(xyz),nearest_axis_r_m=float(radial.min()),
        time_s=.02,previous_time_s=.01,peak_T_K=float(b.max()),previous_peak_T_K=float(a.max()),
        T_change_max_K=float(abs(b-a).max()),T_change_rms_K=float(np.sqrt(np.mean((b-a)**2))),
        axis_peak_T_K=float(b[idx].max()),axis_peak_z_m=float(xyz[idx[np.argmax(b[idx])],2]),
        source='59b99e85dd6908fa6ecb89615885ba2eb4a3e936' if key=='oxy-1' else 'fecef1a844def139a6509687ed26310c988ca051')
    np.savez_compressed(out/(key+'-fields.npz'),xyz=xyz,**{'t'+t+'_'+n:v for t,d in results.items() for n,v in d.items()})

def paper_figure(n):
    x0,y0,x1,y1 = inventory[f'2022-fig{n:02}']['crop']
    return plt.figure(figsize=((x1-x0)/72,(y1-y0)/72))

def save(fig,name):
    fig.savefig(out/(name+'.png'),dpi=360)
    fig.savefig(out/(name+'.svg'))
    plt.close(fig)

def panel(ax,c,n,lim=None,color='red',label=None):
    idx=c['idx']; z=c['xyz'][idx,2]
    ax.plot(z,c['data']['0.02'][n][idx],'--',color=color,label=label)
    if lim:
        ax.set_ylim(*lim)
        selected=(z>=ax.get_xlim()[0])&(z<=ax.get_xlim()[1])
        clipped=np.count_nonzero(selected&((c['data']['0.02'][n][idx]<lim[0])|(c['data']['0.02'][n][idx]>lim[1])))
        if clipped:ax.text(.02,.02,f'{clipped} samples outside axis',transform=ax.transAxes,fontsize=4.5,color='#8d3020')

for key,n,xlim in [('oxy-1',9,(.003,.018)),('oxy-200',10,(.002,.0035))]:
    c=cases[key]; fig=paper_figure(n)
    axes=[fig.add_axes(p) for p in [(.145,.555,.307,.4),(.555,.555,.307,.4),(.145,.06,.307,.4),(.555,.06,.307,.4)]]
    for ax,letter in zip(axes,'abcd'):
        ax.set(xlim=xlim,xlabel='z [m]'); ax.text(-.13,1,letter+')',transform=ax.transAxes,fontweight='bold')
    a,b,cax,d=axes
    a.set_ylabel('Temperature [K]');panel(a,c,'T',(250,2100 if n==9 else 2400))
    a.text(.03,.93,'ONE-STEP, t = 20 ms\nNOT GRI30 VALIDATION',transform=a.transAxes,va='top',fontsize=5,color='#8d3020')
    b.set_ylabel('Mass fraction'); b.set_ylim(-.02,1.02)
    for species,col in [('CH4','black'),('O2','#0080ff'),('CO2','#00aaaa'),('H2O','#00a000')]:panel(b,c,species,color=col,label=species)
    b.legend(fontsize=5,frameon=False);b.text(.02,.03,'OH absent from one-step mechanism',transform=b.transAxes,fontsize=4.5)
    for ax,left,right,l1,l2,y1,y2 in [(cax,'rho','Cp',(.19,.71) if n==9 else (35,165),(1100,2750) if n==9 else (1100,3600),'Density [kg/m$^3$]','$c_p$ [J/kg-K]'),(d,'mu','kappa',(0,6.5e-5) if n==9 else (0,7.5e-5),(.03,.145) if n==9 else (.055,.20),'Viscosity [kg/m-s]','Conductivity [W/m-K]')]:
        ax.set_ylabel(y1);panel(ax,c,left,l1);tw=ax.twinx();tw.set(xlim=xlim,ylabel=y2);panel(tw,c,right,l2)
    save(fig,f'2022-fig{n:02}-interim')
c=cases['air-100'];fig=paper_figure(11)
a=fig.add_axes((.17,.55,.66,.4));b=fig.add_axes((.17,.055,.66,.4))
for ax in (a,b):ax.set(xlim=(.0105,.012),xlabel='z [m]')
a.set_ylabel('Temperature [K]');panel(a,c,'T',(200,2300));tw=a.twinx();tw.set(xlim=a.get_xlim(),ylabel='Density [kg/m$^3$]');panel(tw,c,'rho',(10,120))
a.text(.03,.92,'ONE-STEP, t = 20 ms\nNOT GRI30 VALIDATION',transform=a.transAxes,va='top',fontsize=5,color='#8d3020')
b.set(ylabel='Mass fraction',ylim=(-.02,1.02))
for n,col in [('CH4','black'),('O2','#0080ff'),('CO2','#00aaaa'),('H2O','#00a000')]:panel(b,c,n,color=col,label=n)
b.legend(fontsize=5,frameon=False);save(fig,'2022-fig11-interim')

fig=paper_figure(8)
for i,key in enumerate(['oxy-1','oxy-200']):
    c=cases[key];xyz=c['xyz'];r=c['r'];p=c['points'];f=c['data']['0.02']
    # Polyhedral moment arithmetic introduces picometre radial differences
    # between nominally identical rings; group well below the mesh spacing.
    rr=np.unique(np.round(r,10));zz=np.unique(np.round(xyz[:,2],10))
    order=np.lexsort((np.round(r,10),np.round(xyz[:,2],10)))
    shape=(len(zz),len(rr)); assert np.prod(shape)==len(xyz)
    re=np.unique(np.round(np.hypot(p[:,0],p[:,1]),12));ze=np.unique(np.round(p[:,2],12))
    assert len(re)==len(rr)+1 and len(ze)==len(zz)+1
    ax=fig.add_axes((.27,.55-i*.49,.51,.375));upper=2000 if i==0 else 2400
    m=ax.pcolormesh(re,ze,f['T'][order].reshape(shape),cmap='hot',vmin=200,vmax=upper,shading='flat')
    rg=np.linspace(rr[0],rr[-1],len(rr));zg=np.linspace(zz[0],zz[-1],300)
    velocity=[]
    for component in (0,2):
        raw=f['U'][order,component].reshape(shape)
        along_r=np.array([np.interp(rg,rr,row) for row in raw])
        velocity.append(np.array([np.interp(zg,zz,along_r[:,j]) for j in range(len(rg))]).T)
    ax.streamplot(rg,zg,*velocity,color='#a1eeee',density=.7,linewidth=.4,arrowsize=.5)
    ax.set(xlabel='r [m]',ylabel='z [m]',xlim=(0,re[-1]),ylim=(0,ze[-1]))
    ax.text(.03,.95,'ONE-STEP, 20 ms',transform=ax.transAxes,va='top',fontsize=5,bbox=dict(facecolor='white',alpha=.8,edgecolor='none',pad=1))
    cb=fig.add_axes((.45,.955-i*.49,.33,.025));fig.colorbar(m,cax=cb,orientation='horizontal',extend='max' if f['T'].max()>upper else 'neither')
    fig.text(.19,.955-i*.49,('a)' if i==0 else 'b)')+' T [K]',fontsize=8)
fig.text(.52,.085,'INITIALIZATION ONLY; NOT GRI30 VALIDATION',ha='center',fontsize=4.5)
save(fig,'2022-fig08-interim')

fig,axes=plt.subplots(1,3,figsize=(10,3.2),constrained_layout=True)
for ax,(key,c) in zip(axes,cases.items()):
    idx=c['idx'];z=c['xyz'][idx,2]*1000
    for t,col in [('0.01','#888888'),('0.02','#c73522')]:ax.plot(z,c['data'][t]['T'][idx],color=col,label=f'{float(t)*1000:g} ms')
    ax.set(title=key,xlabel='Axial position [mm]',ylabel='Temperature [K]',ylim=(250,2500));ax.legend()
fig.suptitle('One-step initialization history; full domain, nearest-axis cells',fontsize=10)
save(fig,'counterflow-history')
data=np.genfromtxt(root/'state/checkpoint-review-20261017/phi110-10us-fields.csv',delimiter=',',names=True)
fig,axes=plt.subplots(2,2,figsize=(7,4.8),constrained_layout=True);x=data['x_m']*1000
for ax in axes.flat:ax.set_xlabel('x [mm]');ax.axvspan(.9,1.1,color='#eeeeee')
axes[0,0].plot(x,data['T'],color='#c73522');axes[0,0].axhline(3000,color='gray',ls=':');axes[0,0].set_ylabel('Temperature [K]')
axes[0,1].plot(x,data['p']/1e6);axes[0,1].axhline(10.1325,color='gray',ls=':',label='Nominal');axes[0,1].set_ylabel('Pressure [MPa]');axes[0,1].legend()
for n in ['CH4','O2']:axes[1,0].plot(x,data[n],label=n)
axes[1,0].plot(x,10*data['OH'],label='OH x 10');axes[1,0].set_ylabel('Mass fraction');axes[1,0].legend()
axes[1,1].plot(x,data['Ux']);axes[1,1].set_ylabel('Axial velocity [m/s]')
fig.suptitle('Phi = 1.10, 10 microseconds: ignition diagnostic, NOT a flame-speed result',fontsize=10)
save(fig,'premixed-diagnostic')

style=ParagraphStyle('body',fontName='Helvetica',fontSize=10,leading=14)
width,height=landscape(A3);pdf=canvas.Canvas(str(out/'realfluidfoam-interim-comparison.pdf'),pagesize=(width,height))
def text(s,x,y,w):
    p=Paragraph(s,style);_,h=p.wrap(w,height);p.drawOn(pdf,x,y-h)
def picture(path,x,y,w,h):
    im=ImageReader(str(path));iw,ih=im.getSize();scale=min(w/iw,h/ih)
    pdf.drawImage(im,x+(w-iw*scale)/2,y+(h-ih*scale)/2,width=iw*scale,height=ih*scale)
for n in [8,9,10,11,12]:
    pdf.setFont('Helvetica-Bold',19);pdf.drawString(40,height-40,f'2022 Figure {n}: interim comparison, 17 October 2026')
    note='ONE-STEP INITIALIZATION at 20 ms, 11,200 cells. The paper uses developed GRI30 flames. No replication or error score is claimed; original axis limits can hide current out-of-range values.' if n!=12 else 'Figure 12 remains unavailable: the right-hand plot is a transient ignition diagnostic, not a flame-speed comparison. 621/4000 cells are exactly 3000 K; pressure has not returned to nominal.'
    text(note,40,height-60,width-80)
    picture(atlas/f'originals/2022-fig{n:02}.png',40,170,width/2-60,height-300)
    picture(atlas/f'captions/2022-fig{n:02}.png',40,45,width/2-60,100)
    name=f'2022-fig{n:02}-interim' if n!=12 else 'premixed-diagnostic'
    picture(out/(name+'.png'),width/2+15,170,width/2-55,height-300)
    text('Published figure and original caption (owner-supplied PDF)',40,155,width/2-60)
    text('Current saved simulation fields; no reference curve digitization or fit',width/2+15,155,width/2-60)
    detail='Jobs: oxyfuel 1 atm 124672685; oxyfuel 200 atm 124674723; air 100 atm 124674728. OH is absent from the one-step mechanism and is not plotted.' if n!=12 else 'Job 124674599, phi=1.10, t=10 microseconds, 4000 cells. Gray band marks the original ignition kernel. No laminar burning velocity has been extracted.'
    text(detail,width/2+15,115,width/2-60);pdf.showPage()
pdf.setFont('Helvetica-Bold',19);pdf.drawString(40,height-40,'Counterflow initialization: full-domain history')
picture(out/'counterflow-history.png',40,170,width-80,height-250)
text('10 and 20 ms snapshots. These views supplement the paper-scale plots, whose narrow axes can omit the current peak. No temporal or mesh convergence is claimed. All cases remain in one-step initialization.',40,135,width-80)
pdf.showPage();pdf.save()
summary['plots']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.png')}
summary['pdf_sha256']=hashlib.sha256((out/'realfluidfoam-interim-comparison.pdf').read_bytes()).hexdigest()
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary['cases'],indent=2))
