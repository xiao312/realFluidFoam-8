"""Solve an independent ideal steady flame to seed a declared pressure control."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['plan', 'apply'])
    p.add_argument('inputs', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--atm', type=float, required=True)
    p.add_argument('--phi', type=float, default=1.1)
    p.add_argument('--width', type=float, default=.03)
    a = p.parse_args()
    if a.output.exists() or not 1 <= a.atm <= 100 or not .5 <= a.phi <= 2 or a.width <= 0:
        raise ValueError('Use a new output, 1--100 atm, phi 0.5--2 and positive width')
    manifest = dict(pressure_Pa=a.atm*101325, phi=a.phi, Tu_K=298,
                    initial_width_m=a.width, initial_guess='independent ideal steady FreeFlame',
                    inputs={name: hashlib.sha256((a.inputs/name).read_bytes()).hexdigest()
                            for name in ['ideal.yaml', 'srk.yaml', 'species.txt']})
    print(json.dumps(manifest, indent=2), flush=True)
    if a.action == 'plan':
        return
    import cantera as ct
    import numpy as np
    if ct.__version__ != '3.2.0':
        raise ValueError('Pinned Cantera 3.2.0 required')
    a.output.mkdir(parents=True)
    for name in manifest['inputs']:
        shutil.copyfile(a.inputs/name, a.output/name)
    gas = ct.Solution(str(a.inputs/'ideal.yaml'))
    gas.TP = 298, a.atm*101325
    gas.set_equivalence_ratio(a.phi, 'CH4', 'O2:0.21,N2:0.79')
    flame = ct.FreeFlame(gas, width=a.width)
    flame.transport_model = 'mixture-averaged'
    flame.flux_gradient_basis = 'molar'
    flame.soret_enabled = False
    rows = []
    for index, (slope, curve) in enumerate([(.06, .1), (.015, .025)]):
        flame.set_refine_criteria(ratio=3, slope=slope, curve=curve, prune=0)
        flame.solve(loglevel=0, auto=index == 0)
        rows.append(dict(slope=slope, curve=curve, points=len(flame.grid),
                         speed_cm_s=float(100*flame.velocity[0])))
        print(json.dumps(rows[-1]), flush=True)
    np.savetxt(a.output/'guess.csv', np.column_stack([
        flame.grid, flame.T, flame.velocity, flame.density, flame.heat_release_rate, flame.Y.T]),
        delimiter=',', comments='',
        header=','.join(['x_m', 'T_K', 'U_m_s', 'rho_kg_m3', 'Qdot_W_m3']+gas.species_names))
    flame.save(a.output/'ideal-flame.yaml', name='flame')
    manifest.update(cantera_version=ct.__version__, refinements=rows,
                    final_width_m=float(flame.grid[-1]-flame.grid[0]))
    (a.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
