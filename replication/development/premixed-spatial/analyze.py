"""Plot local SI-unit terms, retaining stage and flux-definition distinctions."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load(path):
    rows=list(csv.DictReader(path.open()))
    data={k:np.array([float(r[k]) for r in rows]) for k in rows[0]}
    if len(rows)!=8000 or not all(np.isfinite(a).all() for a in data.values()):
        raise ValueError('Invalid spatial data '+str(path))
    return data


def contour(data,level,side='left'):
    x=data['x_m'];y=data['YOH'];mid=.002
    selected=(x[:-1]<mid)&(x[1:]<mid)&(y[:-1]<=level)&(y[1:]>level) if side=='left' else (
        (x[:-1]>mid)&(y[:-1]>level)&(y[1:]<=level))
    crossings=np.flatnonzero(selected)
    if len(crossings)!=1:raise ValueError('Expected unique OH contour')
    i=crossings[0];f=(level-y[i])/(y[i+1]-y[i])
    q={k:float(v[i]+f*(v[i+1]-v[i])) for k,v in data.items()}
    denominator=q['rho_unburned_kg_m3']*abs(q['gradOH_1_m'])
    q.update(level=level,side=side,
        chemistry_cm_s=100*q['omegaOH_kg_m3_s']/denominator,
        diffusion_cm_s=100*q['diffusion_used_kg_m3_s']/denominator,
        speed_cm_s=100*(q['omegaOH_kg_m3_s']+q['diffusion_used_kg_m3_s'])/denominator,
        fick_speed_cm_s=100*(q['omegaOH_kg_m3_s']+q['diffusion_Fick_kg_m3_s'])/denominator)
    return q


def speed(data,field='diffusion_used_kg_m3_s'):
    grad=np.abs(data['gradOH_1_m'])
    result=100*(data['omegaOH_kg_m3_s']+data[field])/(data['rho_unburned_kg_m3']*np.maximum(grad,1e-300))
    left=data['x_m']<.002;peak=np.argmax(np.where(left,data['YOH'],-1))
    threshold=max(1e-6,.001*grad[left].max())
    mask=left & (np.arange(len(grad))<peak) & (data['gradOH_1_m']>threshold) & (data['YOH']>=1e-7)
    return np.where(mask,result,np.nan),mask,threshold


def display_profile(data):
    # Interpolate terms before taking their quotient, as for contour markers.
    # This only draws the existing piecewise-linear data; it adds no resolution.
    x=data['x_m'];fine=np.linspace(x[0],x[-1],8*(len(x)-1)+1)
    return {k:np.interp(fine,x,v) for k,v in data.items()}


def analyze(root,output):
    output.mkdir(parents=True,exist_ok=False)
    inputs=json.loads((root/'checkpoint-inputs.json').read_text())
    raw=(root/'donor-flame-speed.csv').read_bytes()
    end=raw.rfind(b'\n')+1
    live=list(csv.DictReader(raw[:end].decode().splitlines()))
    plt.rcParams.update({'font.family':'serif','font.size':9,'axes.linewidth':.7,'lines.linewidth':1.2})
    profiles=[];measurements=[];receipts=[]
    for i in range(4):
        case=root/('on'+str(i))/'processor0';time=float(inputs['on'+str(i)]['time'])
        stages={}
        for stage in ['instantaneous_checkpoint','integrated_species_solve','instantaneous_end_step']:
            paths=list(case.glob('spatial-'+stage+'-*.csv'))
            if len(paths)!=1:raise ValueError('Missing/ambiguous stage')
            path=paths[0];data=load(path);stages[stage]=data
            receipts.append({'file':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            for level in [1e-5,2e-5,3e-5]:
                for side in ['left','right']:
                    row=contour(data,level,side);row.update(checkpoint_time_s=time,stage=stage)
                    if stage=='instantaneous_checkpoint':
                        candidates=[r for r in live if r.get('stage')=='instantaneous_end_step' and r.get('side')==side and
                            abs(float(r['OH_level'])-level)<1e-15 and r['status']=='valid']
                        closest=min(candidates,key=lambda r:abs(float(r['time_s'])-time))
                        if abs(float(closest['time_s'])-time)>1e-13:raise ValueError('Missing matching live sample')
                        row['live_speed_cm_s']=float(closest['speed_m_s'])*100
                        row['reload_difference_cm_s']=row['speed_cm_s']-row['live_speed_cm_s']
                    measurements.append(row)
        profiles.append((time,stages))
    fig,axes=plt.subplots(2,2,figsize=(10,7))
    for i,(time,stages) in enumerate(profiles):
        color=f'C{i}';label=f'{time*1e6:.2f} µs';initial=stages['instantaneous_checkpoint'];x=initial['x_m']*1000
        axes[0,0].plot(x,initial['YOH'],color=color,label=label)
        axes[0,1].plot(x,initial['T_K'],color=color,label=label)
        for ax,stage in zip(axes[1],['instantaneous_checkpoint','integrated_species_solve']):
            raw_data=stages[stage];data=display_profile(raw_data);values,mask,threshold=speed(data)
            ax.plot(data['x_m']*1000,values,color=color,label=label+(' + 0.10 µs' if stage=='integrated_species_solve' else ''))
            for level,marker in [(1e-5,'o'),(2e-5,'s'),(3e-5,'^')]:
                q=contour(raw_data,level);ax.plot(q['x_m']*1000,q['speed_cm_s'],marker=marker,color=color,ms=4,ls='none')
    axes[0,0].set(ylabel='OH mass fraction',title='Both fronts: saved checkpoint states')
    axes[0,1].set(ylabel='Temperature (K)',title='Both fronts: saved checkpoint states')
    axes[1,0].set(ylabel='Local S*d (cm/s)',title='Instantaneous chemistry + deployed diffusion')
    axes[1,1].set(ylabel='Local S*d (cm/s)',title='Chemistry source and diffusion used in replay')
    for ax in axes.flat:
        ax.set(xlim=(1.80,1.98),xlabel='Position x (mm)');ax.grid(alpha=.15);ax.legend(fontsize=7)
    for ax in axes[0]:ax.set_xlim(1.75,2.25)
    for ax in axes[1]:
        ax.set_yscale('symlog',linthresh=10);ax.axhline(6.8,color='k',ls=':',lw=.9)
    fig.suptitle('Products-seeded flame: spatial displacement-speed audit',fontsize=12)
    fig.text(.5,.025,'Symbols: OH = 1e−5 (circle), 2e−5 (square), 3e−5 (triangle). Dotted: paper ≈6.8 cm/s.\nSpeed axes: symmetric log, linear within ±10 cm/s. Fresh-side rising flank; small gradients masked. Replay ≠ historical RR.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.075,1,.96))
    for ext in ['png','svg']:fig.savefig(output/('spatial-speed.'+ext),dpi=200)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4.8))
    for i,(time,stages) in enumerate(profiles):
        data=display_profile(stages['instantaneous_checkpoint']);four,mask,_=speed(data);two,_,_=speed(data,'diffusion_Fick_kg_m3_s')
        axes[0].plot(data['YOH'][mask],four[mask],color=f'C{i}',label=f'{time*1e6:.2f} µs, deployed')
        axes[0].plot(data['YOH'][mask],two[mask],color=f'C{i}',ls='--',label=f'{time*1e6:.2f} µs, Eq.39 Fick')
    data=display_profile(profiles[-1][1]['instantaneous_checkpoint']);_,mask,_=speed(data)
    denom=data['rho_unburned_kg_m3']*np.maximum(abs(data['gradOH_1_m']),1e-300)
    for field,label,color in [('omegaOH_kg_m3_s','Chemistry','C3'),('diffusion_used_kg_m3_s','Deployed diffusion','C0'),('diffusion_Fick_kg_m3_s','Eq.39 Fick diffusion','C2')]:
        axes[1].plot(data['YOH'][mask],100*data[field][mask]/denom[mask],label=label,color=color)
    axes[0].set_title('Instantaneous local speed vs OH marker')
    axes[1].set_title(f'Contributions at {profiles[-1][0]*1e6:.2f} µs')
    for ax in axes:
        ax.set(xlim=(1e-6,1e-4),xlabel='OH mass fraction',ylabel='Density-weighted contribution (cm/s)')
        ax.set_xscale('log');ax.set_yscale('symlog',linthresh=10);ax.grid(alpha=.15);ax.legend(fontsize=7)
        for level in [1e-5,2e-5,3e-5]:ax.axvline(level,color='.65',lw=.5)
    axes[0].axhline(6.8,color='k',ls=':',lw=.9)
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(output/('spatial-flux-audit.'+ext),dpi=200)
    plt.close(fig)
    result={'measurements':measurements,'inputs':receipts,
        'live_history_sha256':hashlib.sha256(raw).hexdigest(),'ignored_live_partial_bytes':len(raw)-end,
        'gradient_mask':'left rising flank before OH maximum; YOH>=1e-7; gradOH>max(1e-6,0.001*peak abs gradient)',
        'units':'SI inputs; speeds multiplied by 100 for cm/s',
        'max_reload_difference_cm_s':max(abs(r.get('reload_difference_cm_s',0)) for r in measurements)}
    (output/'analysis.json').write_text(json.dumps(result,indent=2))
    for row in measurements:
        if row['level']==2e-5 and row['side']=='left':
            print({k:row[k] for k in ['checkpoint_time_s','stage','speed_cm_s','fick_speed_cm_s','chemistry_cm_s','diffusion_cm_s']})
    print('Maximum reload/live difference (cm/s):',result['max_reload_difference_cm_s'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();analyze(a.root,a.output)
