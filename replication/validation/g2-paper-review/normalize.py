"""Explicitly deduplicate identical processor-boundary samples; conflicting data fail."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'g2-review'))
from inputs import read_csv,sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('case','run-record','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    inputs={str(args.run_record.resolve()):sha256(args.run_record)}
    prepared=[];audits=[]
    for path in sorted((args.case/'postProcessing').rglob('*.csv')):
        fields=read_csv(path)
        columns=list(fields)
        coordinates=[name for name in ('x','y','z') if name in fields]
        data=np.column_stack(list(fields.values()))
        points=np.column_stack([fields[key] for key in coordinates])
        unique,first,inverse,counts=np.unique(points,axis=0,return_index=True,return_inverse=True,return_counts=True)
        duplicates=[]
        for i in np.flatnonzero(counts>1):
            indices=np.flatnonzero(inverse==i)
            if not np.array_equal(data[indices],np.repeat(data[indices[:1]],len(indices),axis=0)):
                raise ValueError(f'Conflicting repeated coordinate in {path}: {unique[i]}')
            duplicates.append({'coordinate':dict(zip(coordinates,map(float,unique[i]))),'count':int(counts[i])})
        kept=np.sort(first)
        inputs[str(path.resolve())]=sha256(path)
        prepared.append((path,columns,data[kept]))
        audits.append({'path':str(path.relative_to(args.case)),'raw_rows':len(data),'retained_rows':len(kept),
            'duplicates_removed':len(data)-len(kept),'duplicates':duplicates})
    if not prepared:
        raise ValueError('No actual sampled CSVs found')
    for path in args.case.glob('*.json'):
        inputs[str(path.resolve())]=sha256(path)
    receipt={'schema':'exact-sample-deduplication/v1','mode':'apply' if args.apply else 'read-only-plan',
        'policy':'Only identical values at exactly repeated coordinates; retain first row/order. No averaging, tolerance or interpolation.',
        'source_sha256':sha256(Path(__file__)),'input_hashes':inputs,'files':audits,
        'removed_rows':sum(a['duplicates_removed'] for a in audits),'scientific_acceptance':False}
    if not args.apply:
        print(json.dumps(receipt,indent=2));return
    if any(sha256(path)!=expected for path,expected in inputs.items()):
        raise ValueError('Snapshot changed while preparing derived samples')
    args.out.mkdir(parents=True,exist_ok=False)
    case=args.out/'case';case.mkdir()
    for path in args.case.glob('*.json'):
        shutil.copyfile(path,case/path.name)
    for path,columns,data in prepared:
        destination=case/path.relative_to(args.case)
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('w',newline='') as handle:
            writer=csv.writer(handle);writer.writerow(columns)
            writer.writerows([[format(value,'.17g') for value in row] for row in data])
    receipt['output_hashes']={str(p.relative_to(args.out)):sha256(p) for p in case.rglob('*') if p.is_file()}
    (args.out/'derivation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    run=json.loads(args.run_record.read_text(encoding='utf-8'))
    run['sample_derivation']={'kind':receipt['schema'],'receipt_sha256':sha256(args.out/'derivation.json'),
        'receipt_path':str((args.out/'derivation.json').resolve()),'original_run_record_sha256':sha256(args.run_record),
        'removed_identical_rows':receipt['removed_rows']}
    (args.out/'run-record.json').write_text(json.dumps(run,indent=2)+'\n')
    print(json.dumps({'out':str(args.out.resolve()),'removed_identical_rows':receipt['removed_rows'],'scientific_acceptance':False}))


if __name__=='__main__':
    main()
