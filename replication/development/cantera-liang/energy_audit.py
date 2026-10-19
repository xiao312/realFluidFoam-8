"""Audit reconstructed energy flux from frozen, explicitly labelled profiles."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply'])
    for name in ['root','build','sdk','manifest','output']:parser.add_argument(name,type=Path)
    args=parser.parse_args();root=args.root.resolve(strict=True)
    def contained(path):
        path=path.resolve(strict=True);path.relative_to(root);return path
    build,sdk,manifest=map(contained,[args.build,args.sdk,args.manifest])
    output=args.output.resolve();output.relative_to(root)
    if output.exists():raise ValueError('Use a new energy-audit output directory')
    records=json.loads(manifest.read_text());binary=build/'energy-probe'
    checksum=(build/'energy-binary.sha256').read_text().split()
    if len(checksum)!=2 or checksum[1]!='energy-probe' or digest(binary)!=checksum[0]:
        raise ValueError('Energy probe checksum mismatch')
    for record in records:
        if not str(record['profile_job']).isdigit() or record['stage'] not in range(1,6):
            raise ValueError('Invalid profile job or stage')
        contained(root/'jobs'/str(record['profile_job'])/'result/profile.csv')
        contained(Path(record['inputs']))
        pressure=record['pressure_atm']
        if not math.isfinite(pressure) or not 1<=pressure<=100:raise ValueError('Pressure outside qualified range')
    print(json.dumps(dict(action=args.action,profiles=len(records),output=str(output),binary_sha256=checksum[0])))
    if args.action=='plan':return
    job=os.environ.get('SLURM_JOB_ID','')
    if not job.isdigit():raise ValueError('Apply requires a scheduler allocation')
    output.relative_to(root/'jobs'/job)
    output.mkdir(parents=True)
    env=dict(os.environ,LD_LIBRARY_PATH=str(sdk/'lib')+':'+os.environ.get('LD_LIBRARY_PATH',''),
             CANTERA_DATA=str(sdk/'share/cantera/data'),OMP_NUM_THREADS='1')
    reports=[]
    for index,record in enumerate(records):
        profile=root/'jobs'/str(record['profile_job'])/'result/profile.csv';inputs=Path(record['inputs'])
        target=output/('energy-'+str(index)+'.csv')
        subprocess.run([str(binary),str(inputs),str(record['stage']),str(profile),str(target),
                        record['variant'],str(record['pressure_atm'])],env=env,check=True)
        with target.open() as stream:rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(stream)]
        if len(rows)<10 or not all(math.isfinite(v) for row in rows for v in row.values()):
            raise ValueError('Invalid reconstructed flux')
        values=[r['total_W_m2'] for r in rows];scale=max(abs(r['conductive_W_m2']) for r in rows)
        if scale<=0:raise ValueError('No conductive flux scale')
        reports.append(dict(record,profile_sha256=digest(profile),
            input_sha256={p.name:digest(p) for p in inputs.iterdir() if p.is_file()},
            total_range_W_m2=max(values)-min(values),endpoint_difference_W_m2=values[-1]-values[0],
            peak_conductive_W_m2=scale,range_over_peak_conduction=(max(values)-min(values))/scale,
            maximum_mass_diffusion_sum_kg_m2s=max(abs(r['mass_diffusion_sum_kg_m2s']) for r in rows)))
    result=dict(binary_sha256=checksum[0],manifest_sha256=digest(manifest),
                audit_script_sha256=digest(Path(__file__)),profiles=reports,scientific_acceptance=False)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
