"""Check the exported table on frozen held-out coordinates without changing them."""
import argparse
from pathlib import Path
import subprocess
import sys
import numpy as np
from lookup_baseline import query


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table',type=Path,required=True)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    table=np.load(args.table);ref=np.load(args.reference)
    if not np.array_equal(table['species'],ref['species']):raise ValueError('Species identities differ')
    grid=table['Z'];eta=table['eta'];lower=table['c_min'];upper=table['c_max']
    fields=table['values'];rows=[]
    for i in range(len(grid)):
        c=lower[i]+eta*(upper[i]-lower[i])
        # Remove diagnostic Q; query returns T, source and species in fixed order.
        values=np.column_stack([fields[i,:,0],fields[i,:,1],fields[i,:,3:]])
        axis,indices=np.unique(c,return_index=True)
        rows.append((axis,values[indices]))
    model=(grid,rows);predictions=[];covered=[]
    for z,c in zip(ref['Z'],ref['C']):
        try:
            predictions.append(query(model,float(z),float(c)));covered.append(True)
        except ValueError:
            predictions.append(np.full(2+len(table['species']),np.nan));covered.append(False)
    values=np.array(predictions)
    args.out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(args.out/'predictions.npz',T=values[:,0],Sc_kg_m3_s=values[:,1],
                        Y=values[:,2:],covered=covered)
    subprocess.run([sys.executable,str(Path(__file__).with_name('evaluate_lookup.py')),
        '--reference',str(args.reference),'--predictions',str(args.out/'predictions.npz'),
        '--out',str(args.out/'metrics.json')],check=True)


if __name__=='__main__':main()
