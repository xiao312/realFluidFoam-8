"""Validate saved evidence and prepare numerical series without changing values."""
import csv
import subprocess
import sys
import numpy as np
from common import REPLICATION, contained, digest, read_json, write_json
from flame_speed import track, estimate

sys.path.insert(0, str(REPLICATION/"validation/figures"))
from foam_fields import read_decomposed

FIELDS = {"rho":"rho_kg_m3", "Cp":"Cp_J_kg_K", "mu":"mu_Pa_s", "kappa":"kappa_W_m_K"}
COLORS = {"CH4":"#333333", "O2":"#0080ff", "CO2":"#00bcbc", "H2O":"#00ba00", "OH":"#ff00bc"}


def table(path, delimiter=","):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def values(rows, key):
    array = np.array([float(r[key]) for r in rows])
    if not np.isfinite(array).all():
        raise ValueError(f"Nonfinite {key}")
    return array


def series(figure, panel, field, x, y, label, color="#165bbb", marker=None, **extra):
    x, y = np.asarray(x), np.asarray(y)
    if x.ndim != 1 or x.shape != y.shape or not len(x) or not np.isfinite(x+y).all():
        raise ValueError(f"Invalid series: {label}/{field}")
    return dict(figure=figure, panel=panel, field=field, x=x.tolist(), y=y.tolist(),
                label=label, color=color, marker=marker, **extra)


def properties(config, inputs, output):
    layers, metrics = [], {}
    for gas in ("methane", "nitrogen"):
        cfg = config[gas]
        models = {e: table(inputs.file(p)) for e,p in cfg["files"].items()}
        inputs.file(cfg["receipt"])
        if gas == "methane":
            refdir = contained(inputs.root,cfg["reference_dir"],True)
            for path in sorted(refdir.glob("*.tsv")): inputs.file(path)
            subprocess.run([sys.executable, "-B", str(REPLICATION/"validation/properties/compare.py"),
                str(inputs.file(cfg["files"]["SRK"])),str(inputs.file(cfg["files"]["PR"])),
                str(refdir),str(output/"data/methane-nist")], check=True)
            metrics[gas] = read_json(output/"data/methane-nist/provenance.json")
            for field, column in FIELDS.items():
                for pressure in (1,50,100,200,300):
                    rows = [r for r in models["SRK"] if float(r["p_atm"])==pressure]
                    layers.append(series("2022-fig06",field,field,values(rows,"T_K"),values(rows,column),
                                         f"Computed SRK {pressure} atm",marker="^"))
        else:
            refpath = inputs.file(cfg["reference"])
            receipt = read_json(inputs.file(cfg["reference_manifest"]))
            if digest(refpath) != receipt["merged_sha256"]:
                raise ValueError("Nitrogen reference hash mismatch")
            reference = table(refpath,"\t")
            t = values(reference,"Temperature (K)")
            if not np.array_equal(t,np.linspace(100,325,901)):
                raise ValueError("Nitrogen reference coverage must be 901 specified temperatures")
            metrics[gas] = {}
            for eos, rows in models.items():
                if len(rows)!=901 or not np.allclose(values(rows,"T_K"),t,atol=1e-8,rtol=0):
                    raise ValueError(f"Nitrogen coverage mismatch: {eos}")
                if not np.allclose(values(rows,"p_atm")*101325,3980000,atol=.01,rtol=0):
                    raise ValueError("Nitrogen pressure mismatch")
                errors = {}
                for field, refkey, scale in [("rho","Density (kg/m3)",1),("Cp","Cp (J/g*K)",1000)]:
                    target = values(reference,refkey)*scale
                    y = values(rows,FIELDS[field])
                    if np.any(y<=0): raise ValueError("Nonpositive nitrogen property")
                    rel = (y-target)/target
                    errors[field] = {"RMS_relative":float(np.sqrt(np.mean(rel**2))),
                                     "max_absolute_relative":float(abs(rel).max())}
                inversion = values(rows,"inversion_relative_error")
                if np.any(inversion<0): raise ValueError("Negative inversion error")
                errors["inversion"] = {"threshold":1e-6,"failed_states":int(np.sum(inversion>1e-6))}
                metrics[gas][eos] = errors
                for panel, field in [("a","rho"),("b","Cp"),("c","rho"),("d","rho")]:
                    if panel=="b" and eos=="SRK": continue
                    # Density marker spacing follows the visible source marker cadence.
                    stride = 4 if panel=="c" else 32
                    layers.append(series("2025-fig06",panel,field,t[::stride],values(rows,FIELDS[field])[::stride],
                                         f"Computed {eos}",color="#165bbb" if eos=="PR" else "#009688",marker="o"))
    return layers, metrics


def counterflows(config, inputs, output):
    cfg = config["counterflow"]
    manifest = read_json(inputs.file(cfg["manifest"]))
    receipt_path = inputs.file(cfg["snapshot_receipt"])
    receipt = read_json(receipt_path)
    layers, contours, records = [], {}, {}
    for key, number in [("oxy-1",9),("oxy-200",10),("air-100",11)]:
        item = manifest["cases"][key]
        case = contained(inputs.root,item["path"],True)
        source = receipt["cases"][key]
        if "source="+cfg["source_revision"] not in source["inputs"] or "build_job="+cfg["build_job"] not in source["inputs"]:
            raise ValueError(f"Counterflow identity mismatch: {key}")
        if item["time"] not in source["times"]:
            raise ValueError("Requested time absent from snapshot receipt")
        # Check all collected files against the transfer receipt before reading fields.
        for relative, expected in source["sha256"].items():
            path = inputs.file(receipt_path.parent/relative)
            if digest(path)!=expected: raise ValueError(f"Snapshot changed: {path}")
        if case != (receipt_path.parent/source["case"]).resolve():
            raise ValueError("Case path does not match snapshot receipt")
        xyz, fields, time = read_decomposed(case,item["time"],item["ranks"])
        radius = np.hypot(xyz[:,0],xyz[:,1])
        idx = np.flatnonzero(np.isclose(radius,radius.min(),rtol=0,atol=1e-9))
        idx = idx[np.argsort(xyz[idx,2])]
        z = xyz[idx,2]
        if np.any(np.diff(z)<=0): raise ValueError("Near-axis coordinates must increase")
        pairs = {"T":["T"],"species":["CH4","O2","CO2","H2O","OH"],
                 "thermo":["rho","Cp"],"transport":["mu","kappa"]} if number<11 else {
                 "thermo":["T","rho"],"species":["CH4","O2","CO2","H2O"]}
        for panel, names in pairs.items():
            for name in names:
                layers.append(series(f"2022-fig{number:02}",panel,name,z,fields[name][idx],
                                     f"Computed {key}: {name}",COLORS.get(name,"#165bbb")))
        names = list(FIELDS)+["T","CH4","O2","CO2","H2O","OH"]
        np.savetxt(output/"data"/f"{key}-near-axis.csv",np.column_stack([z,*[fields[n][idx] for n in names]]),
                   delimiter=",",header=",".join(["z_m",*names]),comments="")
        records[key] = {"job":source["job"],"time_s":time,"cells":len(xyz),"nearest_axis_r_m":float(radius.min()),
                        "status":manifest.get("case_status",{}).get(key,cfg["status"]),"inputs":source["inputs"]}
        if number<11:
            contours[key] = dict(xyz=xyz,fields=fields,radius=radius,case=case)
    return layers, contours, records


def premixed(config, inputs, output):
    cfg = config["premixed"]
    data = read_json(inputs.file(cfg["snapshot"]))
    layers, records = [], []
    for index, job in enumerate(data["jobs"]):
        record = {"job":job["job"],"phi":job["metadata"]["config"]["phi"],
                  "binary_sha256":job["binary_sha256"],"inlet_m_s":job["metadata"]["config"]["inlet_speed_m_s"],"estimates":[]}
        for level in cfg["OH_levels"]:
            rows = track(job,level)
            for window in cfg["windows_s"]:
                result = estimate(rows,job["runtime"]["unburned_density_kg_m3"],window)
                record["estimates"].append(dict(OH_level=level,window_s=window,**result))
        chosen = next(r for r in record["estimates"] if r["OH_level"]==5e-5 and r["window_s"]==min(cfg["windows_s"]))
        layers.append(series("2022-fig12","speed","speed",[record["phi"]],[chosen["OH_speed_cm_s"]],
                             f"Job {job['job']}, OH estimate",color=["#165bbb","#d47b00"][index%2],marker="s"))
        records.append(record)
    return layers, {"status":cfg["status"],"method":"rho/rho_u*(U-dx_OH/dt); thermal crosscheck Uu-dx_dTmax/dt; no source-term Eq40 evaluation", "jobs":records}
