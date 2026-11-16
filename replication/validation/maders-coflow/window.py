"""Finite-window profile statistics from bound samples; no steady-state claim."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from plot import read_samples


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrate(times, values):
    """Exact first/second moments of the piecewise-linear sampled history."""
    dt = np.diff(times)[:, None]
    duration = times[-1] - times[0]
    mean = np.sum(dt * (values[:-1] + values[1:]) / 2, axis=0) / duration
    # Integrate centered values directly; E[x²]-E[x]² loses small fluctuations.
    left, right = values[:-1]-mean, values[1:]-mean
    variance = np.sum(dt * (left**2 + left*right + right**2) / 3, axis=0) / duration
    return mean, np.sqrt(variance)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['samples', 'collection', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ['start', 'end']:
        parser.add_argument('--' + name, type=float, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.start < args.end or not np.isfinite([args.start,args.end]).all():
        raise ValueError('Explicit finite increasing time window required')
    collection = json.loads(args.collection.read_text())
    if collection['startTime'] != 0 or args.start < collection['ignition_s']:
        raise ValueError('Fresh-zero post-ignition profiles required')
    bound = {key.replace('\\','/'):value for key,value in collection['inputs'].items()}
    times = sorted((float(p.name),p) for p in args.samples.iterdir()
                   if p.is_dir() and args.start <= float(p.name) <= args.end)
    if len(times) < 3:
        raise ValueError('At least three actual times inside the window required')
    time_values = np.array([t for t,_ in times])
    inputs = {}
    outputs = {}
    for height in [.01,.04]:
        arrays = []
        radius = None
        for _,directory in times:
            file,data = read_samples(directory,height)
            key = 'postProcessing/radialProfiles/' + str(file.relative_to(args.samples)).replace('\\','/')
            if digest(file) != bound[key]:
                raise ValueError('Sample differs from retained collection: ' + key)
            inputs[str(file.resolve())] = digest(file)
            if radius is not None and not np.array_equal(radius,data['r_m']):
                raise ValueError('Radial sample coordinates changed inside window')
            radius = data['r_m']
            arrays.append(np.column_stack([data['T_K'],data['Y_CO']]))
        values = np.asarray(arrays)
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite captured temperature or CO')
        mean,std = integrate(time_values,values.reshape(len(times),-1))
        outputs[height] = (radius,mean.reshape(-1,2),std.reshape(-1,2))
    report = dict(schema='maders-temporal-window/v1',job_id=collection['job'],startTime=0,
        requestedWindow_s=[args.start,args.end],actualWindow_s=[times[0][0],times[-1][0]],
        actualTimes_s=time_values.tolist(),sampleCount=len(times),
        quadrature='Exact first/second moments of piecewise-linear saved histories; no extrapolation',
        collectionSha256=digest(args.collection),inputHashes=inputs,codeSha256=digest(Path(__file__)),
        spatialInterpolation=False,steadyStateEstablished=False,scientificAcceptance=False,
        readOnly=not args.apply)
    if args.apply:
        args.out.mkdir(parents=True,exist_ok=False)
        samples = args.out/'samples'
        samples.mkdir()
        for height,(radius,mean,std) in outputs.items():
            file = samples/f'h{int(height*1000)}_T_CO.csv'
            with file.open('w',newline='') as handle:
                writer=csv.writer(handle)
                writer.writerow(['y','T','CO','T_temporal_std','CO_temporal_std'])
                writer.writerows(zip(radius,mean[:,0],mean[:,1],std[:,0],std[:,1]))
        report['outputHashes']={str(p.relative_to(args.out)).replace('\\','/'):digest(p) for p in samples.iterdir()}
        (args.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
