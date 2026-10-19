"""Construct a different steady-flame guess from independently calculated HP products."""
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply'])
    for name in ['base','equilibrium','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Output exists')
    import cantera as ct
    gas=ct.Solution(a.base/'ideal.yaml')
    with a.equilibrium.open(newline='',encoding='utf8') as f:burn=next(csv.DictReader(f))
    with (a.base/'guess.csv').open(newline='',encoding='utf8') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    Tb=float(burn['T_K']);Tu=float(rows[0]['T_K']);oldTb=float(rows[-1]['T_K'])
    if not Tb>Tu or not oldTb>Tu:raise ValueError('Invalid temperature span')
    gas.TPX=Tb,10132500,{n:float(burn['X_'+n]) for n in gas.species_names}
    yb=dict(zip(gas.species_names,map(float,gas.Y)))
    yu={n:float(rows[0][n]) for n in gas.species_names}
    manifest={'description':'HP-products ramp initial guess; no solved flame profile is reused as the target solution',
        'equilibrium_sha256':hashlib.sha256(a.equilibrium.read_bytes()).hexdigest(),
        'base_profile_sha256':hashlib.sha256((a.base/'guess.csv').read_bytes()).hexdigest(),
        'Tu_K':Tu,'Tb_K':Tb,'pressure_Pa':10132500,
        'composition':'linear mass-fraction interpolation from fresh gas to supplied HP products',
        'velocity':'existing ideal-profile numerical guess','rho':'ideal-gas guess only; solver recalculates SRK',
        'Qdot':'zero placeholder; not a heat-release result'}
    print(json.dumps(manifest,indent=2))
    if a.action=='plan':return
    shutil.copytree(a.base,a.output)
    for row in rows:
        progress=max(0.,min(1.,(float(row['T_K'])-Tu)/(oldTb-Tu)))
        T=Tu+progress*(Tb-Tu);Y={n:(1-progress)*yu[n]+progress*yb[n] for n in gas.species_names}
        gas.TPY=T,10132500,Y
        row.update(T_K=T,rho_kg_m3=gas.density,Qdot_W_m3=0,**Y)
    with (a.output/'guess.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    (a.output/'equilibrium-guess.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
