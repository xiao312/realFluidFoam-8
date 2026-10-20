"""Add light-species and high-pressure property pages to the verification PDF."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("light", type=Path)
    parser.add_argument("self_diffusion", type=Path)
    parser.add_argument("existing_pdf", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = [args.light, args.self_diffusion, args.existing_pdf]
    if not all(path.is_file() for path in paths):
        parser.error("Missing input report")
    if args.output is None:
        print("Plan: preserve existing PDF; append two property pages and PNG previews")
        return
    if args.output.exists():
        parser.error("Select a new output directory")
    import fitz
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.lines import Line2D
    light = json.loads(args.light.read_text())
    high = json.loads(args.self_diffusion.read_text())
    args.output.mkdir(parents=True)
    plt.rcParams.update({"font.family": "serif", "font.size": 9,
                         "axes.linewidth": .7, "lines.linewidth": 1.1})
    colors = ["#1f77b4", "#d62728", "#2c8b46", "#8c5aa6"]
    with PdfPages(args.output/"additional-properties.pdf") as pages:
        fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.8))
        fig.subplots_adjust(left=.08, right=.98, bottom=.40, top=.90, wspace=.30)
        for color, series in zip(colors, light["references"]["hydrogen"]["series"]):
            rows = [r for r in light["hydrogen"] if r["series"] == series["id"]]
            axes[0].plot([r["temperature_K"] for r in rows],
                         [r["residual_percent"] for r in rows], "o-", ms=3,
                         color=color, label=series["id"]+"; carrier "+series["carrier"])
        axes[0].axhspan(-2, 2, color=".9", zorder=-1, label="Author estimated +/-2%")
        axes[0].set(title="(a) Hydrogen: measured Taylor diffusion",
                    xlabel="Temperature (K)", ylabel="Model minus reference (%)", ylim=(-7.2, 2.5))
        axes[0].legend(fontsize=6.3, loc="lower center", bbox_to_anchor=(.5, -.36), ncol=2)
        for color, name in zip(colors, ["H2O-N2", "H2O-CO2", "CH4-N2", "O2-O2"]):
            rows = [r for r in light["nist_fits"] if r["series"] == name]
            axes[1].plot([r["temperature_K"] for r in rows],
                         [r["residual_percent"] for r in rows], "s-", ms=3,
                         color=color, label=name)
        axes[1].set(title="(b) NIST evaluated temperature fits",
                    xlabel="Temperature (K)", ylabel="Model minus fit (%)", ylim=(-12, 1))
        axes[1].legend(fontsize=7, loc="lower center", bbox_to_anchor=(.5, -.36), ncol=2)
        for ax in axes:
            ax.axhline(0, color="k", lw=.7)
            ax.tick_params(direction="in", top=True, right=True)
        oh, later = light["oh_air"], light["oh_air_followup"]
        note = (
            "Fixed author transport / Cantera 3.2; 101325 Pa. Chemistry unchanged. Stock GRI30 differs by at most 0.16% here.\n"
            "Matsunaga (2001), Table 1: carrier directions retained; +/-2% is estimated, not a stated 95% interval.\n"
            "NIST TN2279: evaluated fits, sampled only inside published ranges; printed uncertainty ranges are 2-5%.\n"
            f"OH-air at 296 K: model {oh['calculated_cm2_s']['author']['air_21_79']:.4f}, Ivanov (2007) {oh['reference_cm2_s']:.4f} +/- {oh['reported_uncertainty_cm2_s']:.4f} cm2/s.\n"
            f"OH-air at 300 K: model {later['calculated_cm2_s']:.4f}, Liu (2009) {later['reference_cm2_s']:.4f} +/- {later['reported_uncertainty_cm2_s']:.4f} cm2/s.\n"
            "OH checks use approximate 21/79 air; room-temperature evidence does not qualify hot-flame extrapolation."
        )
        fig.text(.08, .025, note, fontsize=7, va="bottom", linespacing=1.45)
        fig.savefig(args.output/"light-species.png", dpi=200)
        pages.savefig(fig)
        plt.close(fig)
        fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.6))
        fig.subplots_adjust(left=.08, right=.98, bottom=.30, top=.90, wspace=.30)
        for color, nominal in zip(colors, [257, 297, 323, 354]):
            rows = sorted([r for r in high["rows"] if r["isotherm_K"] == nominal and r["table_range"]],
                          key=lambda r: r["Pr"])
            p = np.array([r["Pr"] for r in rows])
            axes[0].plot(p, [r["correction_factor"] for r in rows], color=color)
            axes[0].plot(p, [r["measured_over_dilute"] for r in rows], "o",
                         ms=3.5, mfc="none", color=color)
            axes[1].plot(p, [r["normalized_shape_error_percent"] for r in rows],
                         "o-", ms=3.2, color=color, label=f"{nominal} K")
        axes[0].set(title="(a) Methane self-diffusion",
                    xlabel="Reduced pressure $P_r$", ylabel="$D / D_{dilute}$",
                    xlim=(0, 5.1), ylim=(.55, 1.05))
        axes[0].legend(handles=[Line2D([], [], color="k", label="Takahashi Table 2"),
                                Line2D([], [], color="k", marker="o", mfc="none", ls="",
                                       label="Dawson measurement / dilute model")],
                       fontsize=6.8, loc="lower left")
        axes[1].set(title="(b) Pressure trend, normalized at first point",
                    xlabel="Reduced pressure $P_r$", ylabel="Model trend minus measured trend (%)",
                    xlim=(0, 5.1))
        axes[1].legend(fontsize=7, ncol=2)
        for ax in axes:
            ax.tick_params(direction="in", top=True, right=True)
        axes[1].axhline(0, color="k", lw=.7)
        summary = high["summary"]
        note = (
            "Dawson dissertation (1966), Table I, p.104; pulsed-NMR pure-CH4 self-diffusion. No mixture thermodynamic factor.\n"
            f"28 in-range points shown; 7 beyond Pr=5 retained separately in JSON. Mean absolute error: "
            f"{summary['dilute_mean_absolute_error_percent']:.2f}% dilute, {summary['corrected_mean_absolute_error_percent']:.2f}% corrected.\n"
            "Separate uncertainty components: 3% shared gradient systematic, about 1.5% scatter; no stated 95% interval.\n"
            f"Pressure treated as absolute; +1 atm sensitivity changes predictions by up to {summary['pressure_basis_max_prediction_change_percent']:.2f}%.\n"
            "Panel (b) cancels constant scale and shared calibration; first measured point is not zero pressure.\n"
            "This conditional pure-fluid check does not validate radical binary diffusion or resolve the Liang flame-speed gap."
        )
        fig.text(.08, .025, note, fontsize=7, va="bottom", linespacing=1.45)
        fig.savefig(args.output/"self-diffusion.png", dpi=200)
        pages.savefig(fig)
        plt.close(fig)
    combined = fitz.open(args.existing_pdf)
    original_count = len(combined)
    with fitz.open(args.output/"additional-properties.pdf") as addition:
        combined.insert_pdf(addition)
    combined.save(args.output/"diffusion-validation.pdf")
    if len(combined) != original_count+2:
        raise ValueError("Unexpected page count")
    for index in range(original_count, len(combined)):
        combined[index].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(
            args.output/f"page-{index+1}-render.png")
    combined.close()
    manifest = dict(
        inputs={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_page_count=original_count, output_page_count=original_count+2,
        flame_curves_changed=False)
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
