#!/usr/bin/env python3
"""Sweep the SRK + Chung property model over Cavalieri et al. (2025) Fig. 1 conditions.

Pure O2 and CH4 at 56 bar, 100-400 K, on a 0.25 K grid.  Writes

  sweep.csv   one row per (species, temperature) with every model quantity
  sweep.json  the same curves in `forge-property-sweep-v1` form for render_figures.mjs,
              plus the declared sensitivity runs and the provenance of this module

Nothing is fitted and no residual is hidden: the published-figure comparison is a separate
step (`compare_reference.py`), so a weak residual cannot be absorbed by tuning here.

Run: python3 sweep_properties.py [--out-dir DIR]
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import srk_chung as sc

PRESSURE_PA = 56.0e5          # Cavalieri et al. (2025) Fig. 1 condition
T_MIN, T_MAX, T_STEP = 100.0, 400.0, 0.25
SENSITIVITY_STEP = 10.0

# Declared sensitivity: the acentric factors retained in this repository's mechanism file
# differ from the paper's Table 1, so the figure reports the Table 1 model and the sweep
# records how much that choice moves the curves.
REPO_OMEGA = {"O2": 0.025, "CH4": 0.011}

COLUMNS = [
    "species", "T_K", "pressure_Pa", "rho_kg_m3", "cp_kJ_kgK", "mu_Pas",
    "kappa_W_mK", "Z", "v_m3_mol", "h_kJ_mol", "cp_J_molK", "cv_J_molK",
    "ideal_cp_J_molK", "Y_chung", "srk_alpha", "n_stable_roots",
]


def grid(start, stop, step):
    count = int(round((stop - start) / step))
    return [start + index * step for index in range(count + 1)]


def evaluate(species_name, T, p=PRESSURE_PA, omega=None, a_coeff=sc.A_COEFF):
    species = sc.SPECIES[species_name]
    if omega is not None:
        species = dict(species, omega=omega)
    state = sc.thermo_state(species, T, p, a_coeff=a_coeff)
    transport = sc.chung_state(species, T, p, rho=state["rho"],
                              cp_ideal_value=state["cp_ideal"], a_coeff=a_coeff)
    molar_mass = species["molar_mass"]
    return {
        "species": species_name,
        "T_K": T,
        "pressure_Pa": p,
        "rho_kg_m3": state["rho"],
        "cp_kJ_kgK": state["cp"] / molar_mass / 1000.0,
        "mu_Pas": transport["mu"],
        "kappa_W_mK": transport["kappa"],
        "Z": state["Z"],
        "v_m3_mol": state["v"],
        "h_kJ_mol": state["h"] / 1000.0,
        "cp_J_molK": state["cp"],
        "cv_J_molK": state["cv"],
        "ideal_cp_J_molK": state["cp_ideal"],
        "Y_chung": transport["y"],
        "srk_alpha": state["a"] / (sc.A_COEFF * (sc.R * species["Tc"]) ** 2
                                   / species["pc"]),
        "n_stable_roots": state["n_stable_roots"],
    }


def sensitivity():
    """Max relative change from the two declared model ambiguities."""
    out = {}
    coarse = grid(T_MIN, T_MAX, SENSITIVITY_STEP)
    for name, species in sc.SPECIES.items():
        base = {T: evaluate(name, T) for T in coarse}
        printed = {T: evaluate(name, T, a_coeff=sc.A_COEFF_PRINTED) for T in coarse}
        repo = {T: evaluate(name, T, omega=REPO_OMEGA[name]) for T in coarse}
        out[name] = {
            "a_coeff_0.427_vs_0.42748": {
                key: max(abs(printed[T][key] - base[T][key]) / abs(base[T][key])
                         for T in coarse)
                for key in ("rho_kg_m3", "cp_kJ_kgK", "mu_Pas", "kappa_W_mK")},
            "acentric_factor_table1_vs_repo": {
                "table1": species["omega"], "repo": REPO_OMEGA[name],
                **{key: max(abs(repo[T][key] - base[T][key]) / abs(base[T][key])
                            for T in coarse)
                   for key in ("rho_kg_m3", "cp_kJ_kgK", "mu_Pas", "kappa_W_mK")}},
        }
        # The a-coefficient changes the pressure branch smoothly; record the worst point.
        worst = max(coarse, key=lambda T: abs(printed[T]["rho_kg_m3"] - base[T]["rho_kg_m3"])
                    / base[T]["rho_kg_m3"])
        out[name]["a_coeff_0.427_vs_0.42748"]["worst_rho_T_K"] = worst
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="out")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    temperatures = grid(T_MIN, T_MAX, T_STEP)
    rows = []
    for name in ("O2", "CH4"):
        for T in temperatures:
            rows.append(evaluate(name, T))

    with (out_dir / "sweep.csv").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(",".join(COLUMNS) + "\n")
        for row in rows:
            handle.write(",".join(
                ("%s" % row[key]) if isinstance(row[key], str)
                else ("%d" % row[key]) if key == "n_stable_roots"
                else ("%.10g" % row[key]) for key in COLUMNS) + "\n")

    properties = {"rho": {}, "cp": {}, "mu": {}, "kappa": {}}
    key_for = {"rho": "rho_kg_m3", "cp": "cp_kJ_kgK", "mu": "mu_Pas", "kappa": "kappa_W_mK"}
    scale = {"rho": 1.0, "cp": 1.0, "mu": 1e4, "kappa": 1.0}
    for fluid in ("o2", "ch4"):
        name = fluid.upper()
        for column, key in key_for.items():
            properties[column][fluid] = [
                [row["T_K"], row[key] * scale[column]] for row in rows if row["species"] == name]

    summary = {}
    for name in ("O2", "CH4"):
        subset = [row for row in rows if row["species"] == name]
        summary[name] = {
            key: {"min": min(row[key] for row in subset),
                  "max": max(row[key] for row in subset),
                  "at_min_K": min(subset, key=lambda row: row[key])["T_K"],
                  "at_max_K": max(subset, key=lambda row: row[key])["T_K"]}
            for key in ("rho_kg_m3", "cp_kJ_kgK", "mu_Pas", "kappa_W_mK", "Z", "Y_chung")}
        summary[name]["max_n_stable_roots"] = max(row["n_stable_roots"] for row in subset)
        summary[name]["max_Y_chung"] = max(row["Y_chung"] for row in subset)

    module = Path(__file__).resolve().parent / "srk_chung.py"
    sweep = {
        "schema": "forge-property-sweep-v1",
        "target": "cavalieri2025-fig-1",
        "model": "SRK (Graboski-Daubert alpha, Eq. 2/4) + Chung, Ajlan & Lee (1988) "
                 "dense-gas transport (Eqs. 9-12); NASA7 ideal-gas cp",
        "pressure_Pa": PRESSURE_PA,
        "temperature_K": [T_MIN, T_MAX],
        "temperature_step_K": T_STEP,
        "samples_per_fluid": len(temperatures),
        "model_parameters": {
            name: {
                "Tc_K": species["Tc"], "pc_Pa": species["pc"], "omega": species["omega"],
                "vc_cm3_mol": species["vc"] * 1e6,
                "molar_mass_kg_mol": species["molar_mass"],
                "alpha_coefficient": 0.48508 + 1.55171 * species["omega"]
                                     - 0.15613 * species["omega"] ** 2,
                "lj_sigma_angstrom": species["lj_sigma"] * 1e10,
                "lj_epsilon_over_k": species["lj_epsilon_k"],
            } for name, species in sc.SPECIES.items()},
        "model_constants": {
            "A_coefficient": sc.A_COEFF,
            "A_coefficient_printed_in_paper": sc.A_COEFF_PRINTED,
            "B_coefficient": sc.B_COEFF,
            "gas_constant_J_molK": sc.R,
            "chung_viscosity_A": list(sc._A0), "chung_viscosity_A_w": list(sc._A1),
            "chung_viscosity_A_mur4": list(sc._A2),
            "chung_viscosity_A_kappa": list(sc._A3),
            "chung_conductivity_B": list(sc._B0),
            "chung_conductivity_B_w": list(sc._B1),
            "chung_conductivity_B_mur4": list(sc._B2),
            "chung_conductivity_B_kappa": list(sc._B3),
        },
        "sensitivity": sensitivity(),
        "summary": summary,
        "provenance": {
            "module": module.name,
            "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
            "generated_by": Path(__file__).name,
            "python": "stdlib only",
        },
        "properties": properties,
    }
    (out_dir / "sweep.json").write_text(json.dumps(sweep, indent=2) + "\n", encoding="utf-8")

    print(f"sweep.csv: {len(rows)} rows ({len(temperatures)} per fluid)")
    for name in ("O2", "CH4"):
        info = summary[name]
        print(f"  {name}: rho {info['rho_kg_m3']['min']:.2f}..{info['rho_kg_m3']['max']:.2f} kg/m3, "
              f"cp {info['cp_kJ_kgK']['min']:.3f}..{info['cp_kJ_kgK']['max']:.3f} kJ/(kg K), "
              f"mu {info['mu_Pas']['max'] * 1e4:.3f}e-4 Pa s, "
              f"kappa {info['kappa_W_mK']['min']:.3f}..{info['kappa_W_mK']['max']:.3f} W/(m K), "
              f"max Y {info['max_Y_chung']:.3f}, max roots {info['max_n_stable_roots']}")
    print("sweep.json written")


if __name__ == "__main__":
    main()
