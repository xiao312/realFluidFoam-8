"""Generate actual DRM19 chemistry nodes for weighted-reader parity, not CFD tables."""
import argparse
import json
from pathlib import Path
import hashlib
import numpy as np
import cantera as ct


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mechanism',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--plan',action='store_true')
    a=p.parse_args()
    if a.plan:
        print('Plan: export cold/equilibrium/half-composition DRM19 nodes; reader parity only.');return
    a.out.mkdir(parents=True,exist_ok=False)
    gas=ct.Solution(str(a.mechanism))
    fuel={'CH4':.55,'N2':.45};air={'O2':1,'N2':3.76};pressure=101325.
    gas.TPX=298.,pressure,fuel;yf=gas.Y.copy();hf=gas.enthalpy_mass
    gas.TPX=298.,pressure,air;ya=gas.Y.copy();ha=gas.enthalpy_mass
    zst=1/(1+gas.stoich_air_fuel_ratio(fuel,air,basis='mole'))
    ref=gas.molecular_weights[gas.species_index('H2O')]
    names=['CO2','H2O','H2'];weights=np.array([ref/gas.molecular_weights[gas.species_index(s)] for s in names])
    indices=[gas.species_index(s) for s in names]
    gas.TP=298.15,pressure;h0=gas.partial_molar_enthalpies/gas.molecular_weights
    rows=[];bounds=[]
    for z in [0.,zst,1.]:
        y=z*yf+(1-z)*ya;h=z*hf+(1-z)*ha
        gas.HPY=h,pressure,y
        if z not in (0.,1.):gas.equilibrate('HP')
        burnt=gas.Y.copy();high=float(burnt[indices]@weights)
        bounds.append(high)
        for eta in [0.,.5,1.]:
            mix=(1-eta)*y+eta*burnt
            gas.HPY=h,pressure,mix
            omega=gas.net_production_rates*gas.molecular_weights
            rows.append({'Z':z,'C':eta*high,'Y':gas.Y.copy(),
                'Sc':float(omega[indices]@weights),'Q':float(-omega@h0),'Tdiag':gas.T})
    num=lambda x:' '.join(format(float(v),'.17g') for v in x)
    lines=['schema forge-fgm-table-v3','source physical-DRM19-reader-parity',
        'profile-sha256 '+hashlib.sha256(a.mechanism.read_bytes()).hexdigest(),
        'units-progress-source kg/m3/s','units-heat-release W/m3',
        'density-owner thermophysicalModel','temperature-owner thermophysicalModel','enthalpy-owner thermophysicalModel',
        'progress-coordinate weighted-mass-fraction-mapped','progress-species '+' '.join(names),
        'progress-weights '+num(weights),'species '+' '.join(gas.species_names),'nZ 3','nC 3',
        'z '+num([0,zst,1]),'c 0 0.5 1','c-min 0 0 0','c-max '+num(bounds)]
    blocks=[('Y '+s,[r['Y'][k] for r in rows]) for k,s in enumerate(gas.species_names)]
    blocks += [(name,[r[name] for r in rows]) for name in ['Sc','Q','Tdiag']]
    for name,values in blocks:
        lines += ['block '+name]+[num(values[i:i+3]) for i in range(0,9,3)]+['end']
    table='\n'.join(lines)+'\n'
    (a.out/'physical-v3.tbl').write_text(table)
    with (a.out/'expected.txt').open('w') as stream:
        stream.write(f'{gas.n_species} {len(rows)}\n')
        for r in rows:stream.write(num([r['Z'],r['C'],r['Sc'],r['Q'],r['Tdiag'],*r['Y']])+'\n')
    (a.out/'wrong-weights.tbl').write_text(table.replace('progress-weights '+num(weights),'progress-weights 1 1 1'))
    (a.out/'missing-weights.tbl').write_text(table.replace('progress-weights '+num(weights)+'\n',''))
    (a.out/'receipt.json').write_text(json.dumps({'schema':'weighted-reader-physical-nodes/v1',
        'scope':'Nine actual chemistry nodes; this is not a flamelet manifold or CFD validation',
        'cantera':ct.__version__,'Zst':zst,'weights':dict(zip(names,weights)),
        'mechanism_sha256':hashlib.sha256(a.mechanism.read_bytes()).hexdigest(),
        'nodes':9,'scientific_acceptance':False},indent=2)+'\n')


if __name__=='__main__':main()
