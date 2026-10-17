"""Plot verified comparison CSV; keep matplotlib's cache under the project root."""
import argparse
import csv
import os
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("comparison", type=Path)
parser.add_argument("--project-root", type=Path, required=True)
args = parser.parse_args()
root = args.project_root.resolve()
directory = args.comparison.resolve()
directory.relative_to(root)
os.environ["MPLCONFIGDIR"] = str(root/"cache/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

with (directory/"errors.csv").open(newline="") as stream:
    rows = list(csv.DictReader(stream))
properties = [("rho_kg_m3", "Density (kg/m³)"), ("Cp_J_kg_K", "Cp (J/(kg K))"),
              ("mu_Pa_s", "Viscosity (Pa s)"), ("kappa_W_m_K", "Conductivity (W/(m K))")]
for eos in ("SRK", "PR"):
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    for axis, (name, label) in zip(axes.flat, properties):
        for pressure, color in zip((1, 50, 100, 200, 300), plt.get_cmap("tab10").colors):
            group = sorted((r for r in rows if r["eos"] == eos and r["property"] == name
                            and float(r["p_atm"]) == pressure), key=lambda r: float(r["T_K"]))
            temperatures = [float(r["T_K"]) for r in group]
            axis.plot(temperatures, [float(r["computed"]) for r in group], color=color, label=f"{pressure} atm")
            axis.plot(temperatures, [float(r["reference"]) for r in group], linestyle="none",
                      marker="o", markersize=3, markerfacecolor="none", color=color)
        axis.set(xlabel="Temperature (K)", ylabel=label)
        axis.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=9)
    fig.suptitle(f"Methane: {eos}/rfJanaf/Chung\nLines: realFluidFoam OF8; circles: NIST WebBook retrieved 2026-10-17")
    for extension in ("png", "pdf"):
        destination = directory/f"methane-{eos}.{extension}"
        if destination.exists():
            raise FileExistsError(destination)
        fig.savefig(destination, dpi=180)
    plt.close(fig)
print("Saved SRK and PR comparisons as PNG and PDF")
