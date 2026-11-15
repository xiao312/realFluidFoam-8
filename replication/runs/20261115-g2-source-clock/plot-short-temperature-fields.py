from pathlib import Path
import argparse,json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
parser=argparse.ArgumentParser();parser.add_argument("--root",type=Path,required=True);args=parser.parse_args();root=args.root.resolve();entries=json.loads((root/"collection.json").read_text(encoding="utf8"))["entries"]
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.labelsize":11,"axes.titlesize":11})
norm=plt.Normalize(80,3600)
def draw(ax,e):
 d=np.load(root/(e["condition"]+"-"+e["mode"]+".npz"),allow_pickle=True)
 coll=PolyCollection(list(d["polygons_mm"]),array=d["T_K"],cmap="inferno",norm=norm,edgecolors="none",rasterized=True);ax.add_collection(coll)
 ax.set(xlim=(0,20),ylim=(0,6),xlabel="Axial position x (mm)",ylabel="Radius r (mm)");ax.set_aspect("equal");ax.set_facecolor("#ededed")
 mode="Cr = 100" if e["mode"]=="steps" else "fixed τ = 10 µs";state="CALORIC FAILURE" if e["failedCaloricClosure"] else "completed startup"
 ax.set_title(f"{e['condition'].capitalize()} | {mode} | t = {1e3*e['time_s']:.3f} ms\nTmax = {e['Tmax_K']:.0f} K | {state}",color="#a83228" if e["failedCaloricClosure"] else "#222222")
 return coll
fig,axes=plt.subplots(2,2,figsize=(12,7),layout="constrained")
for ax,e in zip(axes.flat,entries):coll=draw(ax,e)
fig.colorbar(coll,ax=list(axes.flat),label="Temperature (K)",shrink=.78,pad=.025)
fig.suptitle("G2 source-clock controls: actual finite-volume temperature fields",fontsize=14)
fig.supxlabel("Cavalieri times differ; its right panel is a raw failed state. No developed means or scientific acceptance.",fontsize=10)
fig.savefig(root/"g2-source-clock-short-controls.png",dpi=180);plt.close(fig)
for condition in ["schmitt","cavalieri"]:
 fig,axes=plt.subplots(2,1,figsize=(11,7),layout="constrained")
 for ax,e in zip(axes,[e for e in entries if e["condition"]==condition]):coll=draw(ax,e)
 fig.colorbar(coll,ax=list(axes),label="Temperature (K)",shrink=.83,pad=.025)
 fig.supxlabel("Original-zero cases; piecewise-constant cell values, no smoothing. Startup diagnostics."+(" Unequal times; faster-source state failed caloric closure." if condition=="cavalieri" else " Same-time comparison."),fontsize=9)
 fig.savefig(root/(condition+"-source-clock-short-controls.png"),dpi=180);plt.close(fig)
print(root/"g2-source-clock-short-controls.png")
