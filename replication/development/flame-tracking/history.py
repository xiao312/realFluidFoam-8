"""Plot the three retained measures from immutable local runtime snapshots."""
import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


def read(path):
    with path.open() as stream:return list(csv.DictReader(stream))


def assess(snapshot):
    manifest=json.loads((snapshot/'snapshot.json').read_text());results=[]
    for item in manifest['jobs']:
        base=snapshot/item['job']
        for name,expected in item['files'].items():
            assert hashlib.sha256((base/name).read_bytes()).hexdigest()==expected
        config=json.loads((base/'tracking-inputs.json').read_text())
        tracked=read(base/'front-tracking.csv');source=read(base/'flame-speed.csv')
        end=max(float(r['time_s']) for r in tracked)
        series={}
        for side in ['left','right']:
            for marker in ['T','OH']:
                rows=[r for r in tracked if r['side']==side and r['marker']==marker and
                      r['primary']=='1' and r['status']=='valid']
                series[side+'_'+marker]=[(float(r['time_s']),100*float(r['density_weighted_m_s'])) for r in rows]
            rows=[r for r in source if r['side']==side and r['stage']=='integrated_species_solve'
                  and r['status']=='valid' and abs(float(r['OH_level'])-2e-5)<1e-15]
            series[side+'_source']=[(float(r['time_s']),100*float(r['speed_m_s'])) for r in rows]
        for values in series.values():assert all(math.isfinite(t+v) for t,v in values)
        summary={}
        for name,values in series.items():
            window=[v for t,v in values if t>=end-5e-6]
            summary[name]={'latest_cm_s':values[-1][1] if values else None,
                'median_last_5us_cm_s':statistics.median(window) if window else None,'samples':len(values)}
        results.append(dict(phi=config['phi'],job=item['job'],time_s=end,
            reference_cm_s=config['temperature_anchor']['speed_cm_s'],series=series,
            latest=summary,scientific_acceptance=False))
    return manifest,sorted(results,key=lambda x:x['phi'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();manifest,results=assess(a.snapshot)
    if a.output.exists():raise ValueError('Use a new output directory')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.linewidth':.7})
    fig,axes=plt.subplots(3,4,figsize=(12,8.2),sharey=True)
    for ax,row in zip(axes.flat,results):
        for marker,color,label in [('source','#9b721d','Species-solve source'),('OH','#257548','OH-front tracking'),('T','#7c43a4','T-anchor tracking')]:
            for side in ['left','right']:
                values=row['series'][side+'_'+marker]
                ax.plot([t*1e6 for t,v in values],[v for t,v in values],color=color,
                        linestyle='-' if side=='left' else '--',linewidth=.8,label=label if side=='left' else None)
        ax.axhline(row['reference_cm_s'],color='black',linestyle=':',linewidth=.9,label='Cantera ideal gas')
        ax.set_title('phi %.2f | job %s'%(row['phi'],row['job']),fontsize=8)
        ax.set_xlabel('Physical time (us)');ax.set_ylabel('Speed (cm/s)')
        ax.set_ylim(0,10);ax.grid(alpha=.15)
    axes.flat[-1].axis('off');handles,labels=axes.flat[1].get_legend_handles_labels()
    axes.flat[-1].legend(handles,labels,loc='center left',frameon=False)
    axes.flat[-1].text(.02,.15,'Solid: left front; dashed: right front\nTracking: trailing 5-us fit\nTransient; no accepted steady CFD points',transform=axes.flat[-1].transAxes)
    fig.suptitle('Ideal-gas OpenFOAM: three in-situ speed measures | '+manifest['timestamp_local'],fontsize=11)
    fig.tight_layout(rect=(0,0,1,.96));a.output.mkdir(parents=True)
    fig.savefig(a.output/'ideal-openfoam-histories.png',dpi=180)
    fig.savefig(a.output/'ideal-openfoam-histories.svg')
    for row in results:row.pop('series')
    (a.output/'assessment.json').write_text(json.dumps(dict(snapshot=str(a.snapshot),
        timestamp_local=manifest['timestamp_local'],sacct=manifest['sacct'],conditions=results),indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
