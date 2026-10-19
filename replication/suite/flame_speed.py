"""Finite-time gas-relative diagnostics; these are not accepted flame speeds."""
import numpy as np


def track(job, level=5e-5):
    cfg = job["metadata"]["config"]
    n = cfg["cells"]
    x = (np.arange(n)+.5)*cfg["length_m"]/n
    rows = []
    for sample in job["samples"]:
        f = {k: np.asarray(v, dtype=float) for k, v in sample["fields"].items()}
        for name in ("OH", "T", "U", "rho"):
            if name not in f or f[name].shape != (n,) or not np.isfinite(f[name]).all():
                raise ValueError(f"Missing/invalid {name} in job {job['job']}")
        oh = f["OH"]
        peak = int(oh.argmax())
        crossings = np.flatnonzero((oh[:peak] < level) & (oh[1:peak+1] >= level))
        if len(crossings) != 1:
            raise ValueError(f"OH={level:g}: expected one rising crossing")
        i = crossings[0]
        position = x[i]+(level-oh[i])/(oh[i+1]-oh[i])*(x[i+1]-x[i])
        gradient = np.gradient(f["T"], x)
        k = int(gradient.argmax())
        if not 0 < k < n-1:
            raise ValueError("Temperature front touches domain boundary")
        denominator = gradient[k-1]-2*gradient[k]+gradient[k+1]
        offset = .5*(gradient[k-1]-gradient[k+1])/denominator if denominator else 0
        if abs(offset) > 1 or np.max(f["T"][:min(100,n//10)]) > cfg["unburned_temperature_K"]+1:
            raise ValueError("Temperature marker or unburned region is invalid")
        rows.append([sample["time_s"], position, np.interp(position,x,f["U"]),
                     np.interp(position,x,f["rho"]), x[k]+offset*(x[1]-x[0]),
                     np.mean(f["U"][:min(100,n//10)])])
    rows = np.array(sorted(rows))
    if len(rows) < 3 or np.any(np.diff(rows[:,0]) <= 0):
        raise ValueError("Need three distinct saved times")
    return rows


def estimate(rows, rho_u, duration):
    """Use actual saved times, not a presumed write interval."""
    selected = rows[rows[:,0] >= rows[-1,0]-duration-1e-12]
    if len(selected) < 3 or selected[-1,0]-selected[0,0] < duration*.8:
        raise ValueError("Insufficient saved history for requested speed window")
    if not np.isfinite(rho_u) or rho_u <= 0:
        raise ValueError("Unburned density must be positive")
    t = selected[:,0]-selected[0,0]
    oh_velocity = np.polyfit(t, selected[:,1], 1)[0]
    thermal_velocity = np.polyfit(t, selected[:,4], 1)[0]
    return {"start_s":float(selected[0,0]), "end_s":float(selected[-1,0]),
            "samples":len(selected), "OH_speed_cm_s":float(100*np.mean(selected[:,3]*(selected[:,2]-oh_velocity))/rho_u),
            "temperature_speed_cm_s":float(100*(selected[:,5].mean()-thermal_velocity))}
