"""Explicitly apply the frozen cold candidate only to an isolated energy-corrected source."""
import argparse
import json
from pathlib import Path
import subprocess
from common import sha256, write_json
from spitfire_patch import UPSTREAM, RELATIVE, PATCHED_SHA256
from prepare_cold_patch import CANDIDATE_PATCH_SHA256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--energy-patch-receipt", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    patch = args.candidate / "candidate.patch"
    manifest = json.loads((args.candidate / "manifest.json").read_text())
    energy = json.loads(args.energy_patch_receipt.read_text())
    head = subprocess.check_output(["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True).strip()
    if (head != UPSTREAM or manifest.get("upstream_revision") != UPSTREAM or
            manifest.get("patch_sha256") != CANDIDATE_PATCH_SHA256 or sha256(patch) != CANDIDATE_PATCH_SHA256 or
            energy.get("applied") is not True or energy.get("patched_sha256") != PATCHED_SHA256 or
            sha256(args.checkout / RELATIVE) != PATCHED_SHA256):
        raise ValueError("Exact candidate/upstream/applied energy patch identity required")
    for relative, hashes in manifest["files"].items():
        path = args.checkout / relative
        if hashes["original_sha256"] is None:
            if path.exists():
                raise ValueError(f"Candidate addition already exists: {relative}")
        elif sha256(path) != hashes["original_sha256"]:
            raise ValueError(f"Original source differs: {relative}")
    changed = subprocess.check_output(["git", "-C", str(args.checkout), "diff", "--name-only", "HEAD"], text=True).splitlines()
    if changed != [RELATIVE]:
        raise ValueError(f"Only the qualified energy patch may precede this candidate: {changed}")
    subprocess.run(["git", "-C", str(args.checkout), "apply", "--check", str(patch.resolve())], check=True)
    receipt = {"schema": "spitfire-cold-patch/v1", "upstream_revision": UPSTREAM,
        "patch_sha256": CANDIDATE_PATCH_SHA256, "candidate_manifest": manifest,
        "candidate_manifest_sha256": sha256(args.candidate / "manifest.json"),
        "energy_patch_receipt_sha256": sha256(args.energy_patch_receipt),
        "applied": bool(args.apply), "scientific_acceptance": False, "runtime_qualified": False}
    if args.apply:
        if args.receipt is None or args.receipt.exists():
            raise ValueError("--receipt must be a new path; no mutation performed")
        subprocess.run(["git", "-C", str(args.checkout), "apply", str(patch.resolve())], check=True)
        receipt["applied_files"] = {relative: sha256(args.checkout / relative) for relative in manifest["files"]}
        for relative, digest in receipt["applied_files"].items():
            if digest != manifest["files"][relative]["candidate_sha256"]:
                raise ValueError(f"Applied source hash differs: {relative}")
        write_json(args.receipt, receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
