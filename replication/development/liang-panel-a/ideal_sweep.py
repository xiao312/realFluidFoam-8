"""Fill the ideal reference curve with independently solved operating points."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def run(action,source,output):
    old=json.loads((source/'results.json').read_text())
    known={round(r['phi'],4) for r in old}
    phis=sorted({round(.92+.02*i,2) for i in range(27)} | {phi for phi in known if .92<=phi<=1.44})
    print(json.dumps({'new_phi':phis,'existing_phi':sorted(known),'pressure_Pa':10132500,
        'Tu_K':298,'output':str(output.resolve())}),flush=True)
    if output.exists():raise ValueError('Use a new output directory')
    if action=='plan':return
    import cantera as ct
    import numpy as np
    if ct.__version__!='3.2.0':raise ValueError('Use Cantera 3.2.0')
    output.mkdir(parents=True)
    results=[]
    for phi in phis:
        start=time.monotonic()
        nearest=min(old,key=lambda r:abs(r['phi']-phi))
        seed=source/f"phi{round(nearest['phi']*100):03d}.yaml"
        gas=ct.Solution(source.parent/'cantera/author-gri30.yaml')
        flame=ct.FreeFlame(gas,width=.004)
        flame.restore(seed,name='flame')
        flame.P=10132500;flame.inlet.T=298
        flame.inlet.X={'CH4':phi,'O2':2,'N2':2*79/21}
        flame.set_max_grid_points(flame.flame,6000)
        history=[]
        for slope,curve in [(.0075,.0125),(.00375,.00625)]:
            flame.set_refine_criteria(ratio=3,slope=slope,curve=curve,prune=0)
            flame.solve(loglevel=0,auto=False)
            history.append({'slope':slope,'curve':curve,'grid_points':len(flame.grid),
                            'speed_cm_s':float(flame.velocity[0]*100)})
        key=f'phi{round(phi*100):03d}'
        flame.save(output/(key+'.yaml'),name='flame')
        np.savetxt(output/(key+'.csv'),np.column_stack([flame.grid,flame.T,flame.velocity,
            flame.density,flame.heat_release_rate,flame.Y.T]),delimiter=',',comments='',
            header=','.join(['x_m','T_K','U_m_s','rho_kg_m3','Qdot_W_m3']+gas.species_names))
        row={'phi':phi,'pressure_Pa':float(flame.P),'Tu_K':float(flame.inlet.T),
            'speed_cm_s':float(flame.velocity[0]*100),'Tmax_K':float(max(flame.T)),
            'grid_points':len(flame.grid),'width_m':float(flame.grid[-1]-flame.grid[0]),
            'refinements':history,'last_refinement_relative_change':abs(history[-1]['speed_cm_s']/history[-2]['speed_cm_s']-1),
            'seed_phi':nearest['phi'],'seed_sha256':hashlib.sha256(seed.read_bytes()).hexdigest(),
            'transport':flame.transport_model,'flux_gradient_basis':flame.flux_gradient_basis,
            'soret':flame.soret_enabled,'wall_seconds':time.monotonic()-start}
        results.append(row)
        (output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps(row),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply']);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.action,a.source,a.output)
