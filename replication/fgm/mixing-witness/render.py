"""Render retained physical mixing witnesses; never integrate or change a table."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(input_dir, table_dir):
    receipt=json.loads((input_dir/'receipt.json').read_text())
    assert receipt['schema']=='physical-mixing-witness/v1' and not receipt['audit_only']
    assert sha(table_dir/'receipt.json')==receipt['input_receipt_sha256']
    assert sha(table_dir/'table.npz')==receipt['input_table_sha256']
    with np.load(table_dir/'table.npz') as archive:
        table={key:archive[key] for key in archive.files}
    records=[];hashes={'receipt.json':sha(input_dir/'receipt.json'),'table.npz':sha(table_dir/'table.npz')}
    for case in receipt['cases']:
        folder=input_dir/case['name']
        initial=json.loads((folder/'initial-state.json').read_text())
        assert sha(folder/'initial-state.json')==case['initial_state_sha256']
        report=json.loads((folder/'physical-receipt.json').read_text())
        assert sha(folder/'physical-receipt.json')==case['physical_receipt_sha256']
        assert sha(folder/'chemical-tail.npz')==report['trajectory_sha256']
        with np.load(folder/'chemical-tail.npz') as archive:
            times,states=archive['time_s'].copy(),archive['states'].copy()
        assert times[0]==0 and np.all(np.diff(times)>0) and np.isfinite(states).all()
        records.append((case,initial,report,times,states))
        for name in ['initial-state.json','physical-receipt.json','chemical-tail.npz']:
            hashes[case['name']+'/'+name]=sha(folder/name)
    return receipt,table,records,hashes


def slice_at(table,z):
    axis=table['Z'];i=min(len(axis)-2,max(0,int(np.searchsorted(axis,z))-1))
    weight=(z-axis[i])/(axis[i+1]-axis[i])
    return (1-weight)*table['states'][i]+weight*table['states'][i+1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--table-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    receipt,table,records,hashes=load(args.input,args.table_dir)
    if args.out is None:
        print(json.dumps({'plan':True,'job_id':receipt['job_id'],'cases':len(records),'input_hashes':hashes}));return
    args.out.mkdir(exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR',str(args.out/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':11,'axes.titlesize':12,'axes.labelsize':11,
        'lines.linewidth':1.8,'axes.spines.top':False,'axes.spines.right':False})
    colors=['#2675b8','#d47526','#6953a3','#159886']
    labels=['Rich cap + CH4: Z=0.4853','Rich cap + CH4: Z=0.5050',
            'Same Z/C: rich-cap path','Same Z/C: lean-cap path']
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for index,(_,initial,_,times,states) in enumerate(records):
        co=6+initial['species_names'].index('CO')
        for ax,column in zip(axes.flat,[1,0,4,co]):
            ax.plot(times*1e3,states[:,column],color=colors[index],label=labels[index])
            ax.set_xscale('symlog',linthresh=1e-6)
            ax.set_xlabel('Elapsed physical time (ms); symlog below 1 ns')
            ax.grid(alpha=.2)
    for ax,label in zip(axes.flat,['Temperature (K)','Cwater = YCO2 + YCO + YH2O',
                                 'Chemical source Scwater (kg m⁻³ s⁻¹)','CO mass fraction']):
        ax.set_ylabel(label)
    axes[1,0].set_yscale('symlog',linthresh=1)
    axes[0,0].legend(fontsize=9)
    fig.suptitle('Fresh HP-conserving mixtures: actual full-chemistry relaxation')
    for suffix in ['png','svg']:fig.savefig(args.out/('physical-trajectories.'+suffix),dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for index,(case,_,_,_,states) in enumerate(records):
        col=0 if index<2 else 1
        for row,field in [(0,1),(1,4)]:
            ax=axes[row,col]
            ax.plot(states[:,0],states[:,field],color=colors[index],label=labels[index])
            ax.scatter(states[0,0],states[0,field],color=colors[index],s=35,marker='o')
            ax.scatter(states[-1,0],states[-1,field],color=colors[index],s=35,marker='x')
            if index<3:
                sliced=slice_at(table,case['Z'])
                ax.plot(sliced[:,0],sliced[:,field],color=colors[index] if index<2 else '#444444',
                        linestyle='--',linewidth=1.3,label='Existing table at same Z' if index==2 else 'Existing table, matching Z')
            ax.set_xlabel('Raw Cwater = YCO2 + YCO + YH2O');ax.grid(alpha=.2)
    axes[0,0].set_title('Mixing states outside the current upper envelope')
    axes[0,1].set_title('Same initial Z/C; different composition and h')
    for ax in axes[0]:ax.set_ylabel('Temperature (K)');ax.legend(fontsize=8)
    for ax in axes[1]:ax.set_ylabel('Chemical source Scwater (kg m⁻³ s⁻¹)');ax.set_yscale('symlog',linthresh=1)
    fig.suptitle('Coordinate closure diagnostic: circles = initial; crosses = final')
    for suffix in ['png','svg']:fig.savefig(args.out/('coordinate-closure.'+suffix),dpi=170)
    plt.close(fig)
    page='''<!doctype html><meta charset="utf-8"><title>Physical mixing witnesses</title>
<style>body{font:17px/1.55 system-ui,sans-serif;max-width:1200px;margin:40px auto;padding:0 20px;color:#21303c}img{max-width:100%}pre{white-space:pre-wrap;background:#f2f4f6;padding:20px}</style>
<h1>Physical mixing witnesses</h1><p>Four fresh constant-pressure adiabatic GRI reactors at 5.61 MPa,
initialized by mass- and enthalpy-conserving mixtures of retained actual states.
No table bound or source was modified. These are diagnostics, not CFD or scientific acceptance.</p>
<p>The same-Z/C pair has a small but nonzero enthalpy difference. Its divergence demonstrates
non-uniqueness in a two-coordinate composition closure; it does not prove that a Z/C/h closure fails.
Source errors and out-of-table states remain visible. Curves connect actual accepted solver states;
they are not regressions.</p><section id="physical-trajectories"><h2>Physical time histories</h2>
<img src="physical-trajectories.png"></section><section id="coordinate-closure"><h2>Projection against the unchanged table</h2>
<img src="coordinate-closure.png"></section><h2>Run identity and completion</h2><pre>SUMMARY</pre>'''
    summary={key:receipt[key] for key in ['job_id','source_commit','status','cantera_extension_sha256']}
    summary['cases']=[{**case,'physical':{k:report[k] for k in ['numerically_complete','enthalpy_relative','element_absolute','HP_endpoint'] if k in report}} for case,_,report,_,_ in records]
    (args.out/'index.html').write_text(page.replace('SUMMARY',html.escape(json.dumps(summary,indent=2))),encoding='utf8')
    result={'schema':'mixing-witness-review/v1','input_hashes':hashes,'physics_source':receipt['source_commit'],
        'job_id':receipt['job_id'],'renderer_sha256':sha(Path(__file__)),
        'outputs_sha256':{p.name:sha(p) for p in args.out.iterdir() if p.is_file()},'scientific_acceptance':False}
    (args.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'output':str(args.out),'panels':2,'job_id':receipt['job_id'],'scientific_acceptance':False}))


if __name__=='__main__':main()
