"""Validate pinned seed data and construct symmetric central products fields."""
import hashlib
import json
import math
from pathlib import Path
import re

MODULE=Path(__file__).resolve().parent


def seed_for(cfg):
    path=MODULE/'equilibrium-seed.json'
    seed=json.loads(path.read_text())
    provenance=json.loads((MODULE/'equilibrium-seed-provenance.json').read_text())
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=provenance['sha256']: raise ValueError('Seed hash differs from pinned input')
    thermo=MODULE.parents[1]/'validation/inputs/thermo.inputData_GRI'
    if hashlib.sha256(thermo.read_bytes()).hexdigest()!=seed['NASA7_source_sha256']:
        raise ValueError('Seed NASA7 input does not match runtime input')
    names=re.search(r'species\s+53\s*\((.*?)\)\s*;',thermo.read_text(),re.S)[1].split()
    if seed['phi']!=cfg['phi'] or seed['pressure_Pa']!=cfg['pressure_Pa']:
        raise ValueError('Seed operating condition differs')
    if seed['unburned']['temperature_K']!=cfg['unburned_temperature_K']:
        raise ValueError('Seed fresh temperature differs')
    for state in ['unburned','burned']:
        data=seed[state]; y=data['mass_fractions']
        if set(y)!=set(names) or not all(math.isfinite(v) and 0<=v<=1 for v in y.values()):
            raise ValueError('Invalid seed species')
        if abs(sum(y.values())-1)>1e-12 or not 200<data['temperature_K']<3000:
            raise ValueError('Invalid seed normalization or temperature')
    return seed,digest


def scalar_field(template,values,name):
    header=re.sub(r'\bobject\s+[^;]+;', 'object '+name+';',template)
    field='internalField nonuniform List<scalar>\n'+str(len(values))+'\n(\n'+'\n'.join(format(v,'.16g') for v in values)+'\n);'
    text,count=re.subn(r'internalField\s+uniform\s+[^;]+;',field,header)
    if count!=1:raise ValueError('Expected one uniform template field')
    return text


def products_fields(case,cfg):
    seed,digest=seed_for(cfg)
    pilot=json.loads((case/'pilot.json').read_text())
    for name,y in pilot['mass_fractions'].items():
        if abs(y-seed['unburned']['mass_fractions'][name])>1e-12:
            raise ValueError('Generated fresh composition differs from seed')
    n=cfg['cells'];L=cfg['length_m'];width=cfg['kernel_width_m']
    hot=[abs((i+.5)*L/n-L/2)<width/2 for i in range(n)]
    if hot!=hot[::-1] or sum(hot)!=round(width*n/L):
        raise ValueError('Products slab not symmetric or wrong cell count')
    temperatures=[seed['burned' if flag else 'unburned']['temperature_K'] for flag in hot]
    template=(case/'0/Ydefault').read_text()
    sums=[0.]*n
    for name in seed['burned']['mass_fractions']:
        y=[seed['burned' if flag else 'unburned']['mass_fractions'][name] for flag in hot]
        (case/'0'/name).write_text(scalar_field(template,y,name),encoding='utf8')
        sums=[a+b for a,b in zip(sums,y)]
    error=max(abs(s-1) for s in sums)
    if error>1e-12:raise ValueError('Generated composition not normalized')
    return temperatures,{'recipe':'central ideal-gas HP products slab','seed_sha256':digest,
        'products_cells':sum(hot),'fresh_cells':n-sum(hot),'symmetric':True,
        'species_sum_error':error,'temperature_min_K':min(temperatures),
        'temperature_max_K':max(temperatures),'interface':'abrupt',
        'qualification':'seed only; real-fluid equilibrium and energy consistency unqualified'}
