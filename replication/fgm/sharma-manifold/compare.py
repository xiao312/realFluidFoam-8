"""Render computed manifold and slices with auditable paper-raster samples."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def trace(image, box, rule, limits, legend=None):
    rgb=np.array(Image.open(image).convert('RGB'));h,w,_=rgb.shape
    xx,yy=np.meshgrid(np.arange(w),np.arange(h))
    mask=rule(rgb)&(xx>=box[0])&(xx<=box[2])&(yy>=box[1])&(yy<=box[3])
    if legend:
        mask&=~((xx>=legend[0])&(xx<=legend[2])&(yy>=legend[1])&(yy<=legend[3]))
    output=[]
    for x in range(box[0]+2,box[2]-1):
        ys=np.flatnonzero(mask[:,x])
        if len(ys):
            output.append([(x-box[0])/(box[2]-box[0]),limits[1]-(np.median(ys)-box[1])/(box[3]-box[1])*(limits[1]-limits[0])])
    return np.array(output)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--paper-assets',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((a.run/'receipt.json').read_text())
    for name,digest in receipt['files'].items():
        assert hashlib.sha256((a.run/name).read_bytes()).hexdigest()==digest, 'Result identity mismatch: '+name
    data=np.load(a.run/'manifold.npz');slices=json.loads((a.run/'slices.json').read_text())
    species=list(data['species']);figure1=a.paper_assets/'sharma2023-fig-1-paper.png';figure2=a.paper_assets/'sharma2023-fig-2-paper.png'
    red=lambda v:(v[:,:,0]>170)&(v[:,:,1]<120)&(v[:,:,2]<120)
    # Require blue excess over green so antialiased red is not misread as pink.
    pink=lambda v:(v[:,:,0]>180)&(v[:,:,1]>30)&(v[:,:,1]<165)&(v[:,:,2]>130)&(v[:,:,2].astype(int)>v[:,:,1].astype(int)+40)
    blue=lambda v:(v[:,:,2]>170)&(v[:,:,0]>15)&(v[:,:,0]<130)&(v[:,:,1]<130)
    cyan=lambda v:(v[:,:,2]>170)&(v[:,:,0]<80)&(v[:,:,1]>105)&(v[:,:,1]<220)
    colors=['#00a6ee','#4332fa','#df1313','#f04eae'];rules=[cyan,blue,red,pink]
    reference={};errors={}
    for field,box,limits in [('T',[87,16,480,377],[0,4000]),('Y_CO2',[618,16,1007,377],[-.05,.35])]:
        reference[field]={}
        for f,rule in zip(['0.1','0.2','0.4','0.6'],rules):
            values=trace(figure2,box,rule,limits,[box[0]+1,box[1]+1,box[0]+265,box[1]+129])
            reference[field][f]=values.tolist()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.linewidth':.8})
    width,height=Image.open(figure2).size
    fig,axes=plt.subplots(1,2,figsize=(width/100,height/100),layout='constrained')
    for ax,field,label,limits in zip(axes,['T','Y_CO2'],['Temperature [K]','CO₂ mass fraction'],[(0,4000),(-.05,.35)]):
        for f,color in zip(['0.1','0.2','0.4','0.6'],colors):
            c=np.array(slices[f]['c']);v=np.array([np.nan if x is None else x for x in slices[f][field]])
            ax.plot(c,v,color=color,lw=1.6,label='f='+f)
            ref=np.asarray(reference[field][f]);ax.plot(ref[::10,0],ref[::10,1],linestyle='none',marker='o',ms=3,mfc='white',color=color)
            good=np.isfinite(v)
            if good.sum()>1 and len(ref):
                # Only compare within adjacent populated cells; never bridge missing coverage.
                hi=np.searchsorted(c,ref[:,0],side='right').clip(1,len(c)-1)
                lo=hi-1
                keep=(ref[:,0]>=c[0])&(ref[:,0]<=c[-1])&good[lo]&good[hi]
                if keep.any():
                    x=ref[keep,0];left=lo[keep];right=hi[keep]
                    weight=(x-c[left])/(c[right]-c[left])
                    prediction=(1-weight)*v[left]+weight*v[right];error=prediction-ref[keep,1]
                    errors[field+'/'+f]={'RMS':float(np.sqrt(np.mean(error**2))),'samples':int(keep.sum()),'actual_Z':slices[f]['actual_Z']}
        ax.set(xlim=(0,1),ylim=limits,xlabel='Progress variable c',ylabel=label)
        ax.legend(frameon=False,fontsize=9)
    fig.suptitle('Sharma Fig. 2 · lines: our unsteady-manifold diagnostic; hollow markers: paper',fontsize=11)
    fig.savefig(a.out/'figure2.svg');fig.savefig(a.out/'figure2.png',dpi=180);plt.close(fig)
    width,height=Image.open(figure1).size
    fig,axes=plt.subplots(1,2,figsize=(width/100,height/100),layout='constrained')
    z=data['Z'];c=data['c'];tz=data['T']
    for level in [.2,.4,.6,.8]:
        col=np.argmin(abs(c-level));axes[0].plot(z,tz[:,col],color='#4f46ff',lw=1,label=f'c={c[col]:.2f}')
    axes[0].plot(data['burnt_Z'],data['burnt_T'],color='#df1313',lw=1.8,label='c=1 equilibrium reference')
    burnt_reference=trace(figure1,[93,11,508,388],red,[0,3800],[300,15,430,70])
    axes[0].plot(burnt_reference[::10,0],burnt_reference[::10,1],linestyle='none',marker='o',mfc='white',color='#222',ms=3,label='Paper c=1')
    axes[0].set(xlim=(0,1),ylim=(0,3800),xlabel='Mixture fraction f',ylabel='Temperature [K]');axes[0].legend(fontsize=7,frameon=False)
    sp_colors={'CH4':'#e51616','O2':'#4633f4','CO2':'#222','CO':'#6755ff','H2O':'#13b331','OH':'#ed20dc'}
    # Burnt species remain an explicitly labelled equilibrium reference, not a solved steady branch.
    for name,color in sp_colors.items():axes[1].plot(data['burnt_Z'],data['burnt_Y'][:,species.index(name)],color=color,label=name)
    axes[1].set(xlim=(0,1),ylim=(0,1),xlabel='Mixture fraction f',ylabel='Burnt-reference mass fraction');axes[1].legend(fontsize=8,frameon=False,ncol=2)
    fig.suptitle('Sharma Fig. 1 · computed diagnostic; c=1 is equilibrium, not qualified steady flamelet',fontsize=11)
    fig.savefig(a.out/'figure1.svg');fig.savefig(a.out/'figure1.png',dpi=180);plt.close(fig)
    # Retain each physical path as a separate curve. Sorting several paths by c
    # does not make them a unique manifold; this view exposes that distinction.
    equilibrium=np.load(a.run/'equilibrium-initial.npz')
    denominator=equilibrium['Y'][:,species.index('CO2')]+equilibrium['Y'][:,species.index('CO')]
    trajectories=[];stability=[]
    for branch in receipt['branches']:
        if branch['status']=='failed':continue
        chi=int(branch['chi_st']);raw=np.load(a.run/f'chi-{chi}.npz')
        progress=np.divide(raw['Y'][:,:,species.index('CO2')]+raw['Y'][:,:,species.index('CO')],
            denominator[None,:],out=np.full_like(raw['T'],np.nan),where=denominator[None,:]>1e-12)
        trajectories.append((chi,raw,progress))
        i=int(np.argmin(abs(raw['t']-0.9*raw['t'][-1])))
        stability.append({'chi_st':chi,'final_Tmax_K':float(raw['T'][-1].max()),
            'last_interval_s':float(raw['t'][-1]-raw['t'][i]),
            'max_profile_T_change_K':float(abs(raw['T'][-1]-raw['T'][i]).max())})
    fig,axes=plt.subplots(1,2,figsize=tuple(v/100 for v in Image.open(figure2).size),layout='constrained')
    styles=['-','--',':']
    for ax,field,label,limits in zip(axes,['T','Y_CO2'],['Temperature [K]','CO₂ mass fraction'],[(0,4000),(-.05,.35)]):
        for f,color in zip(['0.1','0.2','0.4','0.6'],colors):
            for (chi,raw,progress),style in zip(trajectories,styles):
                j=int(np.argmin(abs(raw['Z']-float(f))))
                values=raw['T'][:,j] if field=='T' else raw['Y'][:,j,species.index('CO2')]
                ax.plot(progress[:,j],values,color=color,ls=style,lw=1.2,label='f='+f if style=='-' else None)
            ref=np.asarray(reference[field][f])
            ax.plot(ref[::10,0],ref[::10,1],ls='none',marker='o',ms=3,mfc='white',color=color)
        ax.set(xlim=(0,1),ylim=limits,xlabel='Progress variable c',ylabel=label)
        ax.legend(frameon=False,fontsize=9)
    fig.suptitle('Separate physical paths · solid χ=10⁴; dashed 3×10⁵; dotted 2×10⁶ s⁻¹ · circles: paper',fontsize=10)
    fig.savefig(a.out/'figure2-paths.svg');fig.savefig(a.out/'figure2-paths.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=tuple(v/100 for v in Image.open(figure1).size),layout='constrained')
    for (chi,raw,_),style in zip(trajectories,styles):
        axes[0].plot(raw['Z'],raw['T'][-1],ls=style,lw=1.5,label=f'χ={chi:g}, t=1 ms')
    axes[0].plot(data['burnt_Z'],data['burnt_T'],color='#777',ls='-.',lw=1,label='HP equilibrium reference')
    axes[0].plot(burnt_reference[::10,0],burnt_reference[::10,1],ls='none',marker='o',mfc='white',color='#222',ms=3,label='Paper burnt line')
    axes[0].set(xlim=(0,1),ylim=(0,3800),xlabel='Mixture fraction f',ylabel='Temperature [K]');axes[0].legend(frameon=False,fontsize=7)
    low=trajectories[0][1]
    for name,color in sp_colors.items():axes[1].plot(low['Z'],low['Y'][-1,:,species.index(name)],color=color,label=name)
    axes[1].set(xlim=(0,1),ylim=(0,1),xlabel='Mixture fraction f',ylabel='Solved mass fraction · χ=10⁴ s⁻¹');axes[1].legend(frameon=False,fontsize=8,ncol=2)
    fig.suptitle('Actual final flamelet profiles · distinct from equilibrium and the remapped manifold',fontsize=11)
    fig.savefig(a.out/'figure1-solved.svg');fig.savefig(a.out/'figure1-solved.png',dpi=180);plt.close(fig)
    report={'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'input_receipt_sha256':hashlib.sha256((a.run/'receipt.json').read_bytes()).hexdigest(),
            'reference_method':'Colour-selected raster samples with manually registered axes; median pixel per x. Legend masked. Approximate digitization, ~1 pixel axis uncertainty.',
            'reference_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [figure1,figure2]},
            'figure2_paper_data':reference,'figure1_burnt_T_paper_data':burnt_reference.tolist(),'figure2_metrics':errors,
            'table_coverage_fraction':receipt['table_coverage_fraction'],'branch_ambiguity_K':receipt['max_T_spread_in_c_bins_K'],
            'final_profile_stability':stability,
            'metric_scope':'Figure 2 RMS describes the first mixed-path remap, not a qualified unique manifold. Raw paths are rendered separately without sorting or smoothing.',
            'limitation':receipt['limitation'],'scientific_acceptance':False}
    (a.out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['figure2_paper_data','figure1_burnt_T_paper_data']},indent=2))


if __name__=='__main__':main()
