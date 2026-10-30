"""Plots preserve sampled trajectories and expose incompatible coordinates."""
import numpy as np
import matplotlib.pyplot as plt
from inputs import sample_z
from digitize import with_gaps


def configure_style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "axes.labelsize": 13, "axes.titlesize": 13,
                         "legend.fontsize": 10, "lines.linewidth": 2,
                         "lines.markersize": 4, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.facecolor": "white"})


def save(fig, out, name):
    fig.savefig(out / f"{name}.png", dpi=180)
    fig.savefig(out / f"{name}.svg")
    plt.close(fig)


def figure_axes(title, ylabel, x_label, ylim=None):
    fig, ax = plt.subplots(figsize=(5.32, 4.71))
    fig.subplots_adjust(left=.17, right=.97, bottom=.18, top=.88)
    ax.set(title=title, ylabel=ylabel, xlabel=x_label)
    ax.grid(alpha=.17)
    if ylim is not None:
        ax.set_ylim(*ylim)
    return fig, ax


def time_diagnostics(data, out):
    trajectory, metrics = data["trajectory"], data["diagnostics"]["frame_metrics"]
    time = trajectory["time_s"] * 1e6
    fig, axes = plt.subplots(2, 1, figsize=(7.8, 7), sharex=True)
    fig.subplots_adjust(left=.14, right=.97, top=.9, bottom=.12, hspace=.18)
    axes[0].plot(time, trajectory["T_K"].max(axis=1), color="#be3c2a", label="Retained transient")
    axes[0].set(ylabel="Peak temperature (K)", title="Physical-time evolution | CH4/O2 diagnostic")
    axes[0].legend(loc="upper right")
    axes[1].plot([m["physical_time_s"] * 1e6 for m in metrics],
                 [m["C_at_stoichiometry"] for m in metrics], color="#007b91", marker="o", markevery=7)
    axes[1].set(ylabel=r"$C_{st}=Y_{CO_2}+Y_{CO}$", xlabel="Physical time (microseconds; symmetric log scale)")
    for ax in axes:
        ax.set_xscale("symlog", linthresh=1e-4)
        ax.set_xlim(0, float(time[-1]))
        ax.grid(alpha=.2)
    chi = data["receipt"]["integration"]["chi_st_s_inverse"]
    fig.text(.14, .025, f"Fresh HP-equilibrium start; chi_st = {chi:g} s^-1; integration completed, not accepted.", fontsize=9)
    save(fig, out, "time-evolution")

    fig, axes = plt.subplots(2, 1, figsize=(7.8, 7), sharex=True)
    fig.subplots_adjust(left=.16, right=.97, top=.9, bottom=.12, hspace=.2)
    t = np.array([m["physical_time_s"] for m in metrics]) * 1e6
    axes[0].plot(t, np.array([m["enthalpy_mixing_max_error_J_kg"] for m in metrics]) / 1000,
                 color="#be3c2a", marker="o", markevery=8)
    axes[0].set(ylabel="Max enthalpy error (kJ/kg)", title="Energy discrepancy remains unresolved")
    axes[1].plot(t, np.maximum([m["griffon_cantera_max_regularized_rate_error"] for m in metrics], 1e-16),
                 color="#007b91", label="Griffon vs Cantera kinetics")
    axes[1].set(yscale="log", ylabel="Regularized mass-rate error", xlabel="Physical time (microseconds; symmetric log scale)")
    axes[1].legend()
    for ax in axes:
        ax.set_xscale("symlog", linthresh=1e-4)
        ax.set_xlim(0, float(time[-1]))
        ax.grid(alpha=.2)
    fig.text(.16, .025, "Rate denominator: |Cantera species mass rate| + 1 kg/(m^3 s). Display floor: 1e-16.", fontsize=9)
    save(fig, out, "energy-and-kinetics")


def temperature_profiles(data, out):
    a = data["trajectory"]
    requested = [0, 1e-8, 5e-8, 1e-7, 1e-6, 1e-3]
    indices = sorted(set(int(np.argmin(abs(a["time_s"] - t))) for t in requested))
    fig, ax = figure_axes("Physical temperature profiles", "Temperature (K)", "Mixture fraction Z", (0, 4000))
    for index, color in zip(indices, plt.cm.viridis(np.linspace(.08, .9, len(indices)))):
        t = a["time_s"][index]
        ax.plot(a["Z"], a["T_K"][index], color=color, label=f"{t * 1e6:.3g} microseconds")
    ax.set_xlim(0, 1); ax.legend(frameon=False, fontsize=9)
    save(fig, out, "temperature-profiles")


def progress_comparisons(data, extractions, config, out):
    a, table = data["trajectory"], data["table"]
    species = list(a["species"])
    co2 = a["Y"][:, :, species.index("CO2")]
    progress = co2 + a["Y"][:, :, species.index("CO")]
    values = np.asarray(table["values"])
    exported = []
    for panel in config["panels"]:
        panel_id = panel["id"]
        source = a["T_K"] if panel_id == "temperature" else co2
        column = table["columns"].index("T_K" if panel_id == "temperature" else "Y_CO2")
        fig, ax = figure_axes("Trajectory diagnostic | different model", panel["ylabel"],
                              r"Our $c=C/C_{eq}$ (initial HP state)", panel["y_range"])
        for curve in config["curves"]:
            c = sample_z(a["Z"], progress, curve["z"])
            if c[0] <= 1e-12:
                raise ValueError("Initial equilibrium progress is too small to normalize")
            norm = c / c[0]
            field = sample_z(a["Z"], source, curve["z"])
            ax.plot(norm, field, color=curve["plot_color"], marker="o", markevery=40,
                    label=f"Z = {curve['z']:g}")
            exported.append({"panel": panel_id, "z": curve["z"], "coordinate": "raw C / initial HP-equilibrium C",
                             "time_s": a["time_s"].tolist(), "x": norm.tolist(), "y": field.tolist(),
                             "normalization_denominator": float(c[0]), "time_order_preserved": True})
        ax.legend(frameon=False, fontsize=10)
        # Do not clip C/C_initial excursions outside [0,1].
        save(fig, out, f"trajectory-{panel_id}")

        fig, ax = figure_axes("Table diagnostic | local coordinate", panel["ylabel"],
                              r"Local table $\eta$ (not paper $c$)", panel["y_range"])
        for curve in config["curves"]:
            field = sample_z(np.asarray(table["z"]), values[:, :, column].T, curve["z"])
            ax.plot(table["eta"], field, color=curve["plot_color"], marker="o", markevery=8,
                    label=f"Z = {curve['z']:g}")
        ax.set_xlim(0, 1); ax.legend(frameon=False, fontsize=10)
        save(fig, out, f"table-{panel_id}")

        fig, ax = figure_axes("Sharma Figure 2 | visible pixels", panel["ylabel"],
                              "Paper normalized progress c", panel["y_range"])
        for curve in extractions[panel_id]["curves"]:
            x, y = with_gaps(curve["points"])
            ax.plot(x, y, color=curve["plot_color"], linewidth=1.5, label=f"f = {curve['z']:g}")
        ax.set_xlim(0, 1); ax.legend(frameon=False, fontsize=10)
        save(fig, out, f"paper-digitized-{panel_id}")
    return exported


def lookup_errors(data, out):
    profiles = data["heldout"]["whole_profile"]
    fields = [("T_K", "Temperature RMS (K)"),
              ("omega_CO2_plus_CO_kg_m3_s", "Progress-source RMS\n(kg m$^{-3}$ s$^{-1}$)"),
              ("Qdot_formation_298K_W_m3", "Formation-Qdot RMS\n(W m$^{-3}$)")]
    fig, axes = plt.subplots(3, 1, figsize=(8, 8.4), sharex=True)
    fig.subplots_adjust(left=.18, right=.97, top=.92, bottom=.13, hspace=.2)
    for ax, (field, label) in zip(axes, fields):
        ax.plot(range(1, len(profiles) + 1), [p["fields"][field]["rms_absolute_error"] for p in profiles.values()],
                color="#c2512f", marker="o")
        ax.set(ylabel=label, yscale="log")
        ax.grid(alpha=.2)
    axes[0].set_title("Whole held-out profiles | table interpolation errors")
    axes[-1].set(xlabel="Held-out profile index (in receipt order)", xticks=range(1, len(profiles) + 1))
    fig.text(.18, .025, "Large source errors remain; source cross-check success does not validate interpolation.", fontsize=10)
    save(fig, out, "heldout-errors")
