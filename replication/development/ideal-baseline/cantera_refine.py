"""Refine existing independently solved flames into a new output directory."""
import argparse
import json
from pathlib import Path
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','apply']);p.add_argument('input',type=Path)
    p.add_argument('output',type=Path);a=p.parse_args()
    results=json.loads((a.input/'results.json').read_text())
    print(json.dumps({'input':str(a.input),'output':str(a.output),'phi':[r['phi'] for r in results]}),flush=True)
    if a.output.exists():raise ValueError('Output exists')
    if a.action=='plan':return
    import cantera as ct
    import numpy as np
    if ct.__version__!='3.2.0':raise ValueError('Use Cantera 3.2.0')
    a.output.mkdir(parents=True)
    complete=[]
    for result in results:
        start=time.monotonic();key=f"phi{round(result['phi']*100):03d}"
        gas=ct.Solution(a.input/'author-gri30.yaml')
        flame=ct.FreeFlame(gas,width=.004)
        flame.restore(a.input/(key+'.yaml'),name='flame')
        flame.set_max_grid_points(flame.flame,5000)
        for slope,curve in [(.015,.025),(.0075,.0125)]:
            flame.set_refine_criteria(ratio=3,slope=slope,curve=curve,prune=0)
            flame.solve(loglevel=0,auto=False)
            result['refinements'].append({'slope':slope,'curve':curve,'points':len(flame.grid),
                'speed_cm_s':float(flame.velocity[0]*100),'width_m':float(flame.grid[-1]-flame.grid[0])})
        result.update(speed_cm_s=float(flame.velocity[0]*100),Tmax_K=float(max(flame.T)),
            last_refinement_relative_change=abs(result['refinements'][-1]['speed_cm_s']/result['refinements'][-2]['speed_cm_s']-1),
            refinement_wall_seconds=time.monotonic()-start)
        flame.save(a.output/(key+'.yaml'),name='flame')
        np.savetxt(a.output/(key+'.csv'),np.column_stack([flame.grid,flame.T,flame.velocity,
            flame.density,flame.heat_release_rate,flame.Y.T]),delimiter=',',comments='',
            header=','.join(['x_m','T_K','U_m_s','rho_kg_m3','Qdot_W_m3']+gas.species_names))
        complete.append(result)
        (a.output/'results.json').write_text(json.dumps(complete,indent=2)+'\n')
        print(json.dumps(result),flush=True)


if __name__=='__main__':main()
