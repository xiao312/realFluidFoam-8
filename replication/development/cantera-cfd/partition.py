"""Create a static, balanced decomposition of the pinned original-zero flame."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'validation/flames/adaptive'))
from fields import scalar

MESH_SHA='4075a578ba36a276976046094a8db6aa54be819e0fa504048fef355ab7411b99'


def mapping():
    owners=[-1]*8000
    bands=[list(range(3800,4200)),list(range(3200,3800))+list(range(4200,4800)),
           list(range(3200))+list(range(4800,8000))]
    for index,band in enumerate(bands):
        for rank in range(32):
            owner=31-rank if index==1 else rank
            for cell in band[rank*len(band)//32:(rank+1)*len(band)//32]:
                if owners[cell]!=-1:raise ValueError('Overlapping partition bands')
                owners[cell]=owner
    if any(owners.count(rank)!=250 for rank in range(32)):
        raise ValueError('Unbalanced or incomplete cell assignment')
    return owners


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply'])
    parser.add_argument('case',type=Path)
    parser.add_argument('profile',choices=['bands32'])
    args=parser.parse_args();case=args.case
    mesh=case/'system/blockMeshDict'
    if hashlib.sha256(mesh.read_text().encode()).hexdigest()!=MESH_SHA:
        raise ValueError('Partition only supports the pinned 8000-cell planar mesh')
    hot=[i for i,t in enumerate(scalar(case/'0/T',8000)) if t>1000]
    if hot!=list(range(3800,4200)):
        raise ValueError('Expected the original 400-cell products slab')
    target=case/'constant/cellDecomposition'
    if target.exists() or any(case.glob('processor[0-9]*')):
        raise ValueError('Partition requires a fresh undecomposed case')
    owners=mapping()
    report=dict(execution_profile=args.profile,ranks=32,cells_per_rank=250,
                hot_cells_per_rank=[sum(owners[i]==rank for i in hot) for rank in range(32)],
                internal_partition_interfaces=sum(a!=b for a,b in zip(owners,owners[1:])),
                original_temperature_sha256=hashlib.sha256((case/'0/T').read_bytes()).hexdigest())
    print(json.dumps(report,indent=2))
    if args.action=='plan':return
    target.write_text('FoamFile {version 2.0; format ascii; class labelList; object cellDecomposition;}\n'
                      '8000\n(\n'+'\n'.join(map(str,owners))+'\n)\n')
    (case/'system/decomposeParDict').write_text(
        'FoamFile {version 2.0; format ascii; class dictionary; object decomposeParDict;}\n'
        'numberOfSubdomains 32;\nmethod manual;\nmanualCoeffs {dataFile cellDecomposition;}\n')
    (case/'partition-inputs.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
