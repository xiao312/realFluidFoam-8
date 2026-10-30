"""Reconstruct the discrete enthalpy balance of a retained warm Spitfire trajectory."""
import argparse
import json
from pathlib import Path
from statistics import NormalDist
import numpy as np
from common import sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--mechanism", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    receipt = json.loads((args.run / "receipt.json").read_text())
    if sha256(args.run / "trajectory.npz") != receipt["artifacts"]["trajectory.npz"] or sha256(args.mechanism) != receipt["mechanism_sha256"]:
        raise ValueError("Input hash mismatch")
    if args.plan:
        print(json.dumps({"run": str(args.run), "input_verified": True, "task": "discrete enthalpy audit"}))
        return
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new JSON path")
    import cantera as ct
    gas = ct.Solution(str(args.mechanism))
    raw = np.load(args.run / "trajectory.npz")
    t, z, temperature, species = raw["time_s"], raw["Z"], raw["T_K"], raw["Y"]
    states = ct.SolutionArray(gas, temperature.shape)
    states.TPY = temperature, float(raw["pressure_pa"]), species
    enthalpy = states.enthalpy_mass
    cp = states.cp_mass
    h_species = states.partial_molar_enthalpies / gas.molecular_weights
    cp_species = states.partial_molar_cp / gas.molecular_weights
    case = receipt["case"]
    gas.TPX = case["fuel"]["temperature_k"], case["pressure_pa"], case["fuel"]["mole_fractions"]
    hf = gas.enthalpy_mass
    gas.TPX = case["oxidizer"]["temperature_k"], case["pressure_pa"], case["oxidizer"]["mole_fractions"]
    ho = gas.enthalpy_mass
    zst = 1 / (1 + gas.stoich_air_fuel_ratio(case["fuel"]["mole_fractions"], case["oxidizer"]["mole_fractions"], basis="mole"))
    normal = NormalDist()
    chi = np.zeros(len(z))
    chi[1:-1] = receipt["integration"]["chi_st_s_inverse"] * np.exp(np.array([-normal.inv_cdf(float(value)) ** 2 for value in z[1:-1]]) + normal.inv_cdf(zst) ** 2)
    dl, dr = np.diff(z)[:-1], np.diff(z)[1:]

    def gradient(values):
        denominator = (dl + dr).reshape((1, -1) + (1,) * (values.ndim - 2))
        return (values[:, 2:] - values[:, :-2]) / denominator

    def second(values):
        shape = (1, -1) + (1,) * (values.ndim - 2)
        left, right = dl.reshape(shape), dr.reshape(shape)
        return 2 * ((values[:, 2:] - values[:, 1:-1]) / right - (values[:, 1:-1] - values[:, :-2]) / left) / (left + right)

    temperature_gradient = gradient(temperature)
    composition_heat_gradient = np.sum(cp_species[:, 1:-1] * gradient(species), axis=2)
    correction = .5 * temperature_gradient * (gradient(cp) + composition_heat_gradient)
    base = .5 * chi[1:-1] * (cp[:, 1:-1] * second(temperature) + np.sum(h_species[:, 1:-1] * second(species), axis=2))
    upstream_hdot = base + chi[:-2] * correction
    corrected_hdot = base + chi[1:-1] * correction
    conservative_hdot = .5 * chi[1:-1] * second(enthalpy)
    measured_hdot = np.gradient(enthalpy, t, axis=0, edge_order=2)[:, 1:-1]
    error = enthalpy - ((1 - z) * ho + z * hf)
    worst = np.unravel_index(np.argmax(abs(error)), error.shape)
    rms = lambda value: float(np.sqrt(np.mean(value ** 2)))
    # Compare inner accepted times to avoid one-sided temporal differences at endpoints.
    trimmed = slice(2, -2)
    metrics = {"schema": "discrete-enthalpy-audit/v1", "trajectory_sha256": sha256(args.run / "trajectory.npz"),
        "mechanism_sha256": sha256(args.mechanism), "grid_points": len(z), "time_frames": len(t),
        "upstream_revision": receipt["integration"]["upstream_revision"],
        "reconstruction_scope": "Warm unity-Lewis adiabatic discrete diffusion; chemical enthalpy terms cancel; not a new physical solve",
        "observed_enthalpy_error_max_J_kg": float(np.max(abs(error))),
        "worst": {"time_s": float(t[worst[0]]), "Z": float(z[worst[1]]), "T_K": float(temperature[worst]), "signed_error_J_kg": float(error[worst])},
        "actual_dhdt_rms_J_kg_s": rms(measured_hdot[trimmed]),
        "upstream_reconstruction_relative_rms_error": rms(upstream_hdot[trimmed] - measured_hdot[trimmed]) / rms(measured_hdot[trimmed]),
        "corrected_index_reconstruction_relative_rms_error": rms(corrected_hdot[trimmed] - measured_hdot[trimmed]) / rms(measured_hdot[trimmed]),
        "upstream_discrete_chain_error_rms_J_kg_s": rms(upstream_hdot - conservative_hdot),
        "corrected_index_discrete_chain_error_rms_J_kg_s": rms(corrected_hdot - conservative_hdot),
        "initial_upstream_max_hdot_J_kg_s": float(np.max(abs(upstream_hdot[0]))),
        "initial_corrected_index_max_hdot_J_kg_s": float(np.max(abs(corrected_hdot[0]))),
        "time_series": [{"time_s": float(t[i]), "max_enthalpy_error_J_kg": float(np.max(abs(error[i]))),
                         "upstream_chain_error_rms_J_kg_s": rms(upstream_hdot[i] - conservative_hdot[i]),
                         "corrected_index_chain_error_rms_J_kg_s": rms(corrected_hdot[i] - conservative_hdot[i])} for i in range(len(t))]}
    write_json(args.out, metrics)
    print(json.dumps({key: value for key, value in metrics.items() if key != "time_series"}, indent=2))


if __name__ == "__main__":
    main()
