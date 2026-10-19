"""Prepare explicit model inputs; the ideal profile is only a steady-solver guess."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply'])
    for name in ['mechanism','species','profile','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Output exists')
    import cantera as ct
    gas=ct.Solution(a.mechanism)
    text=a.species.read_text()
    rows=[]
    for name in gas.species_names:
        m=re.search(r'(?m)^'+re.escape(name)+r'\s*\{',text)
        if not m:raise ValueError('Missing species '+name)
        start=text.index('{',m.start());depth=0
        for end in range(start,len(text)):
            depth+=(text[end]=='{')-(text[end]=='}')
            if depth==0:break
        block=text[start:end+1]
        values=[]
        for key,scale in [('Tc',1),('Pc',1e6),('Vc',.001),('molWeight',1),('omega',1)]:
            match=re.search(r'\b'+key+r'\s+([-+\d.eE]+)\s*;',block)
            if not match:raise ValueError(name+'/'+key)
            values.append(float(match[1])*scale)
        rows.append([name,*values,int(name not in ['NO','NO2','N2O'])])
    manifest={'pressure_Pa':10132500,'Tu_K':298,'cases':[1,2,3,4,5],
        'alpha':'original Soave .48 + 1.574 omega - .176 omega^2; nonnegative sqrt(ai)',
        'kinetics':'physical concentrations, NASA reverse Kc',
        'initial_guess':'previously converged ideal FreeFlame; not a transient restart',
        'conductivity_mapping':'molar volume with methane reference molecular weight',
        'uncertainties':['Liang critical table unavailable','Tu inferred as 298 K','NOx scope taken as NO/NO2/N2O'],
        'inputs':{name:{'path':str(getattr(a,name).resolve()),'sha256':hashlib.sha256(getattr(a,name).read_bytes()).hexdigest()}
                  for name in ['mechanism','species','profile']}}
    print(json.dumps(manifest,indent=2))
    if a.action=='plan':return
    a.output.mkdir(parents=True)
    source=a.mechanism.read_text()
    if source.count('thermo: ideal-gas')!=1:raise ValueError('Expected one ideal phase')
    (a.output/'ideal.yaml').write_text(source)
    (a.output/'srk.yaml').write_text(source.replace('thermo: ideal-gas','thermo: liang-srk'))
    (a.output/'species.txt').write_text('\n'.join(' '.join(map(str,row)) for row in rows)+'\n')
    (a.output/'guess.csv').write_bytes(a.profile.read_bytes())
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
