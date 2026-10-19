"""Supplemental premixed profiles and time histories; no paper spatial reference exists."""
import numpy as np
from common import read_json
from flame_speed import track, estimate


def render(config, inputs, output):
    import matplotlib.pyplot as plt
    cfg=config["premixed"]
    data=read_json(inputs.file(cfg["snapshot"]))
    level=cfg.get("primary_OH_level",5e-5)
    window=min(cfg["windows_s"])
    jobs=sorted(data["jobs"],key=lambda j:j["metadata"]["config"]["phi"])
    colors=plt.cm.viridis(np.linspace(.05,.9,len(jobs)))
    fig,axes=plt.subplots(2,2,figsize=(8.4,5.4),layout="constrained")
    aligned,aa=plt.subplots(1,2,figsize=(8.4,3.6),layout="constrained")
    history,ha=plt.subplots(1,2,figsize=(8.4,3.6),layout="constrained")
    for job,color in zip(jobs,colors):
        spec=job["metadata"]["config"];sample=job["samples"][-1];fields=sample["fields"]
        x=(np.arange(spec["cells"])+.5)*spec["length_m"]/spec["cells"]
        label=f"phi={spec['phi']:.2f}"
        for ax,name,unit in zip(axes.flat,["T","rho","U","OH"],["T [K]","Density [kg/m3]","Velocity [m/s]","OH mass fraction"]):
            ax.plot(x*1000,fields[name],color=color,label=label,lw=.9)
            ax.set(xlabel="x [mm]",ylabel=unit)
        end=sample["time_s"]
        tail=dict(job,samples=[s for s in job["samples"] if s["time_s"]>=end-max(cfg["windows_s"])-1e-12])
        try: rows=track(tail,level)
        except ValueError: continue
        for ax,name,unit in zip(aa,["T","OH"],["T [K]","OH mass fraction"]):
            ax.plot((x-rows[-1,1])*1e6,fields[name],color=color,label=label,lw=.9)
            ax.set(xlabel="x - final OH front [micrometres]",ylabel=unit,xlim=(-100,250))
        estimates=[]
        for stop in range(3,len(rows)+1):
            try: estimates.append(estimate(rows[:stop],job["runtime"]["unburned_density_kg_m3"],window))
            except ValueError: continue
        for ax,name,title in zip(ha,["OH_speed_cm_s","temperature_speed_cm_s"],["OH displacement","Temperature-front displacement"]):
            ax.plot([r["end_s"]*1000 for r in estimates],[r[name] for r in estimates],color=color,label=label,lw=.9,marker="o",ms=2)
            ax.set(xlabel="Fit end time [ms]",ylabel="Speed [cm/s]",title=title)
    for ax in [axes[0,0],aa[0],ha[0]]:
        ax.legend(ncol=2,fontsize=6.8,frameon=False)
    fig.suptitle("Completed Liang-inlet sweep: spatial fields at 1 ms",fontsize=11)
    aligned.suptitle(f"Profiles relative to OH={level:g}; diagnostic alignment only",fontsize=11)
    history.suptitle(f"Final {window*1e6:g}-microsecond fits; convergence unproved",fontsize=11)
    for figure,name in [(fig,"premixed-spatial"),(aligned,"premixed-front-relative"),(history,"premixed-speed-history")]:
        for ax in figure.axes:
            ax.tick_params(labelsize=8)
            ax.xaxis.label.set_size(9);ax.yaxis.label.set_size(9);ax.title.set_size(10)
        for suffix in ("png","svg"):figure.savefig(output/"standalone"/(name+"."+suffix),dpi=240)
        plt.close(figure)
