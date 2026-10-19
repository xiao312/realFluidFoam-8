"""Copy explicit completed checkpoints; never continue or mutate the donor."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

DONOR_JOB = "124797651"
TIMES = ["0.00095", "0.00096", "0.00097", "0.00098", "0.00099", "0.001"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(action, root, output):
    root = root.resolve(strict=True)
    output = output.resolve()
    donor = root / "jobs" / DONOR_JOB / "case"
    for path in (output, donor.resolve(strict=True)):
        if root not in path.parents:
            raise ValueError("All paths must resolve inside the project root")
    target = output / "case"
    if target.exists():
        raise ValueError("Refusing existing case: " + str(target))
    if not (donor.parent / "result.txt").read_text().startswith("PASS:"):
        raise ValueError("Donor has no passed endpoint receipt")
    relative = [Path("system"), Path("constant")]
    for rank in range(4):
        relative.append(Path("processor" + str(rank)) / "constant")
        for time in TIMES:
            relative.append(Path("processor" + str(rank)) / time)
    files = []
    for rel in relative:
        directory = donor / rel
        if not directory.is_dir():
            raise ValueError("Missing input: " + str(directory))
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlink input requires explicit review: " + str(path))
            if path.is_file():
                files.append(path)
    plan = {"donor_job": DONOR_JOB, "donor": str(donor), "output": str(target),
            "times": TIMES, "files": len(files), "bytes": sum(p.stat().st_size for p in files),
            "operation": "copy and postprocess; no simulation advancement"}
    print(json.dumps(plan, indent=2))
    if action == "plan":
        return
    target.mkdir(parents=True)
    hashes = {}
    for source in files:
        rel = source.relative_to(donor)
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        original = digest(source)
        shutil.copy2(source, dest)
        if digest(dest) != original or digest(source) != original:
            raise ValueError("Input changed during copy: " + str(source))
        hashes[str(rel)] = original
    control = target / "system/controlDict"
    content = control.read_text()
    for key, value in (("startFrom", "startTime"), ("startTime", TIMES[0])):
        content, count = re.subn(r"\b" + key + r"\s+[^;]+;", key + " " + value + ";", content)
        if count != 1:
            raise ValueError("Expected exactly one " + key)
    # These cases have no function objects. Fail instead of running hidden actions.
    if re.search(r"\bfunctions\b", content):
        raise ValueError("Review function objects before diagnostic processing")
    control.write_text(content)
    (output / "checkpoint-inputs.json").write_text(json.dumps({**plan, "sha256": hashes,
        "modified_control_sha256": digest(control)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.action, args.root, args.output)
