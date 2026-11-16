"""Read case-sensitive species archives without H/h filesystem collisions."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile

import numpy as np


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def scalar(raw, name, count):
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", raw.decode(), flags=re.S)
    obj = re.search(r'\bobject\s+("[^"]+"|[^;\s]+)\s*;', text)
    if not obj or obj[1].strip('"') != name or not re.search(r"class\s+volScalarField\s*;", text):
        raise ValueError(f"Object-name/type mismatch for {name}; possible case collision")
    many = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;", text, re.S)
    if many:
        values = np.fromstring(many[2], sep=" ")
        if len(values) != count or int(many[1]) != count:
            raise ValueError(f"Wrong cell count for {name}")
    else:
        one = re.search(r"internalField\s+uniform\s+([^;]+);", text)
        if not one:
            raise ValueError(f"Missing scalar values for {name}")
        values = np.full(count, float(one[1]))
    if not np.isfinite(values).all():
        raise ValueError(f"Nonfinite {name}")
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--wedge-degrees", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not 0 < args.wedge_degrees < 30:
        raise ValueError("Explicit small wedge angle required")
    receipt = json.loads(args.collection.read_text())
    if receipt.get("CFDStartTime_s") != 0 or receipt.get("isTimeMean") is not False:
        raise ValueError("Original-zero instantaneous receipt required")
    archive_path = Path(receipt["archivePath"])
    if digest(archive_path.read_bytes()) != receipt["archiveSha256"]:
        raise ValueError("Changed case-sensitive archive")
    root = Path(receipt["localRoot"]).resolve()
    for name, expected in receipt["inputHashes"].items():
        file = (root / name).resolve()
        if not file.is_relative_to(root) or digest(file.read_bytes()) != expected:
            raise ValueError(f"Changed/escaping extracted input: {name}")
    spec = importlib.util.spec_from_file_location("field_renderer", Path(__file__).with_name("render-case.py"))
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    point_file = root / "cases" / receipt["case"] / "constant/polyMesh/points"
    point_key = str(point_file.relative_to(root)).replace("\\", "/")
    if point_key not in receipt["inputHashes"]:
        raise ValueError("Mesh points are not hash-bound")
    point_text = renderer.list_body(point_file)[1]
    xyz = np.array([list(map(float, m[1].split())) for m in re.finditer(r"\(([^()]*)\)", point_text)])
    angles = np.rad2deg(np.arctan2(xyz[:, 2], xyz[:, 1]))
    observed_angle = float(angles.max() - angles.min())
    if abs(observed_angle - args.wedge_degrees) > 1e-6:
        raise ValueError("Requested wedge angle differs from actual mesh")
    polygons, _, temperatures = renderer.load_cells(receipt, root)
    volumes = []
    for polygon in polygons:
        p = polygon * .001
        q = np.roll(p, -1, axis=0)
        cross = p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1]
        volumes.append(np.sin(np.deg2rad(args.wedge_degrees)) * np.sum((p[:, 1] + q[:, 1]) * cross) / 6)
    volumes = np.array(volumes)
    if not (volumes > 0).all():
        raise ValueError("Nonpositive cell volume")
    metadata_raw = args.metadata.read_bytes()
    metadata = json.loads(metadata_raw)
    species = metadata["species"]
    names = [s["name"] for s in species]
    with tarfile.open(archive_path, "r:gz") as archive:
        if len(archive.getnames()) != len(set(archive.getnames())):
            raise ValueError("Repeated archive member")

        def member(name):
            raw = archive.extractfile(name).read()
            if digest(raw) != receipt["rawMemberHashes"][name]:
                raise ValueError(f"Changed/unbound archive member: {name}")
            return raw

        prefix = "cases/" + receipt["case"]
        manifest = json.loads(member(prefix + "/direct-g2-input.json"))
        if manifest["inputHashes"]["metadata"] != digest(metadata_raw):
            raise ValueError("Phase metadata differs from actual case input")
        count = manifest["mesh"]["cellCount"]
        fields = {name: np.full(count, np.nan) for name in [*names, "rho", "Z", "c"]}
        seen = np.zeros(count, dtype=int)
        for rank in range(receipt["ranks"]):
            part = prefix + f"/processor{rank}"
            ids = renderer.labels(root / part / "constant/polyMesh/cellProcAddressing")
            seen[ids] += 1
            for name, values in fields.items():
                values[ids] = scalar(member(part + "/" + receipt["timeDirectory"] + "/" + name), name, len(ids))
        if len(volumes) != count or not (seen == 1).all() or any(not np.isfinite(v).all() for v in fields.values()):
            raise ValueError("Species must map each actual global cell exactly once")
    # Derive elemental masses by exact molecular identities, not a fitted curve.
    weights = {}
    elements = set().union(*(s["composition"] for s in species))
    for _ in range(len(elements) + 1):
        for state in species:
            unknown = set(state["composition"]) - set(weights)
            if len(unknown) == 1:
                element = unknown.pop()
                known = sum(weights[e] * n for e, n in state["composition"].items() if e in weights)
                weights[element] = (state["molecularWeight_kg_kmol"] - known) / state["composition"][element]
    if set(weights) != elements or any(v <= 0 for v in weights.values()):
        raise ValueError("Molecular identities do not determine positive elemental masses")
    if max(abs(sum(weights[e] * n for e, n in s["composition"].items()) - s["molecularWeight_kg_kmol"]) for s in species) > 1e-8:
        raise ValueError("Inconsistent mechanism molecular weights")
    mass = fields["rho"] * volumes
    if not (mass > 0).all():
        raise ValueError("Nonpositive transported cell mass")
    element_reports = []
    for element in sorted(elements):
        coefficients = {s["name"]: s["composition"].get(element, 0) * weights[element] / s["molecularWeight_kg_kmol"] for s in species}
        actual = sum(coefficients[n] * fields[n] for n in names)
        expected = fields["Z"] * coefficients["CH4"] + (1 - fields["Z"]) * coefficients["O2"]
        delta = actual - expected
        element_reports.append(dict(element=element,maximumAbsolute=float(abs(delta).max()),
            massWeightedMeanAbsolute=float(np.sum(mass * abs(delta)) / mass.sum()),
            signedIntegral_kg=float(np.sum(mass * delta)),worstGlobalCell=int(abs(delta).argmax())))
    sum_y = sum(fields[n] for n in names)
    progress_delta = fields["CO"] + fields["CO2"] - fields["c"]
    report = dict(schema="g2-species-element-progress-audit/v1",sourceJob=receipt["sourceJob"],
        time_s=receipt["time_s"],cells=count,CFDStartTime_s=0,isTimeMean=False,
        wedgeDegrees=observed_angle,volume_m3=float(volumes.sum()),transportedMass_kg=float(mass.sum()),
        maximumMassSumError=float(abs(sum_y - 1).max()),
        minimumSpeciesMassFraction=float(min(fields[n].min() for n in names)),
        maximumProgressCompositionError=float(abs(progress_delta).max()),
        elements=element_reports,atomicMasses_kg_kmol=weights,speciesNormalized=False,
        archiveSha256=receipt["archiveSha256"],metadataSha256=digest(metadata_raw),
        collectionSha256=digest(args.collection.read_bytes()),codeSha256=digest(Path(__file__).read_bytes()),
        caseSensitiveArchiveRead=True,conflictingMembersExtracted=False,
        acceptanceThresholdIntroduced=False,scientificAcceptance=False,readOnly=not args.apply)
    if args.apply:
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
