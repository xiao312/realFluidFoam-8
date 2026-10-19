"""Read completed qualification outputs. No writes or automatic scientific acceptance."""
import argparse
import csv
import json
import math
from pathlib import Path


def rows(path):
    with path.open(newline='',encoding='utf8') as f:
        return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path)
    p.add_argument('--ideal-reference-cm-s',type=float)
    a=p.parse_args()
    history=rows(a.output/'refinement.csv');profile=rows(a.output/'profile.csv')
    if len(history)<2 or len(profile)<10:raise ValueError('Incomplete solve')
    for r in history+profile:
        if not all(math.isfinite(v) for v in r.values()):raise ValueError('Nonfinite result')
    speed=history[-1]['speed_cm_s'];change=abs(speed/history[-2]['speed_cm_s']-1)
    flux=[r['rho_kg_m3']*r['U_m_s'] for r in profile]
    imbalance=(max(flux)-min(flux))/abs(flux[0])
    species_error=max(abs(sum(v for k,v in r.items() if k.startswith('Y_'))-1) for r in profile)
    result={'stage':int(history[-1]['stage']),'phi':history[-1]['phi'],'speed_cm_s':speed,
        'last_refinement_relative_change':change,'mass_flux_relative_range':imbalance,
        'maximum_species_sum_error':species_error,'points':len(profile),
        'scientific_acceptance':False,'remaining':['domain sensitivity','initial-guess sensitivity','publication parameter uncertainty']}
    if a.ideal_reference_cm_s is not None:
        result['ideal_parity_relative_error']=abs(speed/a.ideal_reference_cm_s-1)
        if result['ideal_parity_relative_error']>.001:raise ValueError(result)
    if speed<=0 or change>.003 or imbalance>1e-3 or species_error>1e-7:raise ValueError(result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
