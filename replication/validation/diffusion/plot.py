"""Plot dilute validation residuals and the verified Takahashi correlation."""
import argparse
import csv
import json
from pathlib import Path
from prepare import correction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dilute_report", type=Path)
    parser.add_argument("requests", type=Path)
    parser.add_argument("samples", type=Path)
    parser.add_argument("--output", type=Path, help="New output directory; omit for plan")
    args = parser.parse_args()
    for path in (args.dilute_report, args.requests, args.samples):
        if not path.is_file():
            parser.error("Missing input: " + str(path))
    if args.output is None:
        print("Plan: two-panel PNG/PDF; inputs read-only; no files written")
        return
    if args.output.exists():
        parser.error("Select a new output directory")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    report = json.loads(args.dilute_report.read_text())
    rows = [r for r in report["rows"] if r["bath"] == "N2"]
    with args.requests.open() as stream:
        requests = list(csv.DictReader(stream))
    with args.samples.open() as stream:
        samples = list(csv.DictReader(stream))
    if len(requests) != len(samples):
        raise ValueError("Mismatched correlation files")
    table = json.loads(Path(__file__).with_name("references.json").read_text())["takahashi"]["table2"]
    plt.rcParams.update({"font.family": "serif", "font.size": 9,
                         "axes.linewidth": .7, "lines.linewidth": 1.1})
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), layout="constrained")
    temperatures = [r["temperature_K"] for r in rows]
    uncertainty = [100*r["uncertainty_cm2_s"]/r["reference_cm2_s"] for r in rows]
    axes[0].fill_between(temperatures, -np.array(uncertainty), uncertainty,
                         color=".85", label="NIST reported 95% uncertainty")
    axes[0].plot(temperatures, [r["residual_percent"] for r in rows],
                 "o-", ms=3.5, label="Author mechanism / Cantera")
    axes[0].plot(temperatures,
                 [100*(r["stock_gri30_cm2_s"]/r["reference_cm2_s"]-1) for r in rows],
                 "--", label="Stock Cantera GRI30")
    axes[0].axhline(0, color="k", lw=.7)
    axes[0].set(xlabel="Temperature (K)", ylabel="CH$_4$–N$_2$ residual (%)",
                title="(a) Dilute data, 101.3 kPa")
    axes[0].legend(fontsize=7, loc="center", bbox_to_anchor=(.5, .48))
    pressures = np.linspace(.1, 5, 300)
    for tr in (1, 1.5, 2, 3, 5):
        line, = axes[1].plot(pressures, [correction(p, tr, table) for p in pressures],
                            label=f"$T_r={tr:g}$")
        subset = [(q, s) for q, s in zip(requests, samples)
                  if q["first"] == "CH4" and float(q["Tr"]) == tr
                  and .1 <= float(q["Pr"]) <= 5]
        axes[1].plot([float(q["Pr"]) for q, _ in subset],
                     [float(s["factor"]) for _, s in subset],
                     "o", ms=2, mfc="none", mew=.5, color=line.get_color())
    axes[1].set(xlabel="Reduced pressure $P_r$", ylabel="$Dp/(Dp)^0$",
                title="(b) Table 2 lines; actual adapter markers", ylim=(0, 1.1))
    axes[1].legend(fontsize=7, ncol=2)
    args.output.mkdir(parents=True)
    fig.savefig(args.output / "diffusion-validation.png", dpi=220)
    fig.savefig(args.output / "diffusion-validation.pdf")
    plt.close(fig)


if __name__ == "__main__":
    main()
