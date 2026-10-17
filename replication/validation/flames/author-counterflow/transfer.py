"""Check author-case endpoints and transfer internal primitive fields between mechanisms."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def latest(case):
    times = []
    for path in case.iterdir():
        if path.is_dir():
            try:
                value = float(path.name)
            except ValueError:
                continue
            if value > 0:
                times.append((value, path))
    if not times:
        raise ValueError("No positive solution time")
    return max(times)


def internal(path):
    text = path.read_text()
    match = re.search(r"\binternalField\s+(?:uniform\s+[^;]+|nonuniform\s+List<\w+>\s+\d+\s*\(.*?\))\s*;", text, re.S)
    if not match:
        raise ValueError("Unsupported field: " + str(path))
    return text, match


def scalars(path, count):
    _, match = internal(path)
    body = match.group()
    if "nonuniform" in body:
        values = list(map(float, body.split("(", 1)[1].rsplit(")", 1)[0].split()))
    else:
        values = [float(body.split()[2].rstrip(";"))] * count
    if len(values) != count or not all(math.isfinite(v) for v in values):
        raise ValueError("Invalid scalar field: " + str(path))
    return values


def check(case):
    meta = json.loads((case / "author-case.json").read_text())
    time, endpoint = latest(case)
    if abs(time - meta["end_time_s"]) > 1e-10:
        raise ValueError("Endpoint does not reach configured end time")
    count = meta["cells"]
    ranges = {}
    for name in ["T", "p", "rho"]:
        values = scalars(endpoint / name, count)
        if min(values) <= 0:
            raise ValueError("Nonpositive " + name)
        ranges[name] = [min(values), max(values)]
    _, velocity = internal(endpoint / "U")
    vectors = re.findall(r"\(([^()]*)\)", velocity.group())
    expected_vectors = count if "nonuniform" in velocity.group() else 1
    if len(vectors) != expected_vectors:
        raise ValueError("Invalid velocity field size")
    for vector in vectors:
        values = list(map(float, vector.split()))
        if len(values) != 3 or not all(math.isfinite(v) for v in values):
            raise ValueError("Invalid velocity vector")
    sums = [0.] * count
    for name in meta["species"]:
        values = scalars(endpoint / name, count)
        if min(values) < -1e-12 or max(values) > 1 + 1e-8:
            raise ValueError("Mass fraction out of bounds: " + name)
        sums = [a+b for a, b in zip(sums, values)]
    error = max(abs(s-1) for s in sums)
    if error > 1e-8:
        raise ValueError("Mass fractions do not sum to one")
    return endpoint, dict(time_s=time, fields=ranges, species_sum_error=error,
                         qualification="finite endpoint only; convergence not established")


def mesh_body(path):
    # OpenFOAM headers may contain different case locations; compare the lists.
    text = path.read_text()
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S).split("}", 1)[1].strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "plan", "apply"])
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path, nargs="?")
    args = parser.parse_args()
    endpoint, receipt = check(args.source)
    if args.action != "check":
        if args.target is None or args.source.resolve() == args.target.resolve():
            raise ValueError("Distinct target required")
        for name in ["points", "faces", "owner", "neighbour", "boundary"]:
            if mesh_body(args.source / "constant/polyMesh" / name) != mesh_body(args.target / "constant/polyMesh" / name):
                raise ValueError("Mesh mismatch: " + name)
        receipt["source_field_hashes"] = {}
        for name in ["T", "p", "U", "CH4", "O2", "CO2", "H2O", "N2"]:
            src = endpoint / name
            _, source_match = internal(src)
            target = args.target / "0" / name
            text, target_match = internal(target)
            # Resolve original uniform boundary aliases before replacing the
            # internal field with a nonuniform solution (not patch-sized data).
            original_value = re.sub(r"^internalField\s+", "", target_match.group()).rstrip("; ")
            if not original_value.startswith("uniform "):
                raise ValueError("Transfer requires fresh uniform target fields")
            text = text.replace("$internalField", original_value)
            receipt["source_field_hashes"][name] = hashlib.sha256(src.read_bytes()).hexdigest()
            if args.action == "apply":
                target.write_text(text[:target_match.start()] + source_match.group() + text[target_match.end():], encoding="utf-8")
        if args.action == "apply":
            (args.target / "transfer.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
