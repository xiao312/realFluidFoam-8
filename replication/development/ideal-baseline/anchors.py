"""Export actual saved Cantera temperature anchors for CFD front tracking."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply'])
    parser.add_argument('profiles', type=Path)
    parser.add_argument('mechanism', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    records = json.loads((args.profiles/'results.json').read_text())
    if args.output.exists():
        raise ValueError('Use a new output file')
    print(json.dumps({'action':args.action,'conditions':len(records),'output':str(args.output)}))
    if args.action == 'plan':
        return
    import cantera as ct
    import numpy as np
    if ct.__version__ != '3.2.0':
        raise ValueError('Use the pinned Cantera 3.2.0 environment')
    output = []
    for row in sorted(records,key=lambda r:r['phi']):
        source = args.profiles/f"phi{round(row['phi']*100):03d}.yaml"
        flame = ct.FreeFlame(ct.Solution(args.mechanism),width=.004)
        flame.restore(source,name='flame')
        anchor = flame.fixed_temperature_location
        rho = float(np.interp(anchor,flame.grid,flame.density))
        velocity = float(np.interp(anchor,flame.grid,flame.velocity))
        speed = rho*velocity/flame.density[0]
        error = abs(speed/flame.velocity[0]-1)
        if error > 1e-5:
            raise ValueError('Anchor mass flux differs from inlet; inspect restored solution')
        Tu, Tb = float(flame.T[0]), float(flame.T[-1])
        output.append({'phi':row['phi'],'temperature_anchor_K':flame.fixed_temperature,
            'cantera_anchor_location_m':anchor,'Tu_K':Tu,'Tb_K':Tb,
            'sensitivity_temperatures_K':[Tu+c*(Tb-Tu) for c in [.2,.5,.8]],
            'speed_cm_s':float(flame.velocity[0]*100),
            'anchor_mass_flux_speed_cm_s':float(speed*100),
            'anchor_mass_flux_relative_error':float(error),
            'profile_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'cantera_version':ct.__version__,
        'mechanism_sha256':hashlib.sha256(args.mechanism.read_bytes()).hexdigest(),
        'definition':'Track fixed temperature, not the Cantera coordinate. Additional temperatures are fixed from this reference, never rescaled by instantaneous CFD Tmax.',
        'conditions':output},indent=2)+'\n')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
