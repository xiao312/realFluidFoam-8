"""Plot the SRK covolume consistency check; this is not a paper-figure replica."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "apply"))
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    record = json.loads(args.audit.read_text())
    if args.output.exists():
        raise ValueError("Output exists; choose a new image path")
    print(json.dumps(dict(output=str(args.output), rows=len(record["comparison"]))))
    if args.action == "plan":
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    figure, axes = plt.subplots(1, 2, figsize=(9.2, 4.5), sharex=True)
    for fuel, ax in zip(("H2", "CH4"), axes):
        rows = [r for r in record["comparison"] if r["fuel"] == fuel]
        phi = [r["phi"] for r in rows]
        implied = [r["implied_b_cm3_mol"] for r in rows]
        # Conservative propagated bounds from the assigned T/P reading tolerances.
        uncertainty = [r["implied_b_cm3_mol"] * (.1/r["Tc_K"] + .05/r["Pc_atm"]) for r in rows]
        ax.axhspan(rows[0]["minimum_species_b_cm3_mol"], rows[0]["maximum_species_b_cm3_mol"],
                   color=".92", label="Range of pure-species b values")
        ax.plot(phi, [r["computed_b_cm3_mol"] for r in rows], color="#087f5b", lw=1.5,
                marker="o", ms=3, label="Our mole-weighted SRK b")
        ax.errorbar(phi, implied, yerr=uncertainty, color="#ac3150", lw=1.3, marker="s", ms=3,
                    capsize=2, label="b implied by paper Tc/Pc")
        ax.set(title=fuel + "/air", xlabel="Equivalence ratio", ylabel="Molar covolume b (cm³/mol)")
        ax.set_xlim(.55, 1.95)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8, loc="best")
    figure.suptitle("Liang Figure 2: do temperature and pressure imply the stated SRK mixing rule?", fontsize=12)
    figure.text(.06, .02, "Inferred b = 0.08664035 R Tc/Pc. Paper curves are digitized; no physical coefficients were fitted.\n"
                "Shading bounds every normalized mixture of the pinned fuel, O₂ and N₂ species data.", fontsize=8)
    figure.tight_layout(rect=(0, .10, 1, .95))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=200)
    plt.close(figure)


if __name__ == "__main__":
    main()
