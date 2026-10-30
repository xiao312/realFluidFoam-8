"""Plot retained accepted-step physical curves, without fitting or resampling."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((args.input/'diagnostic/receipt.json').read_text())
    assert receipt['status']=='completed' and receipt['cantera']=='3.2.0'
    fetch=json.loads((args.input/'fetch.json').read_text())
    identities={row['path']:row for row in fetch['files']}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.labelsize':10,
        'axes.titlesize':11,'legend.fontsize':9,'lines.linewidth':1.8,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,3,figsize=(13.0,7.4),layout='constrained')
    summaries={}
    for name,label,color in [('coverage-edge','Table boundary','#176b91'),('source-start','Source-stage start','#d27930')]:
        path=args.input/f'diagnostic/{name}/accepted.curves.csv'
        raw=path.read_bytes();identity=identities[path.relative_to(args.input).as_posix()]
        assert hashlib.sha256(raw).hexdigest()==identity['sha256']
        assert identity['source_sha256']==receipt['artifacts'][f'{name}/accepted.csv']
        with path.open(newline='') as handle:rows=list(csv.DictReader(handle))
        data={key:np.array([float(row[key]) for row in rows]) for key in rows[0]}
        t=data['time_s'];early=t<=5e-10
        axes[0,0].plot(t*1e6,data['C'],color=color,label=label)
        axes[0,1].plot(t[early]*1e9,(data['C'][early]-data['C'][0])*1e6,color=color)
        axes[0,2].plot(t*1e6,data['Cwater'],color=color)
        axes[1,0].plot(t*1e6,data['T_K'],color=color)
        axes[1,1].plot(t*1e6,data['Sc_kg_m3_s']/1e6,color=color)
        axes[1,2].plot(t*1e6,data['Scwater_kg_m3_s']/1e6,color=color)
        summaries[name]=json.loads((args.input/f'diagnostic/{name}/summary.json').read_text())
    init=json.loads((args.input/'diagnostic/coverage-edge/initial-table-state.json').read_text())
    axes[0,0].axhline(init['Cmax'],color='#6b7280',linestyle='--',linewidth=1,label='Original table Cmax')
    titles=['CO₂ + CO progress','Early overshoot: each state relative to its start','CO₂ + CO + H₂O progress',
            'Temperature','CO₂ + CO full-chemistry source','CO₂ + CO + H₂O full-chemistry source']
    labels=['Mass fraction','Change in mass fraction (×10⁻⁶)','Mass fraction','Temperature (K)',
            'Source (10⁶ kg m⁻³ s⁻¹)','Source (10⁶ kg m⁻³ s⁻¹)']
    for i,axis in enumerate(axes.flat):
        axis.set_title(titles[i],loc='left');axis.set_ylabel(labels[i]);axis.grid(alpha=.17)
        if i==1:
            axis.set_xlabel('Physical time (ns)');axis.set_xlim(0,.5);axis.axhline(0,color='#8c929a',linewidth=.7)
        else:
            axis.set_xscale('symlog',linthresh=1e-4,linscale=.4)
            axis.set_xlim(0,2000);axis.set_xlabel('Physical time (µs; logarithmic after 0.0001 µs)')
    axes[0,0].legend(loc='best',frameon=False)
    fig.suptitle('The CO₂ + CO coordinate reverses under full chemistry',fontsize=15,fontweight='bold')
    fig.supxlabel('Fresh Cantera 3.2/CVODE · 5.61 MPa · Z = 0.286519 · accepted internal steps\nIdeal-gas GRI30 with declared NASA extrapolation; not real-fluid CFD acceptance.',fontsize=9)
    fig.savefig(args.out/'progress-reactor.png',dpi=180)
    fig.savefig(args.out/'progress-reactor.svg')
    plt.close(fig)
    record={'job_id':receipt['job_id'],'source':receipt['source_commit'],'physical_data':'CVODE accepted internal steps; no fitted curves',
        'input_fetch_sha256':hashlib.sha256((args.input/'fetch.json').read_bytes()).hexdigest(),
        'plot_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scientific_acceptance':False,
        'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.is_file()}}
    (args.out/'plot-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))


if __name__=='__main__':
    main()
