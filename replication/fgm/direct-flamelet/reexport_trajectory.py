"""Export every retained physical frame while preserving the original whole-frame holdouts."""
import argparse
import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from common import gas_and_streams, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--mechanism", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--environment-sha256", required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    receipt = json.loads((args.run / "receipt.json").read_text())
    original = json.loads((args.run / "family-manifest.json").read_text())
    if (sha256(args.run / "trajectory.npz") != receipt["artifacts"]["trajectory.npz"] or
            sha256(args.mechanism) != receipt["mechanism_sha256"] or
            sha256(args.run / "family-manifest.json") != receipt["artifacts"]["family-manifest.json"]):
        raise ValueError("Retained trajectory, family or mechanism identity mismatch")
    if not re.fullmatch("[0-9a-f]{40}", args.source_commit) or not re.fullmatch("[0-9a-f]{64}", args.environment_sha256):
        raise ValueError("Full source/environment identities required")
    raw = np.load(args.run / "trajectory.npz")
    holdouts = [int(member["id"].split("-")[-1]) for member in original["members"] if member["role"] == "held-out"]
    derivation = {"schema": "physical-trajectory-reexport/v1", "physics_source_commit": receipt["source_commit"],
        "source_commit": args.source_commit, "environment_sha256": args.environment_sha256,
        "trajectory_sha256": sha256(args.run / "trajectory.npz"),
        "input_receipt_sha256": sha256(args.run / "receipt.json"),
        "input_manifest_sha256": sha256(args.run / "family-manifest.json"),
        "physical_frames": len(raw["time_s"]), "fixed_heldout_indices": holdouts,
        "raw_physics_modified": False, "rates": "Evaluated at actual stored states, not interpolated source fields",
        "scientific_acceptance": False}
    if args.plan:
        print(json.dumps(derivation, indent=2))
        return
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new directory")
    import cantera as ct
    from spitfire import ChemicalMechanismSpec
    from transient_export import export_frames
    args.out.mkdir(parents=True)
    write_json(args.out / "derivation.json", derivation)
    derived = copy.deepcopy(receipt)
    derived["derivation"] = derivation
    parameters = SimpleNamespace(out=args.out, mechanism=args.mechanism,
        mechanism_sha256=receipt["mechanism_sha256"], source_commit=args.source_commit,
        environment_sha256=args.environment_sha256)
    gas, streams = gas_and_streams(ct, parameters, receipt["case"], derived)
    # Keep the physical-model description from the simulation, not Cantera's property evaluator.
    derived["models"] = copy.deepcopy(receipt["models"])
    settings = copy.deepcopy(receipt["integration"])
    settings.update(selected_frame_indices=list(range(len(raw["time_s"]))), heldout_frame_indices=holdouts)
    metrics = export_frames(ct, gas, ChemicalMechanismSpec(cantera_solution=gas), streams, receipt["case"],
        settings, derived, parameters, raw["Z"], raw["time_s"], raw["T_K"], raw["Y"])
    write_json(args.out / "diagnostics.json", metrics)
    manifest = json.loads((args.out / "family-manifest.json").read_text())
    groups = {}
    for member in manifest["members"]:
        groups.setdefault(sha256(args.out / member["directory"] / "profile.csv"), []).append(member)
    retained, aliases = [], []
    for digest, group in groups.items():
        held = [member for member in group if member["role"] == "held-out"]
        chosen = held[0] if held else group[0]
        if len(held) > 1:
            raise ValueError("Original held-out frames are physically identical; retain evidence and reconsider the holdout design")
        retained.append(chosen)
        for other in group:
            if other is not chosen:
                aliases.append({"excluded": other["id"], "alias_of": chosen["id"], "profile_sha256": digest,
                                "reason": "Exact physical profile duplicate excluded; held-out copies cannot enter training"})
    manifest["members"] = sorted(retained, key=lambda item: item["id"])
    manifest["exact_profile_aliases"] = aliases
    manifest["holdout_scope"] = "Original entire-frame holdouts preserved; identical training copies excluded; all additional distinct actual frames are training"
    write_json(args.out / "family-manifest.json", manifest)
    derivation.update(exported_frames=metrics["selected_frames"], distinct_profiles=len(retained), aliases=aliases,
        artifacts={name: sha256(args.out / name) for name in ("family-manifest.json", "diagnostics.json", "phase-metadata.json")})
    write_json(args.out / "derivation.json", derivation)
    print(json.dumps({key: value for key, value in derivation.items() if key != "aliases"}, indent=2))


if __name__ == "__main__":
    main()
