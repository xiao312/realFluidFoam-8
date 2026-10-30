"""Render labelled computed profiles beside the published full/reduced curves."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS={'T':'#166cbb','rho_PRVTA':'#166cbb','Y_O2':'#2472b3','Y_CH4':'#be513f','Y_H2O':'#1a8b66','Y_CO2':'#9554aa','Y_CO':'#b38b16','Y_OH':'#cf573d','Y_H2':'#326ab5'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--profile',type=Path,action='append',required=True)
    parser.add_argument('--label',action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if len(args.profile)!=len(args.label):parser.error('Each profile requires one label.')
    ref=json.loads(args.reference.read_text())
    profiles=[np.genfromtxt(p,delimiter=',',names=True) for p in args.profile]
    for data in profiles:
        aliases={'Z_mass_mixing':'Z','Z_Bilger':'Z','T_K':'T'}
        data.dtype.names=tuple(aliases.get(name,name) for name in data.dtype.names)
        assert data.size > 2 and 'Z' in data.dtype.names
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.labelsize':12,'axes.linewidth':0.8,'savefig.dpi':200})
    fig,axes=plt.subplots(2,2,figsize=(11.0,7.8),layout='constrained')
    panels=[('Temperature [K]',['T'],(0,4000)),('PR-VTA density [kg/m³]',['rho_PRVTA'],(0,65)),
            ('Major-species mass fraction',['Y_O2','Y_CH4','Y_H2O','Y_CO2','Y_CO'],(0,1)),
            ('Minor-species mass fraction',['Y_OH','Y_H2'],(0,0.1))]
    metrics={}
    for ax,(ylabel,quantities,ylim) in zip(axes.flat,panels):
        for quantity in quantities:
            color=COLORS[quantity]
            reference=np.array(ref['series']['gri30'][quantity]['points'])
            reduced=np.array(ref['series']['reduced'][quantity]['points'])
            label=quantity.removeprefix('Y_')
            ax.plot(reference[:,0],reference[:,1],color=color,lw=1.5,label=f'{label}: paper GRI30')
            ax.plot(reduced[:,0],reduced[:,1],color=color,lw=1,ls='--',alpha=.55,label=f'{label}: paper reduced')
            for index,(data,name) in enumerate(zip(profiles,args.label)):
                if quantity not in data.dtype.names:continue
                z=np.asarray(data['Z']);v=np.asarray(data[quantity]);mask=np.isfinite(z)&np.isfinite(v)
                z=z[mask];v=v[mask];order=np.argsort(z);z=z[order];v=v[order]
                z,unique=np.unique(z,return_index=True);v=v[unique]
                ax.plot(z,v,color=color,lw=.9,ls=':' if index==0 else '-.',marker=['o','s','^'][index%3],
                        markevery=max(1,len(z)//17),markersize=3.5,markerfacecolor='white',label=f'{label}: {name}')
                # Compare on a fixed uniform abscissa; raw path vertex density must not weight the RMS.
                sample=np.linspace(max(0,float(z.min())),min(1,float(z.max())),501)
                observed=np.interp(sample,z,v);expected=np.interp(sample,reference[:,0],reference[:,1]);error=observed-expected
                span=float(np.ptp(reference[:,1]));key=f'{name}/{quantity}'
                metrics[key]={'rms':float(np.sqrt(np.mean(error**2))),'max_abs':float(np.max(abs(error))),
                    'rms_fraction_of_reference_span':float(np.sqrt(np.mean(error**2))/span),'sample_count':len(sample),
                    'Z_range':[float(sample[0]),float(sample[-1])],'computed_peak':float(v.max()),'paper_peak':float(reference[:,1].max())}
        ax.set(xlabel='Mixture fraction Z',ylabel=ylabel,xlim=(0,1),ylim=ylim)
        ax.grid(alpha=.18);ax.legend(fontsize=7,ncol=2,frameon=False)
        if quantities==['rho_PRVTA'] and not any('rho_PRVTA' in d.dtype.names for d in profiles):
            ax.text(.45,.7,'Computed PR-VTA density pending',transform=ax.transAxes,ha='center',fontsize=10)
    fig.suptitle('Müller & Pfitzner (2015), Figure 2 — labelled development comparison',fontsize=13)
    args.output.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output/'comparison.png');fig.savefig(args.output/'comparison.svg');plt.close(fig)
    result={'schema':'muller-figure2-comparison-v1','reference_sha256':hashlib.sha256(args.reference.read_bytes()).hexdigest(),
        'profiles':[{'path':str(p),'label':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,name in zip(args.profile,args.label)],
        'metrics':metrics,'scientific_acceptance':'not_assigned','method':'501 uniform Z samples, interpolation inside computed coverage only'}
    (args.output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
