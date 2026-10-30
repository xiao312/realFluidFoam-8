"""Compare explicit saved-sample window statistics with retained G2 paper figures."""
import argparse
import html
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'g2-review'))
from inputs import read_csv,sha256,image_grid
sys.path.insert(0,str(HERE.parent/'g2-paper-review'))
from references import load_targets
spec=importlib.util.spec_from_file_location('g2_shared_review',HERE.parent/'g2-review/review.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)


def window_text(group):
    q=group['quadrature']
    return f"{q['duration_s']*1e6:.5g} µs used; {q['contributingSampleCount']} snapshots; {q['coverageFraction']*100:.3g}% requested coverage"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['statistics','targets','sharma-reference','sharma-pdf','out']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--x-origin-m',type=float,required=True)
    parser.add_argument('--origin-note',required=True)
    parser.add_argument('--weighting',choices=['reynolds','favre'],default='reynolds')
    parser.add_argument('--label',default='Provisional saved-sample finite-window statistics')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not math.isfinite(args.x_origin_m) or not args.origin_note.strip():raise ValueError('Require explicit coordinate origin/evidence')
    manifest_path=args.statistics/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    if manifest['schema']!='g2-saved-window-statistics/v1' or manifest['mode']!='applied':raise ValueError('Require an applied retained statistics receipt')
    hashes={str(manifest_path.resolve()):sha256(manifest_path)}
    for name,digest in manifest['outputHashes'].items():
        if Path(name).name!=name:raise ValueError('Derived asset must be a basename')
        path=args.statistics/name
        if sha256(path)!=digest:raise ValueError('Changed statistics asset: '+name)
        hashes[str(path.resolve())]=digest
    targets=load_targets(args.targets);hashes.update(targets['hashes'])
    sharma,original_sharma=shared.paper(args.sharma_reference,args.sharma_pdf)
    for path in [args.sharma_reference,args.sharma_pdf]:hashes[str(path.resolve())]=sha256(path)
    groups=[{**group,'values':read_csv(args.statistics/group['output'])} for group in manifest['groups'] if 'output' in group]
    mean,rms=('Mean','RMS') if args.weighting=='reynolds' else ('FavreMean','FavreRMS')
    for group in groups:
        if 'T'+mean not in group['values']:raise ValueError('Requested weighting unavailable in '+group['key'])
    plan={'schema':'g2-window-paper-review/v1','label':args.label,'weighting':args.weighting,
        'requestedWindow_s':manifest['requestedWindow_s'],'groups':[g['key'] for g in groups],
        'inputHashes':hashes,'scientificAcceptance':False,'statisticalConvergenceEstablished':False}
    if not args.apply:print(json.dumps(plan,indent=2));return
    if any(sha256(path)!=digest for path,digest in hashes.items()):raise ValueError('Inputs changed before rendering')
    args.out.mkdir(exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR',str(args.out/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from plots import style,save,line_with_gaps
    style()
    for key in targets['targets']:shutil.copyfile(args.targets/(key+'.png'),args.out/('original-'+key+'.png'))
    (args.out/'original-sharma4b.png').write_bytes(original_sharma)
    observations=manifest['caseInput']['observations'];panels=[]
    streams=manifest['caseInput'].get('streams',{})
    inlet_note=f"Our O2/CH4 inlets: {streams.get('loxinlet',{}).get('temperature','unrecorded')}/{streams.get('ch4inlet',{}).get('temperature','unrecorded')} K; Schmitt target: 83/300 K."
    radial_note=f"Our sampled radius is {observations['nearAxisRadius_m']*1000:g} mm; Schmitt uses the centerline."
    for group in groups:
        values=group['values'];name=group['name'];note=window_text(group)
        if name.startswith('radial'):
            station=(observations['radialPositions_m'][int(name[6:])]-args.x_origin_m)*1000
            selected=next((v for v in (15,45,70) if abs(station-v)<1e-6),None)
            if selected is None:continue
            fig,axes=plt.subplots(1,2,figsize=(11,5.2));fig.subplots_adjust(left=.08,right=.98,top=.78,bottom=.22,wspace=.25)
            for axis,statistic,suffix in zip(axes,['mean','rms'],[mean,rms]):
                for grid,color,dash in [('M1','#aaaaaa',':'),('M2','#b17b43','--'),('M3','#356597','-')]:
                    curves=[c for c in targets['curves'] if c['station_mm']==selected and c['statistic']==statistic and c['grid']==grid]
                    if len(curves)!=1:raise ValueError('Missing paper mean/RMS curve')
                    curve=curves[0];axis.plot(curve['radial_mm'],curve['temperature_K'],color=color,ls=dash,label='Paper '+grid)
                x,y=line_with_gaps(values['y']*1000,values['T'+suffix],.0247/199*1000)
                axis.plot(x,y,color='#553488',lw=2.1,label='Our provisional '+args.weighting)
                axis.set(xlabel='Radius (mm)',ylabel='Temperature '+statistic+' (K)',xlim=(0,25));axis.set_ylim(bottom=0);axis.grid(alpha=.18);axis.legend(fontsize=8)
            fig.suptitle(f'Cavalieri Fig. 6 | x={selected:g} mm | provisional window mean and RMS')
            fig.text(.08,.10,note,fontsize=9)
            fig.text(.08,.05,'Paper window: 60 ms. Our transient RMS includes startup; statistical convergence is unestablished.',fontsize=9)
            panels.append({'name':save(fig,args.out,f'cavalieri-window-{selected}mm'),'title':f'Cavalieri radial mean/RMS at {selected} mm','reference':'cavalieri2025-fig-6','meaning':note})
        elif name=='nearAxis':
            fig,ax=plt.subplots(figsize=(7.5,5.5));fig.subplots_adjust(left=.12,right=.97,top=.83,bottom=.23)
            for key,color,marker in [('fine','#c25932','s'),('finer','#3164af','o')]:
                points=np.asarray(sharma['series'][key]['points']);x,y=line_with_gaps(points[:,0],points[:,1],sharma['reading_uncertainty']['x_one_pixel_m'])
                ax.plot(x,y,color=color,marker=marker,markevery=24,label='Paper '+key+': time mean')
            x,y=line_with_gaps(values['x']-args.x_origin_m,values['T'+mean],.1998/399)
            ax.plot(x,y,color='#553488',label='Our provisional '+args.weighting+' mean',lw=2.1)
            ax.set(xlabel='Axial distance from explicit exit (m)',ylabel='Temperature mean (K)',title='Sharma Fig. 4b | saved-sample window mean',xlim=(0,.2));ax.set_ylim(bottom=0);ax.grid(alpha=.18);ax.legend(fontsize=9)
            fig.text(.12,.10,note,fontsize=9);fig.text(.12,.05,'No statistical convergence. Paper shading marks flame position, not measured temperature.',fontsize=9)
            panels.append({'name':save(fig,args.out,'axial-window-mean'),'title':'Sharma near-axis temperature mean','reference':'sharma4b','meaning':note})
            if 'O2'+mean in values and 'O2'+rms in values:
                fig,ax=plt.subplots(figsize=(7.5,5.5));fig.subplots_adjust(left=.12,right=.97,top=.81,bottom=.25)
                for suffix,label,dash in [(mean,'mean','-'),(rms,'RMS','--')]:
                    x,y=line_with_gaps((values['x']-args.x_origin_m)*1000,values['O2'+suffix],.1998/399*1000)
                    ax.plot(x,y,color='#553488',ls=dash,label='Our provisional '+args.weighting+' '+label)
                ax.set(xlabel='Axial distance from explicit exit (mm)',ylabel='Oxygen mass fraction',title='Schmitt Fig. 21(b) | near-axis window diagnostic',xlim=(0,200));ax.set_ylim(bottom=0);ax.grid(alpha=.18);ax.legend(fontsize=9)
                fig.text(.12,.13,note,fontsize=9)
                fig.text(.12,.085,'No matched paper curve/d-normalization. '+radial_note,fontsize=8)
                fig.text(.12,.04,inlet_note+' No accepted flame length.',fontsize=8)
                panels.append({'name':save(fig,args.out,'schmitt-oxygen-window'),'title':'Schmitt oxygen mean/RMS companion','reference':'schmitt2020-fig-21',
                    'meaning':note+'. Non-equivalent coordinate/conditions; reference digitization and velocity remain unavailable.'})
        elif group['geometry']=='plane':
            for field,label,cmap in [('T','Temperature (K)','inferno'),('rho','Density (kg/m³)','cividis'),('OH','Ground-state OH mass fraction','viridis')]:
                if field+mean not in values:continue
                fig,axes=plt.subplots(2,1,figsize=(10,6));fig.subplots_adjust(left=.08,right=.95,top=.82,bottom=.19,hspace=.5)
                for axis,suffix,statistic in zip(axes,[mean,rms],['Mean','RMS']):
                    x,y,grid=image_grid(values,observations.get('imageGrid'),field+suffix)
                    colors=plt.colormaps[cmap].copy();colors.set_bad('#dddddd')
                    mesh=axis.pcolormesh((x-args.x_origin_m)*1000,y*1000,grid,shading='nearest',cmap=colors,rasterized=True)
                    fig.colorbar(mesh,ax=axis,pad=.02,fraction=.025).set_label(label)
                    axis.set(xlabel='Axial distance (mm)',ylabel='Radius (mm)',title=args.weighting+' '+statistic)
                fig.suptitle('Provisional saved-sample '+label+' statistics')
                fig.text(.08,.10,note,fontsize=9);fig.text(.08,.05,'Missing cells stay gray. No interpolation, optical inference or statistical convergence.',fontsize=9)
                panels.append({'name':save(fig,args.out,'window-map-'+field),'title':label+' mean/RMS','reference':'sharma2023-fig-9' if field=='OH' else None,'meaning':note})
    esc=html.escape
    page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>G2 finite-window comparison</title>
<style>body{font:17px/1.6 system-ui,sans-serif;color:#26312c;background:#f7f6f1;max-width:1320px;margin:36px auto;padding:0 24px}.pair{display:grid;grid-template-columns:1.2fr 1fr;gap:24px}img{width:100%}section{border-top:1px solid #ccd5cd;padding:24px 0}.notice{background:#fff0df;padding:18px}pre{white-space:pre-wrap;font-size:13px}a{color:#00687b}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style>'''
    page+='<h1>'+esc(args.label)+'</h1><p class="notice">Provisional saved-sample statistics. These are not solver fieldAverage counters or statistically converged paper means. Excluded gaps and partial coverage remain explicit. Transient RMS includes flow development.</p>'
    page+=f'<p>Requested window {manifest["requestedWindow_s"]} s; weighting {args.weighting}. {esc(args.origin_note)}. Job {esc(str(manifest["runIdentity"]["jobId"]))}.</p>'
    page+='<nav>'+' · '.join(f'<a href="#{p["name"]}">{esc(p["title"])}</a>' for p in panels)+' · <a href="#references">References</a></nav>'
    for panel in panels:
        page+=f'<section id="{panel["name"]}"><h2>{esc(panel["title"])}</h2><p>{esc(panel["meaning"])}</p>'
        reference=panel['reference'];page+='<div class="pair">' if reference else ''
        page+=f'<div><img src="{panel["name"]}.png"></div>'
        if reference:
            caption=shared.CAPTION if reference=='sharma4b' else targets['targets'][reference]['original_caption']
            page+=f'<div><img src="original-{reference}.png"><p>{esc(caption)}</p><a href="#ref-{reference}">Reference</a></div></div>'
        page+='</section>'
    page+='<section><h2>Coverage and unavailable comparisons</h2><p>Schmitt Fig. 21 oxygen is a provisional companion only: no reliable separated G2 reference curve, matched d-normalization or velocity profile is supplied. '+esc(radial_note+' '+inlet_note)+' Ground-state OH is not OH* emission. No optical proxy is calculated from mean fields.</p><pre>'
    page+=esc(json.dumps([{k:v for k,v in group.items() if k not in ['times_s','fields']} for group in manifest['groups']],indent=2))+'</pre></section><section id="references"><h2>Original captions and references</h2>'
    all_refs={**targets['targets'],'sharma4b':{'paper':{'title':shared.PAPER,'url':shared.URL},'original_caption':shared.CAPTION}}
    for key,target in all_refs.items():
        page+=f'<section id="ref-{key}"><h3><a href="{esc(target["paper"]["url"])}">{esc(target["paper"]["title"])}</a></h3><p>{esc(target["original_caption"])}</p>'
        page+=' · '.join(f'<a href="#{p["name"]}">Return: {esc(p["title"])}</a>' for p in panels if p['reference']==key)+'</section>'
    page+='<p><a href="receipt.json">Exact provenance and artifact hashes</a></p></section>'
    (args.out/'index.html').write_text(page,encoding='utf8')
    dependencies=[Path(__file__),HERE.parent/'g2-review/inputs.py',HERE.parent/'g2-review/plots.py',HERE.parent/'g2-review/review.py',HERE.parent/'g2-paper-review/references.py']
    result={**plan,'statisticsManifest':manifest,'panels':panels,'sourceHashes':{str(p.relative_to(HERE.parent)):sha256(p) for p in dependencies},
            'outputHashes':{p.name:sha256(p) for p in args.out.iterdir() if p.is_file()}}
    (args.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'out':str(args.out),'panels':len(panels),'scientificAcceptance':False}))


if __name__=='__main__':main()
