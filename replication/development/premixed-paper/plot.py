"""Plot a reviewed in-situ CSV without smoothing or silently filling invalid rows."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

STAGES={"integrated_species_solve":"Source used in OH solve",
        "instantaneous_end_step":"Instantaneous end-step source"}
COLORS={1e-5:"#b66118",2e-5:"#1767a0",3e-5:"#505050"}


def load(path):
    with path.open(newline="") as stream: rows=list(csv.DictReader(stream))
    if not rows: raise ValueError("Empty history")
    for row in rows:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Incomplete CSV row; collect a complete snapshot")
    return rows


def series(rows,stage,side,level,field,scale=1.):
    selected=sorted((r for r in rows if r["stage"]==stage and r["side"]==side
                     and float(r["OH_level"])==level),key=lambda r:float(r["time_s"]))
    times=np.array([float(r["time_s"])*1e6 for r in selected])
    values=np.array([float(r[field])*scale if r["status"]=="valid" else np.nan for r in selected])
    return times,values


def plot(csv_path,output,job):
    rows=load(csv_path);output.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({"font.family":"serif","font.size":9,"axes.linewidth":.7,
                         "lines.linewidth":1.1,"savefig.dpi":220})
    fig,axes=plt.subplots(1,2,figsize=(9,4.2))
    for ax,(stage,title) in zip(axes,STAGES.items()):
        for level,color in COLORS.items():
            for side,style in [("left","-"),("right","--")]:
                t,speed=series(rows,stage,side,level,"speed_m_s",100.)
                ax.plot(t,speed,color=color,ls=style,label=f"{side}, OH={level:.0e}")
        ax.set(title=title,xlabel="Time (µs)",ylabel="Density-weighted displacement speed (cm/s)")
        ax.set_yscale("symlog",linthresh=10)
        ax.axhline(0,color="0.65",lw=.6)
        ax.axhline(6.8,color="black",ls=":",lw=.8,label="Nguyen ≈6.8 cm/s (digitized)")
        ax.grid(alpha=.15)
        if not any(r["status"]=="valid" and r["stage"]==stage for r in rows):
            ax.text(.5,.5,"No valid OH contour yet",ha="center",transform=ax.transAxes)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=4,frameon=False,fontsize=8,bbox_to_anchor=(.5,.015))
    fig.suptitle(f"Central ignition: φ=1.10, 100 atm, 298 K — job {job}",fontsize=11)
    fig.text(.5,.90,"Full recorded history; symmetric-log speed axis (linear within ±10 cm/s). Ignition transient; convergence unqualified.",ha="center",fontsize=8)
    fig.subplots_adjust(top=.82,bottom=.29,wspace=.3)
    for ext in ["png","pdf","svg"]:fig.savefig(output/("flame-speed-history."+ext))
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(9,3.8))
    for ax,(stage,title) in zip(axes,STAGES.items()):
        for side,style in [("left","-"),("right","--")]:
            for field,color,label in [("chemistry_m_s","#b66118","chemistry"),("diffusion_m_s","#1767a0","diffusion"),("speed_m_s","#303030","sum")]:
                t,y=series(rows,stage,side,2e-5,field,100.)
                ax.plot(t,y,color=color,ls=style,label=f"{side}: {label}")
        ax.set(title=title,xlabel="Time (µs)",ylabel="Contribution at OH=2e-5 (cm/s)")
        ax.set_yscale("symlog",linthresh=10);ax.axhline(0,color=".65",lw=.6);ax.grid(alpha=.15)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=3,frameon=False,fontsize=8)
    fig.suptitle(f"Eq. (40) signed chemistry and diffusion contributions — job {job}",fontsize=11)
    fig.subplots_adjust(top=.82,bottom=.26,wspace=.3)
    fig.savefig(output/"flame-speed-terms.png");plt.close(fig)
    receipt={"job":job,"source_csv":str(csv_path),"sha256":hashlib.sha256(csv_path.read_bytes()).hexdigest(),
             "rows":len(rows),"valid_rows":sum(r["status"]=="valid" for r in rows),
             "time_range_s":[min(float(r["time_s"]) for r in rows),max(float(r["time_s"]) for r in rows)],
             "status":"in-situ diagnostic history; convergence unqualified"}
    (output/"provenance.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("csv",type=Path);p.add_argument("output",type=Path);p.add_argument("--job",required=True)
    a=p.parse_args();plot(a.csv,a.output,a.job)
