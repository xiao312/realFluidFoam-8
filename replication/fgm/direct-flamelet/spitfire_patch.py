"""Apply one hash-qualified interior-node indexing correction to a fresh source copy."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from common import sha256, write_json

UPSTREAM = "735711dc4a426cc7504747d732f2e7fcc3db2c23"
RELATIVE = "src/spitfire/griffon/src/flamelet_kernels.cpp"
ORIGINAL_SHA256 = "d5c78ee852072de9d6bfd5ee5130b33d3bb74ab5900cea665fc8753c0c7dbee0"
PATCHED_SHA256 = "0f918901c5867645e279c82474fa2a58d7e4ed480bf3ec0e7cc46d54ed311c4f"
PATCH_ID = "flamelet-interior-chi-index-v1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True).strip()
    path = args.checkout / RELATIVE
    if revision != UPSTREAM or sha256(path) != ORIGINAL_SHA256:
        raise ValueError("Upstream revision or original kernel hash differs; no source changed")
    changes = subprocess.check_output(["git", "-C", str(args.checkout), "diff", "--name-only", "HEAD"], text=True).splitlines()
    if changes:
        raise ValueError(f"Tracked source changes already present: {changes}; use a fresh qualified copy")
    original = path.read_bytes()
    if original.count(b"chi[i]") != 8:
        raise ValueError("Expected exactly eight interior energy chi accesses")
    corrected = original.replace(b"chi[i]", b"chi[i + 1]")
    if hashlib.sha256(corrected).hexdigest() != PATCHED_SHA256:
        raise ValueError("Generated correction differs from the qualified patched kernel")
    result = {"schema": "spitfire-source-patch/v1", "patch_id": PATCH_ID,
              "upstream_revision": UPSTREAM, "relative_path": RELATIVE,
              "original_sha256": ORIGINAL_SHA256,
              "patched_sha256": hashlib.sha256(corrected).hexdigest(),
              "replacements": 8, "kinetics_changed": False,
              "scope": "Full-grid chi index at interior i+1 in energy RHS/reference and existing approximate Jacobian",
              "script_sha256": sha256(__file__), "applied": bool(args.apply)}
    if args.apply:
        if args.receipt is None or args.receipt.exists():
            raise ValueError("--receipt must be a new path; no source changed")
        path.write_bytes(corrected)
        if sha256(path) != result["patched_sha256"]:
            raise ValueError("Written kernel hash differs")
        write_json(args.receipt, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
