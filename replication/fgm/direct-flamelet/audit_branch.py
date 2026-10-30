"""Replay table branch construction from retained physical states; no new flame solve."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
from common import sha256, write_json
from table import build
from table_branch import POLICY
from table_io import heldout_report
from table_projection import project
from endpoint_audit import audit as audit_endpoints
from table_endpoint import POLICY as ZERO_ENDPOINT_POLICY, close as close_zero_endpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--mechanism", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--z-points", type=int, default=201)
    parser.add_argument("--eta-points", type=int, default=41)
    parser.add_argument("--zero-endpoint-policy", choices=[ZERO_ENDPOINT_POLICY])
    args = parser.parse_args()
    if args.z_points < 3 or args.eta_points < 2:
        parser.error("invalid table grid")
    receipt = json.loads((args.run / "receipt.json").read_text())
    if (sha256(args.run / "trajectory.npz") != receipt["artifacts"]["trajectory.npz"] or
            sha256(args.mechanism) != receipt["mechanism_sha256"]):
        raise ValueError("Retained trajectory/mechanism identity differs")
    if args.plan:
        print(json.dumps({"trajectory_sha256": receipt["artifacts"]["trajectory.npz"], "purpose": __doc__}))
        return
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new directory")
    import cantera as ct
    if ct.__version__ != "3.2.0":
        raise ValueError("Pinned Cantera3.2 required")
    gas = ct.Solution(str(args.mechanism))
    raw = np.load(args.run / "trajectory.npz")
    z, t, y = raw["Z"], raw["time_s"], raw["Y"]
    progress_indices = [gas.species_index(name) for name in ("CO2", "CO")]
    progress = y[:, :, progress_indices].sum(axis=2)
    case = receipt["case"]
    zst = 1 / (1 + gas.stoich_air_fuel_ratio(case["fuel"]["mole_fractions"], case["oxidizer"]["mole_fractions"], basis="mole"))
    progress_st = np.array([np.interp(zst, z, row) for row in progress])
    targets = np.linspace(float(np.min(progress_st)), float(np.max(progress_st)), receipt["integration"]["max_export_frames"])
    selected = sorted({0, len(t) - 1, *[int(np.argmin(abs(progress_st - value))) for value in targets]})
    gas.TP = 298.15, 101325.0
    formation_h = gas.partial_molar_enthalpies / gas.molecular_weights
    states = ct.SolutionArray(gas, (len(selected), len(z)))
    states.TPY = raw["T_K"][selected], case["pressure_pa"], y[selected]
    source = states.net_production_rates * gas.molecular_weights
    fields = np.concatenate([raw["T_K"][selected, :, None], states.density[:, :, None], progress[selected, :, None],
        source[:, :, progress_indices].sum(axis=2)[:, :, None], (-np.sum(source * formation_h, axis=2))[:, :, None], y[selected]], axis=2)
    columns = ["T_K", "rho_kg_m3", "Y_CO2_plus_CO", "omega_CO2_plus_CO_kg_m3_s", "Qdot_formation_298K_W_m3"] + ["Y_" + name for name in gas.species_names]
    keep = np.ones(len(z), dtype=bool)
    withheld = np.arange(5, len(z) - 1, 5)
    keep[withheld] = False
    members = []
    for n, index in enumerate(selected):
        entry = copy.deepcopy(receipt)
        entry.update(status="transient_snapshot", physical_time_s=float(t[index]))
        held = n % 5 == 4 and index != len(t) - 1
        members.append({"id": f"frame-{index:06d}", "receipt": entry, "role": "held-out" if held else "training", "columns": columns,
            "z": z, "values": fields[n], "train_z": z if held else z[keep],
            "train_values": fields[n] if held else fields[n, keep],
            "spatial_holdout_z": z[withheld], "spatial_holdout_values": fields[n, withheld]})
    training = [member for member in members if member["role"] == "training"]
    report = {"schema": "actual-branch-replay/v1", "trajectory_sha256": receipt["artifacts"]["trajectory.npz"],
        "physics_source_commit": receipt["source_commit"], "mechanism_sha256": sha256(args.mechanism),
        "postprocessing_cantera_version": ct.__version__, "raw_physics_modified": False,
        "scope": "Recomputed state diagnostics from actual T/Y; not original CSV qualification or physical rerun", "scientific_acceptance": False}
    args.out.mkdir(parents=True)
    try:
        build(training, np.linspace(0, 1, 201), np.linspace(0, 1, 41))
        report["original_policy"] = "built"
    except ValueError as error:
        report["original_policy"] = str(error)
    write_json(args.out / "receipt.json", report)
    model = build(training, np.linspace(0, 1, args.z_points), np.linspace(0, 1, args.eta_points), POLICY)
    metadata = json.loads((args.run / "phase-metadata.json").read_text())
    projection = project(model, metadata)
    endpoint_projection = {"policy": None, "applied_to_new_derivation": False}
    if args.zero_endpoint_policy:
        endpoint_projection = close_zero_endpoint(ct, gas, model, case["pressure_pa"])
        write_json(args.out / "zero-endpoint-projection.json", endpoint_projection)
        if not endpoint_projection["within_numerical_bounds"]:
            raise ValueError("Endpoint correction exceeds numerical bounds; audit retained")
    endpoints = audit_endpoints(ct, gas, model, case["pressure_pa"])
    peaks = np.max(abs(fields), axis=(0, 1))
    whole = {member["id"]: heldout_report(model, member["z"], member["values"], peaks, member["receipt"]["physical_time_s"])
             for member in members if member["role"] == "held-out"}
    report.update(branch_policy=POLICY, branch_build="built_not_accepted", grid=[args.z_points,args.eta_points], training_count=len(training), heldout_frames=len(whole),
        evaluated_holdout_points=sum(row["evaluated"] for row in whole.values()), attempted_holdout_points=sum(row["attempted"] for row in whole.values()),
        early_branch_refusals=sum(point["reason"] == "outside_selected_extinction_branch" for row in whole.values() for point in row["rejected_points"]),
        tail_excluded_states=sum(len(row["tail_exclusions"]) for row in model["branch_selection"]))
    write_json(args.out / "branch-selection.json", {"rows": model["branch_selection"]})
    write_json(args.out / "heldout.json", {"whole_profile": whole})
    write_json(args.out / "composition-projection.json", projection)
    write_json(args.out / "endpoint-audit.json", endpoints)
    write_json(args.out / "zero-endpoint-projection.json", endpoint_projection)
    report["zeroEndpointPolicy"] = args.zero_endpoint_policy
    report["artifacts"] = {name: sha256(args.out / name) for name in ("branch-selection.json", "heldout.json", "composition-projection.json", "endpoint-audit.json", "zero-endpoint-projection.json")}
    write_json(args.out / "receipt.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
