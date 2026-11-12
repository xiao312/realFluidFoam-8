"""Mapped weighted-C linear interpolation; consumes only declared training profiles."""
import argparse
import json
from pathlib import Path
import numpy as np


def build(paths):
    profiles=[np.load(p) for p in paths]
    z=profiles[0]['Z']
    if any(not np.array_equal(p['Z'],z) for p in profiles):
        raise ValueError('Training grids differ; explicit remapping is required')
    rows=[]
    for j in range(len(z)):
        values=np.array([[p['C'][j],p['T'][j],p['Sc_kg_m3_s'][j],*p['Y'][j]] for p in profiles])
        values=values[np.argsort(values[:,0])]
        axis,indices,counts=np.unique(values[:,0],return_index=True,return_counts=True)
        for start,count in zip(indices,counts):
            if count>1 and np.max(abs(values[start:start+count,1:]-values[start,1:]))>1e-6:
                raise ValueError('Ambiguous equal-C training states; choose a physical branch explicitly')
        rows.append((axis,values[indices,1:]))
    return z,rows


def query(model,z,c):
    grid,rows=model
    if not np.isfinite([z,c]).all() or z<grid[0] or z>grid[-1]:
        raise ValueError('Z outside training coverage')
    i=min(len(grid)-2,max(0,int(np.searchsorted(grid,z,side='right')-1)))
    w=(z-grid[i])/(grid[i+1]-grid[i])
    low=(1-w)*rows[i][0][0]+w*rows[i+1][0][0]
    high=(1-w)*rows[i][0][-1]+w*rows[i+1][0][-1]
    if c<low-1e-12 or c>high+1e-12:
        raise ValueError('C outside local physical coverage')
    if high-low<=1e-14:
        return (1-w)*rows[i][1][0]+w*rows[i+1][1][0]
    eta=(c-low)/(high-low)
    output=[]
    for row in [rows[i],rows[i+1]]:
        axis,values=row
        local=axis[0]+eta*(axis[-1]-axis[0])
        output.append(np.array([np.interp(local,axis,values[:,k]) for k in range(values.shape[1])]))
    return (1-w)*output[0]+w*output[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--training',type=Path,required=True)
    p.add_argument('--queries',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    training=json.loads(a.training.read_text())
    model=build([a.training.parent/path for path in training['profiles']])
    coordinates=np.load(a.queries)
    values=[];covered=[]
    for z,c in zip(coordinates['Z'],coordinates['C']):
        try:
            value=query(model,float(z),float(c));covered.append(True)
        except ValueError:
            value=np.full(2+training['species_count'],np.nan);covered.append(False)
        values.append(value)
    values=np.asarray(values)
    if a.out.exists():raise ValueError('Refusing existing predictions')
    np.savez_compressed(a.out,T=values[:,0],Sc_kg_m3_s=values[:,1],Y=values[:,2:],covered=covered)


if __name__=='__main__':main()
