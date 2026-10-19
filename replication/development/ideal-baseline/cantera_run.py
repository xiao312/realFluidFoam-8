"""Independent adiabatic ideal-gas FreeFlame sweep and HP initialization seeds."""
import argparse
import json
from pathlib import Path
import time
from mechanism import build

PHIS = [1.1, 1.0, 1.2, .9, .95, 1.05, 1.15, 1.25, 1.3, 1.35, 1.4]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan','apply'])
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps({'output':str(args.output.resolve()),'phi':PHIS,'pressure_Pa':10132500,
        'Tu_K':298,'transport':'mixture-averaged, molar gradients, Soret off'}), flush=True)
    if args.output.exists():
        raise ValueError('Output exists; use a new run directory')
    if args.action == 'plan':
        return
    import cantera as ct
    import numpy as np
    args.output.mkdir(parents=True)
    gas, weights, provenance = build()
    (args.output/'mechanism.json').write_text(json.dumps(provenance,indent=2)+'\n')
    gas.write_yaml(args.output/'author-gri30.yaml')
    # Seeds are independent equilibrium calculations, not flame results.
    seeds = {}
    for phi in PHIS:
        gas.TPX = 298,10132500,{'CH4':phi,'O2':2,'N2':2*79/21}
        hu = gas.enthalpy_mass
        def state():
            m = {n:float(x)*weights[n] for n,x in zip(gas.species_names,gas.X)}
            return {'temperature_K':float(gas.T),'mass_fractions':{n:v/sum(m.values()) for n,v in m.items()}}
        fresh = state()
        gas.equilibrate('HP',rtol=1e-11,max_steps=3000)
        seed = {'phi':phi,'pressure_Pa':10132500,'unburned':fresh,'burned':state(),
            'enthalpy_relative_error':abs(gas.enthalpy_mass-hu)/max(1,abs(hu)),
            'NASA7_source_sha256':provenance['inputs']['thermo.inputData_GRI']}
        if seed['enthalpy_relative_error']>1e-8:
            raise ValueError('HP energy check failed')
        seeds[f'phi{round(phi*100):03d}'] = seed
    (args.output/'seeds.json').write_text(json.dumps(seeds,indent=2)+'\n')
    results = []
    for phi in PHIS:
        started = time.monotonic()
        gas.TPX = 298,10132500,{'CH4':phi,'O2':2,'N2':2*79/21}
        flame = ct.FreeFlame(gas,width=.004)
        flame.transport_model = 'mixture-averaged'
        flame.flux_gradient_basis = 'molar'
        flame.soret_enabled = False
        flame.set_max_grid_points(flame.flame,2500)
        refinements = []
        for level,(slope,curve) in enumerate([(.12,.18),(.06,.10),(.03,.05)]):
            flame.set_refine_criteria(ratio=3,slope=slope,curve=curve,prune=0)
            flame.solve(loglevel=0,auto=level==0)
            refinements.append({'slope':slope,'curve':curve,'points':len(flame.grid),
                'speed_cm_s':float(flame.velocity[0]*100),'width_m':float(flame.grid[-1]-flame.grid[0])})
            print(json.dumps({'phi':phi,'refinement':refinements[-1]}),flush=True)
        key=f'phi{round(phi*100):03d}'
        flame.save(args.output/(key+'.yaml'),name='flame')
        fields = np.column_stack([flame.grid,flame.T,flame.velocity,flame.density,flame.heat_release_rate,flame.Y.T])
        np.savetxt(args.output/(key+'.csv'),fields,delimiter=',',comments='',
            header=','.join(['x_m','T_K','U_m_s','rho_kg_m3','Qdot_W_m3']+gas.species_names))
        result={'phi':phi,'Tu_K':298,'pressure_Pa':10132500,'speed_cm_s':float(flame.velocity[0]*100),
            'Tmax_K':float(max(flame.T)),'refinements':refinements,
            'last_refinement_relative_change':abs(refinements[-1]['speed_cm_s']/refinements[-2]['speed_cm_s']-1),
            'wall_seconds':time.monotonic()-started}
        results.append(result)
        (args.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
