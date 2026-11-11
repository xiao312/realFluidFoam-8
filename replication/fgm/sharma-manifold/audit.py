"""Independent final-profile element and enthalpy diagnostics, without acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import cantera as ct
import numpy as np


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--mechanism',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--plan',action='store_true')
    args=parser.parse_args()
    receipt=json.loads((args.run/'receipt.json').read_text())
    if args.plan:
        print(json.dumps({'input':str(args.run),'output':str(args.out),'branches':receipt['branches']},indent=2));return
    if args.out.exists():raise ValueError('Refusing existing audit output')
    gas=ct.Solution(str(args.mechanism));config=receipt['config']
    gas.TPX=config['oxidizer_K'],config['pressure_Pa'],'O2:1'
    ho=gas.enthalpy_mass;oxygen=gas.elemental_mass_fraction('O')
    gas.TPX=config['fuel_K'],config['pressure_Pa'],'CH4:1'
    hf=gas.enthalpy_mass;carbon=gas.elemental_mass_fraction('C')
    results={}
    for branch in receipt['branches']:
        if branch['status']=='failed':continue
        name=f"chi-{int(branch['chi_st'])}.npz";path=args.run/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==receipt['files'][name]
        raw=np.load(path);enthalpy=[];ce=[];oe=[]
        for temperature,mass in zip(raw['T'][-1],raw['Y'][-1]):
            gas.TPY=temperature,config['pressure_Pa'],mass
            enthalpy.append(gas.enthalpy_mass)
            ce.append(gas.elemental_mass_fraction('C'));oe.append(gas.elemental_mass_fraction('O'))
        z=raw['Z'];defect=np.array(enthalpy)-((1-z)*ho+z*hf)
        results[name]={'input_sha256':receipt['files'][name],
            'max_enthalpy_defect_J_kg':float(abs(defect).max()),
            'max_carbon_mass_fraction_defect':float(abs(np.array(ce)-z*carbon).max()),
            'max_oxygen_mass_fraction_defect':float(abs(np.array(oe)-(1-z)*oxygen).max())}
    output={'cantera':ct.__version__,'mechanism_sha256':hashlib.sha256(args.mechanism.read_bytes()).hexdigest(),
        'diagnostics':results,'scientific_acceptance':False,
        'limitation':'Independent Cantera NASA evaluation; Spitfire cold Cp differs. TPY normalizes/clips signed trace values. This is not strict discrete conservation or thermo qualification.'}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
