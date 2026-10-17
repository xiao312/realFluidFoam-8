"""Replot both papers' property figures using actual library data and references."""
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
import numpy as np

root = Path(sys.argv[1]).resolve(strict=True)
os.environ["MPLCONFIGDIR"] = str(root/"cache/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

out = root/"output/figure-comparison-20261017"
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10, "axes.labelsize": 11})


def read(path, delimiter=","):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def save(fig, name):
    fig.savefig(out/"plots"/(name+".png"), dpi=180)
    fig.savefig(out/"plots"/(name+".svg"))
    plt.close(fig)


curves = read(out/"data/paper-2022-figure6-curves.csv")
states = read(root/"state/properties-124660240/jobs/124660240/properties-SRK/properties.csv")
reference = read(root/"state/properties-124660240-comparison/errors.csv")
styles = ["-.", (0, (5, 2, 1, 2)), (0, (3, 3)), (0, (7, 3)), "-"]
properties = [("rho_kg_m3", "Density [kg/m³]", (-10, 400)),
              ("Cp_J_kg_K", "Cp [J/(kg K)]", (1800, 8500)),
              ("mu_Pa_s", "Dynamic viscosity [kg/(m s)]", (0, 6.5e-5)),
              ("kappa_W_m_K", "Thermal conductivity [W/(m K)]", (0, .155))]
fig, axes = plt.subplots(2, 2, figsize=(10, 7.4))
fig.subplots_adjust(top=.86, bottom=.10, left=.10, right=.97, hspace=.30, wspace=.32)
metrics = []
for axis, (name, label, ylim), letter in zip(axes.flat, properties, "abcd"):
    for pressure, style in zip((1, 50, 100, 200, 300), styles):
        group = [r for r in curves if r["property"] == name and int(r["p_atm"]) == pressure]
        segments = []
        for segment in sorted({r["segment"] for r in group}):
            part = sorted((r for r in group if r["segment"] == segment), key=lambda r: float(r["T_K"]))
            x = np.array([float(r["T_K"]) for r in part])
            y = np.array([float(r["value"]) for r in part])
            x, indices = np.unique(x, return_index=True)
            y = y[indices]
            segments.append((x, y))
            axis.plot(x, y, color="#c52929", linestyle=style, lw=1.1)
        our = [r for r in states if float(r["p_atm"]) == pressure]
        x = np.array([float(r["T_requested_K"]) for r in our])
        y = np.array([float(r[name]) for r in our])
        axis.plot(x, y, "o", color="#1765b5", ms=2.4, mfc="none", mew=.7, markevery=2)
        nist = [r for r in reference if r["eos"] == "SRK" and r["property"] == name and float(r["p_atm"]) == pressure]
        axis.plot([float(r["T_K"]) for r in nist], [float(r["reference"]) for r in nist],
                  "^", color="black", ms=2.7, mfc="none", mew=.5, markevery=2)
        errors = []
        for temperature, value in zip(x, y):
            for sx, sy in segments:
                if sx[0]-.02 <= temperature <= sx[-1]+.02:
                    target = np.interp(temperature, sx, sy)
                    errors.append((value-target)/target)
                    break
        metrics.append(dict(property=name, pressure_atm=pressure, matched_states=len(errors),
            rms_relative_to_digitized_curve=float(np.sqrt(np.mean(np.square(errors)))),
            max_absolute_relative_to_digitized_curve=float(np.max(np.abs(errors)))))
        if name == "rho_kg_m3" and pressure == 1:
            metrics[-1].update(rms_relative_to_digitized_curve=None,
                max_absolute_relative_to_digitized_curve=None,
                qualification="Not scored: low-density curve is unresolved on the printed 0-400 kg/m3 scale; use numerical NIST comparison.")
    axis.set(xlim=(180, 625), ylim=ylim, xlabel="Temperature [K]", ylabel=label)
    axis.set_title(f"({letter})", loc="left", fontweight="bold")
axes[0, 0].legend([Line2D([], [], color="#c52929", ls=s) for s in styles],
                  [f"{p} atm" for p in (1, 50, 100, 200, 300)], loc="upper right", fontsize=8)
fig.legend([Line2D([], [], color="#c52929"), Line2D([], [], color="#1765b5", marker="o", mfc="none", ls="none"),
            Line2D([], [], color="black", marker="^", mfc="none", ls="none")],
           ["Published curves (vector digitization)", "Our OF8 SRK", "NIST retrieved 2026-10-17"],
           loc="upper center", bbox_to_anchor=(.52, .955), ncol=3, fontsize=8)
fig.suptitle("2022 Figure 6 - direct methane-property comparison", y=.995)
fig.text(.5, .012, "Paper axis limits retained; hidden Cp peak is not interpolated. Inversion criterion remains failed.", ha="center", fontsize=8)
save(fig, "2022-fig06")
(out/"data/methane-paper-curve-errors.json").write_text(json.dumps(metrics, indent=2)+"\n")

# Nitrogen: reproduce the panel placement and zoom windows of 2025 Figure 6.
reference_manifest = json.loads((root/"state/figure-audit-20261017/nitrogen-reference.json").read_text())
reference_path = root/"state/figure-audit-20261017/nitrogen-3.98MPa.tsv"
if hashlib.sha256(reference_path.read_bytes()).hexdigest() != reference_manifest["merged_sha256"]:
    raise ValueError("Nitrogen reference hash mismatch")
nist = read(reference_path, "\t")
temperature = np.array([float(r["Temperature (K)"]) for r in nist])
density = np.array([float(r["Density (kg/m3)"]) for r in nist])
cp = np.array([float(r["Cp (J/g*K)"])*1000 for r in nist])
models = {eos: read(root/f"state/nitrogen-124662568/jobs/124662568/properties-{eos}/properties.csv") for eos in ("SRK", "PR")}
fig, axes = plt.subplots(2, 2, figsize=(10, 7.4))
fig.subplots_adjust(top=.88, bottom=.10, left=.10, right=.97, hspace=.35, wspace=.30)
for axis, window, limits, letter in [(axes[0, 0], (100, 325), (0, 800), "a"),
                                    (axes[0, 1], (125, 140), (120, 500), "c"),
                                    (axes[1, 1], (150, 320), (30, 150), "d")]:
    axis.plot(temperature, density, "k-", lw=1.2, label="NIST (current)")
    indices = np.where((temperature >= window[0]) & (temperature <= window[1]))[0][::max(1, int((window[1]-window[0])/8))]
    axis.plot(temperature[indices], density[indices], "o", color="black", ms=3, mfc="white", mew=.6)
    for eos, color, style in (("PR", "#d42929", "--"), ("SRK", "#2459cc", "-.")):
        axis.plot([float(r["T_K"]) for r in models[eos]], [float(r["rho_kg_m3"]) for r in models[eos]],
                  color=color, ls=style, lw=1.3, label=f"Our {eos}")
    axis.set(xlim=window, ylim=limits, xlabel="T [K]", ylabel="Density [kg/m³]")
    axis.set_title(f"({letter})", loc="left", fontweight="bold")
axes[0, 0].legend(fontsize=8)
axes[0, 1].axvline(126.9, color=".55", lw=.7)
axes[0, 1].axvline(137, color=".55", lw=.7)
axes[0, 1].text(127.2, 470, "Case 3: 126.9 K", fontsize=8)
axes[0, 1].text(132, 165, "Case 4: 137 K", fontsize=8)
axes[1, 1].axvline(298, color=".55", lw=.7)
axes[1, 1].text(215, 115, "Chamber: 298 K", fontsize=8)
axis = axes[1, 0]
axis.plot(temperature, cp, "k-", label="NIST (current)", lw=1.2)
axis.plot(temperature[::12], cp[::12], "o", color="black", ms=3, mfc="white", mew=.6)
axis.plot([float(r["T_K"]) for r in models["PR"]], [float(r["Cp_J_kg_K"]) for r in models["PR"]],
          color="#d42929", lw=1.2, label="Our PR/rfJanaf")
axis.set(xlim=(100, 325), ylim=(0, 14000), xlabel="T [K]", ylabel="Cp [J/(kg K)]")
axis.set_title("(b)", loc="left", fontweight="bold")
axis.legend(fontsize=8)
fig.suptitle("2025 Figure 6 - nitrogen at 3.98 MPa", y=.97)
fig.text(.5, .012, "Job 124662568; 0.25 K grid; unchanged library. Property comparison only; inversion criterion failed.", ha="center", fontsize=8)
save(fig, "2025-fig06")
metrics = []
for eos, rows in models.items():
    if len(rows) != 901 or not np.allclose([float(r["T_K"]) for r in rows], temperature, atol=1e-8, rtol=0):
        raise ValueError("Nitrogen solver/reference grid mismatch")
    for name, target in (("rho_kg_m3", density), ("Cp_J_kg_K", cp)):
        values = np.array([float(r[name]) for r in rows])
        relative = (values-target)/target
        worst = int(np.argmax(np.abs(relative)))
        metrics.append(dict(eos=eos, property=name, rms_relative_error=float(np.sqrt(np.mean(relative**2))),
                            max_absolute_relative_error=float(abs(relative[worst])), worst_T_K=float(temperature[worst])))
(out/"data/nitrogen-nist-errors.json").write_text(json.dumps(metrics, indent=2)+"\n")
print("Rendered both property figures and saved quantitative comparison metrics")
