"""Render retained instantaneous G2 observations beside identified paper targets."""
import argparse
import csv
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SHARED = HERE.parent/'g2-review'
sys.path.insert(0, str(SHARED))
from inputs import load_case, read_csv, sha256

spec = importlib.util.spec_from_file_location('shared_g2_review', SHARED/'review.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
from references import load_targets


def proxies(data, phase, out, identity):
    records = [r for r in data['records'] if r['kind']=='instantaneous' and r['geometry']=='plane']
    missing = [r['time_s'] for r in records if not {'x','y','z','T','rho','OH'} <= r['fields'].keys()]
    if not records or missing:
        return {}, [f'LTE proxy not computed: missing actual co-located T/rho/OH plane at {missing or "all times"}.']
    manifest = {'schema':'oh-lte-samples/v1','phaseMetadata':str(phase.resolve()),
        'sampling':{'instantaneous':True,'kind':'instantaneous-cfd'},'provenance':identity,
        'frames':[{'time_s':r['time_s'],'files':r['paths']} for r in sorted(records,key=lambda r:r['time_s'])],
        'averaging':None}
    manifest_path = out/'optical-input.json'
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    result = subprocess.run(['node',str(HERE.parent/'oh-lte-proxy'/'run.mjs'),'--manifest',str(manifest_path),
                             '--out',str(out/'optical'),'--apply'],capture_output=True,text=True,check=False)
    (out/'optical-command.json').write_text(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},indent=2)+'\n')
    if result.returncode:
        raise RuntimeError('LTE calculation failed; retained command result explains the failure')
    return {frame['time_s']:read_csv(out/'optical'/f'instant-{i:04d}.csv') for i,frame in enumerate(manifest['frames'])}, []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('case','targets','sharma-reference','sharma-pdf','run-record','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--phase-metadata',type=Path)
    parser.add_argument('--x-origin-m',required=True,type=float)
    parser.add_argument('--origin-note',required=True)
    parser.add_argument('--label',default='Paper-exit 10k wedge, source-on pilot')
    parser.add_argument('--time',type=float,action='append')
    parser.add_argument('--apply',action='store_true')
    args = parser.parse_args()
    if not math.isfinite(args.x_origin_m) or not args.origin_note.strip() or any(not math.isfinite(t) or t<0 for t in args.time or []):
        raise ValueError('Require finite origin/times and an explicit coordinate evidence note')
    data = load_case(args.case,args.time)
    data['records'] = [r for r in data['records'] if r['kind']=='instantaneous']
    if not data['records']:
        raise ValueError('This preliminary renderer requires actual instantaneous observations')
    references = load_targets(args.targets)
    sharma, original = shared.paper(args.sharma_reference,args.sharma_pdf)
    identity = json.loads(args.run_record.read_text())
    if not isinstance(identity,dict) or not identity:
        raise ValueError('Run record must identify the actual source/job and mesh; empty record rejected')
    hashes = {**data['input_hashes'],**references['hashes']}
    for path in [args.sharma_reference,args.sharma_pdf,args.run_record]+([args.phase_metadata] if args.phase_metadata else []):
        hashes[str(path.resolve())]=sha256(path)
    plan = {'schema':'g2-paper-comparison/v1','mode':'apply' if args.apply else 'read-only-plan',
        'case':str(args.case.resolve()),'out':str(args.out.resolve()),'input_hashes':hashes,
        'x_origin_m':args.x_origin_m,'origin_note':args.origin_note,'sample_groups':len(data['records']),
        'times_s':sorted(set(r['time_s'] for r in data['records'])), 'optional_lte':bool(args.phase_metadata),
        'scientific_acceptance':False,'statistical_convergence_established':False}
    if not args.apply:
        print(json.dumps(plan,indent=2)); return
    if any(sha256(path)!=expected for path,expected in hashes.items()):
        raise ValueError('Inputs changed before render; preserve a frozen snapshot first')
    args.out.mkdir(parents=True,exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR',str((args.out/'matplotlib-cache').resolve()))
    os.environ['MPLBACKEND']='Agg'
    from plots import centerline, style
    from figures import radial, maps
    from page import write_page
    style()
    (args.out/'original-figure4b.png').write_bytes(original)
    for key in references['targets']:
        shutil.copyfile(args.targets/(key+'.png'),args.out/('original-'+key+'.png'))
    panels, missing = radial(data,references,args.out,args.x_origin_m)
    for panel in centerline(data,sharma,args.out,args.x_origin_m,'Our instant'):
        panel['meaning']='Our instantaneous near-axis startup versus the paper temporal means; no temperature acceptance score.'
        panels.append(panel)
    optical, optical_missing = proxies(data,args.phase_metadata,args.out,identity) if args.phase_metadata else ({},['LTE proxy not requested; no optical observable inferred.'])
    image_panels, image_missing = maps(data,args.out,args.x_origin_m,optical)
    panels.extend(image_panels)
    (args.out/'data').mkdir()
    samples=[]
    for index,record in enumerate(data['records']):
        with (args.out/'data'/f'{index:03d}-{record["name"]}-{record["time_s"]:.9g}.csv').open('w',newline='') as handle:
            writer=csv.writer(handle); writer.writerow(record['fields']); writer.writerows(zip(*record['fields'].values()))
        samples.append({**{k:v for k,v in record.items() if k!='fields'},
            'ranges':{k:{'min':float(v.min()),'max':float(v.max())} for k,v in record['fields'].items()}})
    limitations = missing+image_missing+optical_missing+data['manifest'].get('approximations',[])+[
        'Instantaneous startup and paper temporal means are different statistics; no invented RMS.',
        'A 100 microsecond pilot does not establish developed flow at 15/45/70 mm.',
        'Ground-state OH, LTE excited population and camera OH* emission are distinct quantities.',
        'No line-of-sight calculation, optical calibration or scientific approval.',
        f'Missing sample categories: {data["missing_categories"]}',
        f'Missing requested times: {data["missing_requested_times"]}']
    source_hashes={}
    for directory in [HERE,SHARED,HERE.parent/'oh-lte-proxy']:
        for path in directory.iterdir():
            if path.suffix in ('.py','.md','.mjs'):
                source_hashes[str(path.relative_to(HERE.parent))]=sha256(path)
    summary={**plan,'label':args.label,'created_at':datetime.now(timezone.utc).isoformat(),
        'run_identity':identity,'source_hashes':source_hashes,'samples':samples,'panels':panels,'limitations':limitations,
        'case_conditions':{k:data['manifest'].get(k) for k in ['pressure','energyForm','streams','mesh','meshMode','sourceIntegration','boundsPolicy']},
        'producer_report':data['report'],'reference_preparation_receipt':str((args.targets/'receipt.json').resolve())}
    write_page(args.out,summary,panels,references['targets'],{'caption':shared.CAPTION,'paper':shared.PAPER,'url':shared.URL})
    summary['output_hashes']={str(p.relative_to(args.out)):sha256(p) for p in args.out.rglob('*') if p.is_file() and 'matplotlib-cache' not in p.parts}
    (args.out/'receipt.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'out':str(args.out.resolve()),'panels':len(panels),'times_s':plan['times_s'],'scientific_acceptance':False}))


if __name__=='__main__':
    main()
