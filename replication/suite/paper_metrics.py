"""Approximate PDF-curve errors; never extrapolate or bridge clipped segments."""
import numpy as np
from datasets import table, FIELDS
from common import read_json


def compare(layers, output):
    methane=table(output/"data/paper-2022-figure6-curves.csv")
    flames=read_json(output/"data/paper-counterflow-curves.json")["curves"]
    records=[]
    for layer in layers:
        figure=layer["figure"]
        if figure not in {"2022-fig06","2022-fig09","2022-fig10","2022-fig11"}: continue
        segments=[]
        if figure=="2022-fig06":
            pressure=int(layer["label"].split()[-2])
            if pressure==1 and layer["field"]=="rho":
                records.append({"label":layer["label"],"field":"rho","status":"not scored: unresolved 1-atm curve"})
                continue
            rows=[r for r in methane if r["property"]==FIELDS[layer["field"]] and int(r["p_atm"])==pressure]
            for segment in sorted({r["segment"] for r in rows}):
                part=[r for r in rows if r["segment"]==segment]
                segments.append(("Nguyen",[float(r["T_K"]) for r in part],[float(r["value"]) for r in part]))
        else:
            for row in flames:
                if row["figure"]==int(figure[-2:]) and row["field"]==layer["field"]:
                    segments.append((row["series"],row["z_m"],row["value"]))
        x,y=np.array(layer["x"]),np.array(layer["y"])
        for source in sorted({s[0] for s in segments}):
            target=np.full(len(x),np.nan)
            for name,sx,sy in segments:
                if name!=source: continue
                sx=np.asarray(sx);sy=np.asarray(sy);order=np.argsort(sx);sx,unique=np.unique(sx[order],return_index=True);sy=sy[order][unique]
                visible=(x>=sx[0])&(x<=sx[-1])
                target[visible]=np.interp(x[visible],sx,sy)
            valid=np.isfinite(target)
            if not valid.any(): continue
            delta=y[valid]-target[valid]
            record={"figure":figure,"label":layer["label"],"field":layer["field"],"reference":source,
                    "matched_samples":int(valid.sum()),"RMS_absolute":float(np.sqrt(np.mean(delta**2))),
                    "max_absolute":float(abs(delta).max()),"qualification":"approximate digitization; no acceptance tolerance or fitted alignment"}
            if figure=="2022-fig06":
                record["RMS_relative"]=float(np.sqrt(np.mean((delta/target[valid])**2)))
            records.append(record)
    return records
