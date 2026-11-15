from pathlib import Path
import json
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
raw=json.loads((root/"hot-enthalpy-query-summary.json").read_text(encoding="utf8"))
audit=json.loads((root/"hot-state-target-audit.json").read_text(encoding="utf8"))["cases"]
ids=["schmitt-global-hot","schmitt-radial-hot-15","cavalieri-global-hot","cavalieri-radial-hot-15"]
labels=["Schmitt\nhottest cell","Schmitt\nx≈15 mm","Cavalieri\nhottest cell","Cavalieri\nx≈15 mm"]
current=[next(q for q in raw if q["id"]==i+"-captured")["capturedT_K"] for i in ids]
target=[next(q for q in raw if q["id"]==i+"-target")["recoveredTemperatures_K"][0] for i in ids]
progress=[100*next(q for q in audit if q["id"]==i)["progressFractionOfTarget"] for i in ids]
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.labelsize":12,"axes.linewidth":1,"xtick.direction":"in","ytick.direction":"in","legend.frameon":False})
fig,axes=plt.subplots(1,2,figsize=(10,4.6),gridspec_kw={"width_ratios":[1,1.3]})
x=np.arange(4)
axes[0].plot(x,progress,"o",ms=8,color="#2256a0",label="Captured CO + CO₂ / target")
axes[0].axhline(100,color="0.4",ls="--",lw=1,label="Target composition")
axes[0].set(ylabel="Progress indicator (% of table target)",ylim=(0,110),xticks=x,xticklabels=labels)
axes[0].legend(loc="upper center",fontsize=9)
for i in x:axes[1].plot([i,i],[current[i],target[i]],color="0.72",lw=1.5,zorder=1)
axes[1].plot(x,current,"o",ms=8,color="#2256a0",label="Captured CFD temperature")
axes[1].plot(x,target,"D",ms=7,color="#bd5228",label="Table composition at captured Ha, p")
axes[1].set(ylabel="Temperature (K)",ylim=(1000,4000),xticks=x,xticklabels=labels)
axes[1].legend(loc="upper center",fontsize=9)
for ax in axes:ax.tick_params(axis="x",labelsize=9,pad=8);ax.grid(axis="y",alpha=.18)
fig.suptitle("Retained G2 hot cells: composition lag and fixed-enthalpy queries",fontsize=13)
fig.text(.5,.015,"Original 5 ms CFD states; independent library queries. Target substitutions are thermodynamic diagnostics.",ha="center",fontsize=9)
fig.tight_layout(rect=(0,.055,1,.94));fig.savefig(root/"hot-cell-source-diagnostic.png",dpi=180);plt.close(fig)
