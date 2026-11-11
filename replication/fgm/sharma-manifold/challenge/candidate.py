"""Physical seed: separate solved burnt reference and one declared quenching path."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np


def interpolate_z(z,values,f):
    hi=int(np.searchsorted(z,f));hi=max(1,min(len(z)-1,hi));lo=hi-1
    w=(f-z[lo])/(z[hi]-z[lo])
    return (1-w)*values[...,lo,:]+w*values[...,hi,:]


def first_downward_crossing(progress,values,queries):
    # Choose a chronological quenching segment, never interleave distinct paths.
    start=int(np.argmax(progress));output=[];counts=[]
    for target in queries:
        matches=[i for i in range(start+1,len(progress))
                 if progress[i-1]>=target>=progress[i] and progress[i-1]>progress[i]]
        counts.append(len(matches))
        if not matches:output.append(np.full(values.shape[-1],np.nan));continue
        i=matches[0];w=(progress[i-1]-target)/(progress[i-1]-progress[i])
        output.append((1-w)*values[i-1]+w*values[i])
    return np.asarray(output),counts


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--replay',type=Path);args=p.parse_args()
    root=args.config.resolve().parent;config=json.loads(args.config.read_text());physical=args.replay
    if physical is None:
        physical=args.output.parent/'physical'
        subprocess.run([sys.executable,str(root/'physics/run.py'),'--mechanism',str(root/'inputs/zk-author-2019.yaml'),
                        '--out',str(physical)],check=True,timeout=850)
    receipt=json.loads((physical/'receipt.json').read_text())
    for name,digest in receipt['files'].items():
        assert hashlib.sha256((physical/name).read_bytes()).hexdigest()==digest
    eq=np.load(physical/'equilibrium-initial.npz');species=list(eq['species'])
    raw=np.load(physical/'chi-2000000.npz');low=np.load(physical/'chi-10000.npz')
    fields=np.concatenate([raw['T'][...,None],raw['Y']],axis=-1)
    co=species.index('CO');co2=species.index('CO2');curves={};diagnostics={}
    c=np.asarray(config['progress_queries'])
    for f in config['mixture_fractions']:
        local=interpolate_z(raw['Z'],fields,f)
        equilibrium=interpolate_z(eq['Z'],eq['Y'],f)
        progress=(local[:,1+co]+local[:,1+co2])/(equilibrium[co]+equilibrium[co2])
        sampled,counts=first_downward_crossing(progress,local,c)
        for name,col in [('T',0),('CO2',1+co2)]:
            curves[f'fig2-{name}-f{f:g}']={'x':c.tolist(),'y':[float(v) if np.isfinite(v) else None for v in sampled[:,col]]}
        diagnostics[str(f)]={'c_max':float(progress.max()),'queries_with_multiple_crossings':sum(n>1 for n in counts)}
    z=np.asarray(config['mixture_queries'])
    curves['fig1-T-burnt']={'x':z.tolist(),'y':np.interp(z,low['Z'],low['T'][-1]).tolist()}
    for name in ['CH4','O2','CO2','CO','H2O','OH']:
        curves[f'fig1-{name}-burnt']={'x':z.tolist(),'y':np.interp(z,low['Z'],low['Y'][-1,:,species.index(name)]).tolist()}
    output={'curves':curves,'provenance':{'method':'One explicit high-chi quenching path, first downward crossing after maximum C; no cross-path pooling.',
        'burnt_reference':'Actual final chi=10000 flamelet, not assumed to equal paper c=1.',
        'physical_directory':str(physical),'reference_data_used_at_runtime':False,'crossings':diagnostics,
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scientific_acceptance':False}}
    args.output.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n',encoding='utf-8')


if __name__=='__main__':main()
