"""Plot observed heat release without backfilling the unsampled ignition interval."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(manifest,output):
    cases=json.loads(manifest.read_text()); output.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({'font.family':'serif','font.size':9,'axes.linewidth':.7})
    fig,axes=plt.subplots(3,1,figsize=(8,7),sharex=True)
    receipts=[]
    for index,case in enumerate(cases):
        path=Path(case['csv']); rows=list(csv.DictReader(path.open()))
        if not rows or any(None in r or any(v is None for v in r.values()) for r in rows):
            raise ValueError('Empty/incomplete CSV: '+str(path))
        data={key:np.array([float(r[key]) for r in rows]) for key in rows[0]}
        if not all(np.all(np.isfinite(v)) for v in data.values()):raise ValueError('Nonfinite source data')
        if np.any(np.diff(data['time_s'])<=0):raise ValueError('Duplicate/nonmonotone sample time')
        t=data['time_s']*1e6;color=f'C{index}';label=case['label']+' ('+str(case['job'])+')'
        axes[0].plot(t,data['Qdot_max_W_m3']/1e9,color=color,marker='.',label=label+' max')
        axes[0].plot(t,data['Qdot_min_W_m3']/1e9,color=color,ls='--',marker='x',markersize=3,label=label+' min')
        axes[1].plot(t,data['net_W_m2']/1e6,color=color,marker='.',label=label)
        axes[2].plot(t,data['Tmax_K'],color=color,marker='.',label=label)
        receipts.append(dict(case,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(rows),
            start_time_s=float(data['time_s'][0]),end_time_s=float(data['time_s'][-1])))
    axes[0].set_ylabel('Qdot extrema (GW/m³)');axes[0].set_yscale('symlog',linthresh=.1)
    axes[1].set_ylabel('Net power / area (MW/m²)');axes[1].set_yscale('symlog',linthresh=.1)
    axes[2].set(ylabel='Peak temperature (K)',xlabel='Physical time (µs)')
    for ax in axes:
        ax.grid(alpha=.15);ax.legend(fontsize=7,loc='best')
    axes[0].axhline(0,color='.6',lw=.5);axes[1].axhline(0,color='.6',lw=.5)
    fig.suptitle('Heat release used by the energy equation — ignition histories',fontsize=12)
    fig.text(.5,.935,'Integrated chemistry rates; signed heat release. Curves begin at observer attachment. Both fronts included.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,0,1,.92))
    for ext in ['png','pdf']:fig.savefig(output/('heat-release-history.'+ext),dpi=180)
    plt.close(fig)
    (output/'provenance.json').write_text(json.dumps(receipts,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();plot(a.manifest,a.output)
