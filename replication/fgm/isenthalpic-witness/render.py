"""Compare actual equal-h witnesses with the corresponding original HP mixtures."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path

import numpy as np

NAMES=['same-ZC-rich-path','same-ZC-lean-path']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_case(root,case,hashes):
    folder=root/case['name']
    initial_path=folder/'initial-state.json';physical_path=folder/'physical-receipt.json';trace=folder/'chemical-tail.npz'
    if sha(initial_path)!=case['initial_state_sha256'] or sha(physical_path)!=case['physical_receipt_sha256']:
        raise ValueError('Changed retained case receipt')
    initial=json.loads(initial_path.read_text());physical=json.loads(physical_path.read_text())
    if physical.get('status')!='completed' or physical.get('numerically_complete') is not True:
        raise ValueError('Require numerically complete physical trajectories')
    if sha(trace)!=physical['trajectory_sha256']:raise ValueError('Changed physical trajectory')
    with np.load(trace) as raw:times,states=raw['time_s'].copy(),raw['states'].copy()
    if (times.ndim!=1 or states.ndim!=2 or states.shape[0]!=len(times) or states.shape[1]<6
        or len(times)<2 or not np.isfinite(times).all() or times[0]!=0
        or not np.all(np.diff(times)>0) or not np.isfinite(states).all()
        or not np.all(states[:,3]>0)):
        raise ValueError('Invalid retained time/state history')
    for path in [initial_path,physical_path,trace]:hashes[str(path.resolve())]=sha(path)
    return {'case':case,'initial':initial,'physical':physical,'times':times,'states':states}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--prior',type=Path,required=True)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    current=json.loads((args.input/'receipt.json').read_text());prior=json.loads((args.prior/'receipt.json').read_text())
    if current['schema']!='isenthalpic-composition-witness/v1' or current['audit_only']:
        raise ValueError('Require actual equal-h physical execution')
    if prior['schema']!='physical-mixing-witness/v1' or prior['audit_only']:
        raise ValueError('Require original physical execution')
    if current['status']!='completed_diagnostic' or prior['status']!='completed_diagnostic':
        raise ValueError('Require complete diagnostic receipts')
    if current['models']['thermo_model']!='ideal-gas' or current['models']['kinetics_model']!='bulk':
        raise ValueError('This comparison is labelled only for ideal-gas bulk kinetics')
    if (sha(args.prior/'receipt.json') not in current['input_hashes'].values()
        or str(prior['job_id'])!=str(current['original_mixing_job_id'])
        or prior['cantera_extension_sha256']!=current['cantera_extension_sha256']):
        raise ValueError('Original execution is not bound to the equal-h run')
    pair_path=args.input/'same-coordinate-audit.json'
    if sha(pair_path)!=current['artifacts']['same-coordinate-audit.json']:raise ValueError('Changed equal-coordinate audit')
    pair=json.loads(pair_path.read_text())
    hashes={str(p.resolve()):sha(p) for p in [args.input/'receipt.json',args.prior/'receipt.json',pair_path]}
    records=[]
    for family,root,receipt in [('prior',args.prior,prior),('equal-h',args.input,current)]:
        for name in NAMES:
            selected=[case for case in receipt['cases'] if case['name']==name]
            if len(selected)!=1:raise ValueError('Missing original/new physical case '+name)
            record=load_case(root,selected[0],hashes);record['family']=family;records.append(record)
    summary={'schema':'isenthalpic-witness-review/v1','job_id':current['job_id'],
        'prior_job_id':prior['job_id'],'physics_source':current['source_commit'],'prior_source':prior['source_commit'],
        'models':current['models'],'same_coordinate_audit':pair,'input_hashes':hashes,
        'physical_status':current['status'],'scientific_acceptance':False}
    if args.out is None:print(json.dumps(summary,indent=2));return
    if any(sha(Path(p))!=digest for p,digest in hashes.items()):raise ValueError('Inputs changed before render')
    args.out.mkdir(exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR',str(args.out/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':11,'axes.titlesize':12,'axes.labelsize':11,
        'lines.linewidth':1.8,'axes.spines.top':False,'axes.spines.right':False})
    colors={'same-ZC-rich-path':'#6953a3','same-ZC-lean-path':'#159886'}
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for record in records:
        times,states=record['times'],record['states'];name=record['case']['name']
        label=('Equal h' if record['family']=='equal-h' else 'Original h')+'; '+('rich-cap composition' if name==NAMES[0] else 'lean-cap composition')
        options={'color':colors[name],'ls':'-' if record['family']=='equal-h' else '--','label':label,
                 'lw':2 if record['family']=='equal-h' else 1.2,'alpha':1 if record['family']=='equal-h' else .65}
        for ax,values in zip(axes.flat,[states[:,1],states[:,0],states[:,4]/states[:,3],states[:,5]/states[:,3]]):
            ax.plot(times*1e3,values,**options)
            ax.set_xscale('symlog',linthresh=1e-6)
            ax.set_xlabel('Physical time (ms); symlog, linear within 1 ns');ax.grid(alpha=.2)
    for ax,label in zip(axes.flat,['Temperature (K)','Cwater = YCO2 + YCO + YH2O',
        'Chemical dCwater/dt (s⁻¹)','Formation heat release / density (W/kg)']):ax.set_ylabel(label)
    for ax in axes[1]:ax.set_yscale('symlog',linthresh=1)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Same nominal Z/Cwater and matched h/p: actual ideal-gas GRI trajectories')
    for suffix in ['png','svg']:fig.savefig(args.out/('matched-h-trajectories.'+suffix),dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5.6),layout='constrained')
    for record in records:
        states=record['states'];name=record['case']['name'];current_family=record['family']=='equal-h'
        options={'color':colors[name],'ls':'-' if current_family else '--','lw':2 if current_family else 1.2,
            'label':('Equal h' if current_family else 'Original h')+'; '+('rich-cap' if name==NAMES[0] else 'lean-cap')}
        for ax,values in zip(axes,[states[:,1],states[:,4]/states[:,3]]):
            ax.plot(states[:,0],values,**options)
            if current_family:
                ax.scatter(states[0,0],values[0],color=colors[name],marker='o',s=38)
                ax.scatter(states[-1,0],values[-1],color=colors[name],marker='x',s=38)
            ax.set_xlabel('Cwater = YCO2 + YCO + YH2O');ax.grid(alpha=.2)
    axes[0].set_ylabel('Temperature (K)');axes[0].legend(fontsize=8)
    axes[1].set_ylabel('Chemical dCwater/dt (s⁻¹)');axes[1].set_yscale('symlog',linthresh=1)
    fig.suptitle('Coordinate-history diagnostic; circles initial, crosses final')
    for suffix in ['png','svg']:fig.savefig(args.out/('matched-h-coordinate.'+suffix),dpi=170)
    plt.close(fig)
    detail=[]
    for record in records:
        physical=record['physical'];states=record['states'];times=record['times']
        crossings={}
        for delta in [.01,.1,.2]:
            indices=np.flatnonzero(states[:,0]>=states[0,0]+delta)
            n=int(indices[0]) if len(indices) else None
            crossings[str(delta)]=[float(times[max(0,n-1)]),float(times[n])] if n is not None else None
        detail.append({'family':record['family'],'case':record['case']['name'],
            'first_progress_increment_brackets_s':crossings,'initial_T_K':float(states[0,1]),
            'initial_h_J_kg':float(states[0,2]),'initial_dC_dt_s_1':float(states[0,4]/states[0,3]),
            'final_T_K':float(states[-1,1]),'final_Cwater':float(states[-1,0]),
            'maximum_h_drift_J_kg':float(np.max(abs(states[:,2]-states[0,2]))),
            'physical':{k:physical[k] for k in ['status','numerically_complete','actual_final_time_s',
                'elapsed_s','accepted_steps','enthalpy_relative','element_absolute','minimum_Y','HP_endpoint'] if k in physical}})
    summary['cases']=detail
    page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Equal-enthalpy composition witnesses</title>
<style>body{font:17px/1.6 system-ui,sans-serif;max-width:1200px;margin:40px auto;padding:0 22px;color:#21303c}img{width:100%}pre{white-space:pre-wrap;background:#f3f4f5;padding:18px}.note{background:#fff0dd;padding:18px}a{color:#08697e}</style>
<h1>Equal-enthalpy composition witnesses</h1><p class="note">Two fresh constant-pressure adiabatic ideal-gas GRI reactors at 5.61 MPa, using the same nominal Z and Cwater and one common requested enthalpy. Their original compositions are retained. These are not SRK full-chemistry reactors, CFD results, or paper acceptance.</p>
<p>Solid curves: new equal-h states. Dashed curves: original states with the small enthalpy difference. Curves connect actual accepted CVODE states; no regression or smoothing is applied. Differences test global coordinate uniqueness for this pair, not the validity of a deliberately restricted manifold.</p>
<nav><a href="#time">Physical time</a> · <a href="#coordinate">Progress coordinate</a> · <a href="#evidence">Exact evidence</a></nav>
<section id="time"><h2>Physical time histories</h2><img src="matched-h-trajectories.png"></section>
<section id="coordinate"><h2>Composition-history comparison</h2><img src="matched-h-coordinate.png"></section>
<section id="evidence"><h2>Initial equality, numerical completion and ancestry</h2><pre>SUMMARY</pre><a href="receipt.json">Full input/output hashes</a></section>'''
    (args.out/'index.html').write_text(page.replace('SUMMARY',html.escape(json.dumps({k:v for k,v in summary.items() if k!='input_hashes'},indent=2))),encoding='utf8')
    summary.update(renderer_sha256=sha(Path(__file__)),output_hashes={p.name:sha(p) for p in args.out.iterdir() if p.is_file()})
    (args.out/'receipt.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({'out':str(args.out),'job_id':current['job_id'],'figures':2,'scientific_acceptance':False}))


if __name__=='__main__':main()
