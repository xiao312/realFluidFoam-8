"""Save accepted-state checkpoints and bound integration without changing its RHS."""
import csv
from pathlib import Path
import time
import numpy as np


class Checkpoints:
    def __init__(self,out,grid,settings,species_count):
        self.out=Path(out); self.grid=grid; self.settings=settings
        self.species_count=species_count
        self.started=time.monotonic(); self.last_write=self.started
        self.stopped_by_wall=False; self.count=0
        self.log=(self.out/'accepted-steps.csv').open('w',newline='')
        self.writer=csv.writer(self.log)
        self.writer.writerow(['step','physical_time_s','wall_s','temperature_min_K','temperature_max_K','scaled_step_residual'])

    def __call__(self,t,state,residual,steps):
        now=time.monotonic(); wall=now-self.started
        self.count=int(steps)
        self.writer.writerow([steps,t,wall,float(np.min(state[::self.species_count])),float(np.max(state[::self.species_count])),float(residual)])
        self.stopped_by_wall=wall>=self.settings['integration_wall_limit_s']
        if steps%self.settings['checkpoint_steps']==0 or now-self.last_write>=self.settings['checkpoint_wall_s'] or self.stopped_by_wall:
            temporary=self.out/'checkpoint.tmp.npz'
            np.savez_compressed(temporary,physical_time_s=t,interior_state=state,Z=self.grid,accepted_steps=steps,wall_s=wall)
            temporary.replace(self.out/'checkpoint.npz')
            self.log.flush(); self.last_write=now
        return self.stopped_by_wall

    def close(self):
        self.log.close()


def select_frames(times,fractions,species,grid,zst):
    """Time and both progress coordinates retain rapid chemistry missed by one sum."""
    selected={0,len(times)-1}
    if times[-1]>0:
        positive=times[times>0]
        queries=np.unique(np.r_[np.linspace(0,times[-1],21),np.geomspace(positive[0],times[-1],21)])
        selected.update(int(np.argmin(abs(times-value))) for value in queries)
    for names in [('CO2','CO'),('CO2','CO','H2O')]:
        values=fractions[:,:,[species.index(n) for n in names]].sum(axis=2)
        central=np.array([np.interp(zst,grid,row) for row in values])
        selected.update(int(np.argmin(abs(central-value))) for value in np.linspace(float(central.min()),float(central.max()),20))
    return sorted(selected)
