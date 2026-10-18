"""Validate rank-local inlet properties or prepare a small serial/MPI fixture."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

PROPERTIES=['rho_kg_m3','Cp_J_kg_K','Cv_J_kg_K']
TOLERANCE=1e-12


def read(path):
    with path.open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    result={}
    for row in rows:
        patch=row['patch']
        if patch not in ['fuel','oxidizer']:continue
        if patch in result:raise ValueError('Duplicate inlet patch in '+str(path))
        values={key:float(row[key]) for key in PROPERTIES}
        if not all(math.isfinite(v) and v>0 for v in values.values()):
            raise ValueError('Invalid inlet properties in '+str(path))
        result[patch]=values
    return result


def collect(case,ranks,reference):
    expected=read(reference)
    if set(expected)!={'fuel','oxidizer'}:raise ValueError('Incomplete serial reference')
    values={patch:[] for patch in expected};hashes={}
    for rank in range(ranks):
        path=case/('processor'+str(rank))/'inlet-densities.csv'
        hashes[str(path.relative_to(case))]=hashlib.sha256(path.read_bytes()).hexdigest()
        for patch,row in read(path).items():values[patch].append((rank,row))
    combined={};report={}
    for patch,rows in values.items():
        if not rows:raise ValueError('No rank owns inlet '+patch)
        errors={key:max(abs(row[key]/expected[patch][key]-1) for _,row in rows) for key in PROPERTIES}
        if max(errors.values())>TOLERANCE:raise ValueError('Serial/MPI disagreement: '+patch+' '+str(errors))
        combined[patch]={key:sum(row[key] for _,row in rows)/len(rows) for key in PROPERTIES}
        report[patch]={'owning_ranks':[rank for rank,_ in rows],'max_relative_difference_from_serial':errors,
                       'properties':combined[patch]}
    return combined,{'ranks':ranks,'relative_tolerance':TOLERANCE,'inlets':report,'rank_csv_sha256':hashes,
                     'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest()}


def fixture(case,source,ranks,apply):
    if ranks!=4:raise ValueError('Fixture qualification uses four ranks')
    if case.exists():raise ValueError('Refusing existing fixture '+str(case))
    if not source.is_dir():raise ValueError('Missing fixture source')
    # Fixture must copy uniform pre-mapping state, never truncate nonuniform fields.
    for path in (source/'0').iterdir():
        if path.is_file() and not re.search(r'internalField\s+uniform',path.read_text()):
            raise ValueError('Fixture needs uniform source: '+str(path))
    print(json.dumps({'fixture':str(case),'source':str(source),'cells':112,'ranks':ranks,'apply':apply}))
    if not apply:return
    for name in ['0','constant','system']:shutil.copytree(source/name,case/name)
    mesh=case/'system/blockMeshDict'
    blocks=iter([4,6,4])
    text,count=re.subn(r'(hex\s*\([^)]*\)\s*)\(1000 1 \d+\)',
                      lambda m:m[1]+'(8 1 '+str(next(blocks))+')',mesh.read_text())
    if count!=3:raise ValueError('Unexpected fine mesh block layout')
    mesh.write_text(text)
    (case/'system/decomposeParDict').write_text('''FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }
numberOfSubdomains 4; method simple; simpleCoeffs { n (2 1 2); delta 0.001; }
''')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply','fixture-plan','fixture-apply'])
    parser.add_argument('case',type=Path);parser.add_argument('ranks',type=int)
    parser.add_argument('--reference',type=Path);parser.add_argument('--fixture-source',type=Path)
    args=parser.parse_args()
    if args.action.startswith('fixture-'):
        if args.fixture_source is None:parser.error('--fixture-source required')
        fixture(args.case,args.fixture_source,args.ranks,args.action=='fixture-apply');return
    if args.reference is None or args.ranks<1:parser.error('Positive ranks and --reference required')
    combined,report=collect(args.case,args.ranks,args.reference)
    if args.action=='apply':
        destination=args.case/'inlet-densities.csv'
        if destination.exists():raise ValueError('Refusing existing aggregate '+str(destination))
        with destination.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['patch',*PROPERTIES]);writer.writeheader()
            for patch,row in combined.items():writer.writerow({'patch':patch,**row})
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
