"""Adapt the versioned products-slab setup to the ideal runtime family."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PAPER=HERE.parent/'premixed-paper'


def prepare(action,key,output,mode):
    seeds=json.loads((HERE/'seeds.json').read_text())
    seed=seeds[key]
    thermo=HERE.parents[1]/'validation/inputs/thermo.inputData_GRI'
    if hashlib.sha256(thermo.read_bytes()).hexdigest()!=seed['NASA7_source_sha256']:
        raise ValueError('Seed and runtime thermo differ')
    if mode not in ('smoke','full') or output.exists():
        raise ValueError('Use smoke/full and a new output path')
    cfg={'key':key,'phi':seed['phi'],'mode':mode,'pressure_Pa':10132500,
         'Tu_K':298,'max_delta_t_s':5e-8,'end_time_s':1e-9 if mode=='smoke' else 2e-4,
         'seed_sha256':hashlib.sha256((HERE/'seeds.json').read_bytes()).hexdigest(),
         'status':'ideal-gas diagnostic baseline; scientific convergence unqualified'}
    print(json.dumps({'output':str(output.resolve()),'configuration':cfg},indent=2))
    if action=='plan':return
    # Reuse all versioned mesh, numerical and boundary settings. Then replace
    # every species and temperature together for the selected equivalence ratio.
    subprocess.run([sys.executable,'-B',str(PAPER/'prepare.py'),'apply',
        'phi110-equilibrium',str(output),mode],check=True)
    def write(name,text):
        (output/name).write_text(text,encoding='utf8')
    for name,old,new in [
        ('constant/thermophysicalProperties','SRKchungTakaMixture','idKineticMixture'),
        ('constant/thermophysicalProperties','chungTaka','sutherlandKinetic'),
        ('constant/thermophysicalProperties','rfJanaf','janaf'),
        ('constant/thermophysicalProperties','soaveRedlichKwong','perfectGas'),
        ('constant/thermophysicalProperties','rfSpecie','specie'),
        ('constant/chemistryProperties','SRKchungTakaStandard','idKineticStandard'),
        ('system/controlDict','maxDeltaT 1e-07','maxDeltaT 5e-08'),
        ('system/controlDict','rfPaperReactingFoam','rfSpatialReactingFoam')]:
        text=(output/name).read_text()
        if text.count(old)!=1:raise ValueError('Unexpected template: '+old)
        write(name,text.replace(old,new))
    n=8000
    hot=[abs((i+.5)*.004/n-.002)<.0001 for i in range(n)]
    if sum(hot)!=400 or hot!=hot[::-1]:raise ValueError('Slab symmetry/width')
    for name in list(seed['unburned']['mass_fractions'])+['T']:
        states=([seed[s]['temperature_K'] for s in ['unburned','burned']] if name=='T' else
                [seed[s]['mass_fractions'][name] for s in ['unburned','burned']])
        values=[states[int(flag)] for flag in hot]
        field='internalField nonuniform List<scalar>\n8000\n(\n'+'\n'.join(format(v,'.16g') for v in values)+'\n);'
        text,count=re.subn(r'internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\(.*?\)\s*;',
            field,(output/'0'/name).read_text(),flags=re.S)
        if count!=1:raise ValueError('Expected species/T field: '+name)
        write('0/'+name,text)
    pilot=json.loads((output/'pilot.json').read_text())
    pilot.update(phi=seed['phi'],mass_fractions={n:y for n,y in seed['unburned']['mass_fractions'].items() if y>0},
        kernel_temperature_K=seed['burned']['temperature_K'],thermo_family='idKinetic')
    write('pilot.json',json.dumps(pilot,indent=2)+'\n')
    write('paper-case.json',json.dumps(cfg,indent=2)+'\n')
    write('initialization-check.json',json.dumps({'recipe':'central ideal-gas HP products slab',
        'seed':seed,'symmetric':True,'products_cells':sum(hot),
        'seed_file_sha256':cfg['seed_sha256'],'species_sum_error':max(abs(sum(seed[s]['mass_fractions'].values())-1)
            for s in ['unburned','burned'])},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply']);p.add_argument('key')
    p.add_argument('output',type=Path);p.add_argument('mode',choices=['smoke','full'])
    a=p.parse_args();prepare(a.action,a.key,a.output,a.mode)
