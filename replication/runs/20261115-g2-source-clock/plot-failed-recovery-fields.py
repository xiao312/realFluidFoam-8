from pathlib import Path
import json,sys,numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
r=Path(sys.argv[1]);q=json.loads((r/"collection.json").read_text());fig,axes=plt.subplots(1,2,figsize=(11,3.5),layout="constrained");norm=plt.Normalize(80,3600)
for ax,e in zip(axes,q["entries"]):
 d=np.load(r/(e["mode"]+".npz"),allow_pickle=True);col=PolyCollection(list(d["polygons_mm"]),array=d["T_K"],cmap="inferno",norm=norm,linewidth=0);ax.add_collection(col);label="Gibbs root policy only" if e["mode"]=="gibbs" else "Gibbs + density/Ha predictor"
 ax.set(xlim=(0,20),ylim=(0,6),xlabel="Axial distance [mm]",ylabel="Radius [mm]",title=label+"\nFailed at 141.918 us; peak %.0f K"%e["Tmax_K"]);ax.set_aspect("equal");ax.plot(.5,.790913,"wx",ms=7,mew=1.5)
fig.colorbar(col,ax=axes,label="Raw failed-state temperature [K]",shrink=.82);fig.suptitle("Failed CFD controls from fresh time zero\n8.696 kJ/kg caloric mismatch; predictor accepted 0, rejected 1",fontsize=11);fig.savefig(r/"coupled-recovery-failed-fields.png",dpi=180)
