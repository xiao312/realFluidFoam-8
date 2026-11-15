from pathlib import Path
import csv,json,sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
r=Path(sys.argv[1]);fig,axes=plt.subplots(2,2,figsize=(10,6),layout="constrained")
for col,(tag,point,title) in enumerate([("s05","cavalieri-fixedtime-failed-point.json","Cavalieri: 161.809 us failed state"),("s10","schmitt-fixedtime-long-failed-point.json","Schmitt: 682.083 us failed state")]):
 q=json.loads((r/point).read_text());data=list(csv.DictReader((r/(tag+"-queries/scan/cold-properties.csv")).open()));data=[v for v in data if abs(float(v["T_K"])-q["temperature_K"])<.002];data.sort(key=lambda v:float(v["T_K"]));x=[1000*(float(v["T_K"])-q["temperature_K"]) for v in data]
 for row,(key,target,label,unit) in enumerate([("Hs_J_kg",q["storedHs_J_kg"],"Sensible enthalpy","kJ/kg"),("rho_kg_m3",q["storedTransportDensity_kg_m3"],"Density","kg/m3")]):
  ax=axes[row,col];scale=.001 if row==0 else 1
  ax.plot(x,[float(v[key])*scale for v in data],"o-",color="#176aa8",label="Executing largest-root EOS",lw=1.2,ms=5)
  ax.axhline(target*scale,color="#aa3c39",ls="--",lw=1.3,label="Transported constraint")
  ax.set(xlim=(-1.1,1.1),ylabel=label+" ["+unit+"]",xlabel="Temperature offset from failed T [mK]")
  ax.grid(alpha=.2);ax.legend(fontsize=8)
  if row==0:ax.set_title(title+"\np = %.6f MPa; T = %.9f K"%(q["pressure_Pa"]/1e6,q["temperature_K"]),fontsize=10)
fig.suptitle("Actual-library branch jumps at two retained cold failures",fontsize=13)
fig.savefig(r/"cold-branch-discontinuities.png",dpi=180)
