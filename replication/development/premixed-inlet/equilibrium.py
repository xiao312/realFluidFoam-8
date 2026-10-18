"""Generate explicitly ideal-gas HP equilibrium seeds from pinned NASA7 data."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
THERMO = HERE.parents[1] / 'validation/inputs/thermo.inputData_GRI'


def generate(cfg):
    import cantera as ct
    import numpy as np
    assert ct.__version__ == '3.2.0', 'Use pinned Cantera 3.2.0'
    text = THERMO.read_text()
    names = re.search(r'species\s+53\s*\((.*?)\)\s*;', text, re.S)[1].split()
    assert len(names)==53
    reference = ct.Solution('gri30.yaml')
    species, weights = [], {}
    for name in names:
        block = re.search(r'(?m)^'+re.escape(name)+r'\s*\{(.*?)dataForRealGas', text, re.S)[1]
        value = lambda key: float(re.search(r'\b'+key+r'\s+([^;]+);', block)[1])
        coeff = lambda key: list(map(float,re.search(key+r'\s*\((.*?)\)',block,re.S)[1].split()))
        item = ct.Species(name, reference.species(name).composition)
        item.thermo = ct.NasaPoly2(value('Tlow'), value('Thigh'), 101325,
                                  [value('Tcommon')]+coeff('highCpCoeffs')+coeff('lowCpCoeffs'))
        species.append(item)
        weights[name] = value('molWeight')
    gas = ct.Solution(thermo='ideal-gas', species=species)
    gas.TPX = cfg['unburned_temperature_K'], cfg['pressure_Pa'], {'CH4':cfg['phi'],'O2':2,'N2':2*79/21}
    hu = gas.enthalpy_mass
    elements = np.array([gas.elemental_mass_fraction(i) for i in range(gas.n_elements)])
    def state():
        masses = {n:float(x)*weights[n] for n,x in zip(names,gas.X)}
        total = sum(masses.values())
        return {'temperature_K':float(gas.T),'mass_fractions':{n:v/total for n,v in masses.items()}}
    unburned = state()
    gas.equilibrate('HP', solver='auto', rtol=1e-11, max_steps=3000)
    element_error = float(np.max(np.abs(elements-[gas.elemental_mass_fraction(i) for i in range(gas.n_elements)])))
    energy_error = abs(gas.enthalpy_mass-hu)/max(1,abs(hu))
    assert element_error < 1e-9 and energy_error < 1e-8
    burned = state()
    assert abs(sum(burned['mass_fractions'].values())-1)<1e-12
    return {'phi':cfg['phi'],'pressure_Pa':cfg['pressure_Pa'],'unburned':unburned,'burned':burned,
            'method':'Cantera ideal-gas HP equilibrium; NOT real-fluid equilibrium',
            'cantera_version':ct.__version__,'NASA7_source_sha256':hashlib.sha256(THERMO.read_bytes()).hexdigest(),
            'element_definition_source':'Cantera 3.2.0 gri30.yaml',
            'composition_mapping':'equilibrium X converted using pinned OpenFOAM species molecular weights',
            'ideal_gas_element_mass_error':element_error,'ideal_gas_relative_enthalpy_error':energy_error,
            'qualification':'initialization seed only; real-fluid relaxation and seed-independence unqualified'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','apply'])
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    config=json.loads((HERE/'cases.json').read_text())
    if args.output.exists():raise ValueError('Output exists')
    print(json.dumps({'output':str(args.output),'cases':list(config),'method':'ideal-gas HP seed only'}))
    if args.action=='apply':
        seeds={key:generate(cfg) for key,cfg in config.items()}
        args.output.mkdir(parents=True)
        for key,seed in seeds.items():(args.output/(key+'.json')).write_text(json.dumps(seed,indent=2)+'\n')
