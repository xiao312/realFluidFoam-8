"""Paper-layout radial comparison; physical flamelets are never plotted as coflow data."""
import argparse
import json
from pathlib import Path
import hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def pchip(x,y,q):
    """Shape-preserving Hermite display interpolation; no extrapolation."""
    h=np.diff(x);delta=np.diff(y)/h;d=np.zeros(len(x))
    if len(x)==2:return np.interp(q,x,y)
    for i in range(1,len(x)-1):
        if delta[i-1]*delta[i]>0:
            a=2*h[i]+h[i-1];b=h[i]+2*h[i-1]
            d[i]=(a+b)/(a/delta[i-1]+b/delta[i])
    for index,a,b,ha,hb in [(0,delta[0],delta[1],h[0],h[1]),(-1,delta[-1],delta[-2],h[-1],h[-2])]:
        value=((2*ha+hb)*a-ha*b)/(ha+hb)
        if value*a<=0:value=0
        elif a*b<0 and abs(value)>abs(3*a):value=3*a
        d[index]=value
    index=np.clip(np.searchsorted(x,q,side='right')-1,0,len(x)-2)
    t=(q-x[index])/h[index]
    return (2*t**3-3*t**2+1)*y[index]+(t**3-2*t**2+t)*h[index]*d[index]+(-2*t**3+3*t**2)*y[index+1]+(t**3-t**2)*h[index]*d[index+1]


def read_samples(directory,height):
    prefix='h10' if height==.01 else 'h40'
    files=list(directory.glob(prefix+'*.csv'))
    for file in files:
        data=np.genfromtxt(file,delimiter=',',names=True)
        names=data.dtype.names or ()
        if 'T' not in names or not ('CO' in names or 'Y_CO' in names):continue
        if names[0] not in ['y','distance','r','coord']:
            raise ValueError('Unexpected radial coordinate '+str(names[0])+': '+str(file))
        x=np.asarray(data[names[0]])
        if np.any(np.diff(x)<=0):raise ValueError('Sample radius must increase strictly')
        return file,{'r_m':x,'T_K':np.asarray(data['T']),'Y_CO':np.asarray(data['CO' if 'CO' in names else 'Y_CO'])}
    raise ValueError('No T/CO radial CSV for '+prefix+' in '+str(directory))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--samples',type=Path,required=True)
    p.add_argument('--time',type=float,required=True)
    p.add_argument('--job-id',required=True)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--plan',action='store_true')
    a=p.parse_args()
    if a.plan:
        print(json.dumps({'paper_reference':str(a.reference),'samples':str(a.samples),'time_s':a.time,'CFD_job':a.job_id,'out':str(a.out)}));return
    if not a.job_id.isdigit() or len(a.source_commit)!=40:raise ValueError('Exact run/source identity required')
    a.out.mkdir(parents=True,exist_ok=False)
    reference=json.loads(a.reference.read_text(encoding="utf-8"))
    samples={height:read_samples(a.samples,height) for height in [.01,.04]}
    plt.rcParams.update({'font.family':'Arial','font.size':9,'axes.labelsize':9,'xtick.labelsize':8.5,'ytick.labelsize':8.5,'legend.fontsize':7.5,'svg.fonttype':'none','axes.linewidth':.4})
    fig=plt.figure(figsize=(6.7,5.05))
    positions=[[.105,.625,.355,.35],[.605,.625,.355,.35],[.12,.14,.345,.35],[.615,.14,.345,.35]]
    metrics=[];artifacts={}
    for index,curve in enumerate(reference['curves']):
        ax=fig.add_axes(positions[index]);height=curve['height_m'];quantity=curve['quantity']
        points=curve['points'];x=np.array([p['r_m'] for p in points]);y=np.array([p['value'] for p in points])
        dense=np.linspace(x[0],x[-1],600)
        ax.plot(dense,pchip(x,y,dense),color='#252525',lw=.75,label='Detailed — paper')
        file,data=samples[height];sx=data['r_m'];sy=data[quantity]
        if not np.isfinite(sy).all():raise ValueError('Nonfinite sampled CFD field')
        # All samples remain in metrics/data; thin markers only for readability.
        ax.plot(sx[::4],sy[::4],linestyle='none',marker='o',ms=2.5,mew=0,color='#7451b8',label=f'Our OF8 · {1000*a.time:.3g} ms')
        ax.set_xlim(0,.03);ax.set_ylim(*curve['yrange'])
        ax.set_xlabel(f'Radial distance for H = {height:g} [m]')
        ax.set_ylabel('Temperature [K]' if quantity=='T_K' else 'CO mass fraction')
        ax.tick_params(colors='#808080',length=0,pad=4)
        for spine in ax.spines.values():spine.set_color('#808080')
        ax.grid(True,color='#999999',linestyle=(0,(1,4)),linewidth=.35)
        ax.set_axisbelow(True);ax.legend(loc='upper right',framealpha=1,edgecolor='black',fancybox=False,borderpad=.3,handlelength=2)
        ax.text(.5,-.32,f'({"abcd"[index]})',transform=ax.transAxes,ha='center',va='top',fontsize=8)
        covered=(x>=sx[0])&(x<=sx[-1]);delta=np.interp(x[covered],sx,sy)-y[covered]
        metrics.append({'panel':'abcd'[index],'height_m':height,'quantity':quantity,'reference_points':len(x),
            'covered_reference_points':int(covered.sum()),'RMSE':float(np.sqrt(np.mean(delta**2))),
            'max_abs_error':float(abs(delta).max()),'computed_min':float(sy.min()),'computed_max':float(sy.max()),
            'sample_file':str(file),'sample_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
            'reference_series':'Detailed - Verhoeven; digitized filled squares'})
    for suffix in ['svg','png']:
        file=a.out/('figure4.'+suffix);fig.savefig(file,dpi=220,facecolor='white');artifacts[file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
    plt.close(fig)
    report={'schema':'maders-figure4-comparison/v1','job_id':a.job_id,'source_commit':a.source_commit,
        'sample_time_s':a.time,'plotter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'matplotlib_version':matplotlib.__version__,'metrics':metrics,'artifacts':artifacts,
        'reference_sha256':hashlib.sha256(a.reference.read_bytes()).hexdigest(),
        'style':{'size_inches':[6.7,5.05],'paper':'PCHIP display lines; raw marker coordinates for metrics','ours':'Markers; no smoothing; every fourth sample displayed','xlim_m':[0,.03]},
        'scientific_acceptance':False,'status':'Startup comparison; steady state is not inferred from job completion'}
    (a.out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
