"""Render exact retained finite-volume temperatures; never advances CFD."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def foam_text(file):
    text = file.read_text()
    if not re.search(r"format\s+ascii\s*;", text):
        raise ValueError(f"Only retained ASCII fields are supported: {file}")
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def list_body(file):
    text = foam_text(file)
    match = re.search(r"\n\s*(\d+)\s*\n\(", text)
    if not match:
        raise ValueError(f"Missing counted list: {file}")
    return int(match[1]), text[match.end():text.rfind(")")]


def labels(file):
    count, body = list_body(file)
    result = np.fromstring(body, sep=" ", dtype=int)
    if len(result) != count:
        raise ValueError(f"Wrong label count: {file}")
    return result


def temperature(file, count):
    text = foam_text(file)
    match = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;", text, re.S)
    if match:
        result = np.fromstring(match[2], sep=" ")
        if len(result) != int(match[1]) or len(result) != count:
            raise ValueError(f"Wrong cell count: {file}")
    else:
        match = re.search(r"internalField\s+uniform\s+([^;]+);", text)
        if not match:
            raise ValueError(f"Missing internal temperature: {file}")
        result = np.full(count, float(match[1]))
    if not np.isfinite(result).all() or not (result > 0).all():
        raise ValueError(f"Nonfinite/nonpositive retained temperature: {file}")
    return result


def load_cells(receipt, base):
    root = base / "cases" / receipt["case"]
    mesh = root / "constant/polyMesh"
    count, text = list_body(mesh / "points")
    points = np.array([[float(v) for v in row.split()] for row in re.findall(r"\(([^()]+)\)", text)])
    if points.shape != (count, 3):
        raise ValueError("Wrong mesh point count")
    count, text = list_body(mesh / "faces")
    faces = [list(map(int, match[1].split())) for match in re.finditer(r"\d+\(([^()]*)\)", text)]
    owner, neighbour = labels(mesh / "owner"), labels(mesh / "neighbour")
    if len(faces) != count or len(owner) != count:
        raise ValueError("Wrong face count")
    cells = int(max(owner.max(), neighbour.max()) + 1)
    values, seen = np.full(cells, np.nan), np.zeros(cells, dtype=int)
    for rank in range(receipt["ranks"]):
        part = root / f"processor{rank}"
        ids = labels(part / "constant/polyMesh/cellProcAddressing")
        if not ((ids >= 0) & (ids < cells)).all() or len(np.unique(ids)) != len(ids):
            raise ValueError("Invalid/duplicate partition cell addresses")
        seen[ids] += 1
        values[ids] = temperature(part / receipt["timeDirectory"] / "T", len(ids))
    if not (seen == 1).all() or not np.isfinite(values).all():
        raise ValueError("Every global cell must be mapped exactly once")
    vertices = [set() for _ in range(cells)]
    for i, face in enumerate(faces):
        vertices[owner[i]].update(face)
        if i < len(neighbour):
            vertices[neighbour[i]].update(face)
    polygons, centers = [], []
    for ids in vertices:
        xyz = points[list(ids)]
        projected = np.unique(np.round(np.column_stack((xyz[:, 0], np.hypot(xyz[:, 1], xyz[:, 2]))), 12), axis=0)
        center = projected.mean(axis=0)
        projected = projected[np.argsort(np.arctan2(projected[:, 1]-center[1], projected[:, 0]-center[0]))]
        area = 0.5*np.sum(projected[:, 0]*np.roll(projected[:, 1], -1)-projected[:, 1]*np.roll(projected[:, 0], -1))
        if len(projected) < 3 or area <= 0:
            raise ValueError("Degenerate/nonpositive cell polygon")
        polygons.append(projected*1000)
        centers.append(center*1000)
    return polygons, np.array(centers), values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.plan and args.apply:
        parser.error("Use --plan or --apply")
    receipt = json.loads(args.collection.read_text())
    qualification = receipt.get('stateQualification', 'retained-timestep')
    if qualification not in ['retained-timestep', 'rejected-nonlinear-state']:
        raise ValueError('Unknown retained-state qualification')
    failure = receipt.get('failureRecord')
    if qualification == 'rejected-nonlinear-state':
        if not isinstance(failure, dict) or digest(Path(failure['path'])) != failure['sha256']:
            raise ValueError('Rejected state requires a hash-bound failure record')
    if receipt.get("schema") != "retained-cfd-cell-field/v1" or receipt.get("CFDStartTime_s") != 0 or receipt.get("isTimeMean") is not False:
        raise ValueError("Explicit original-zero instantaneous collection required")
    if not isinstance(receipt["ranks"], int) or receipt["ranks"] < 1 or not 0 < receipt["time_s"] == float(receipt["timeDirectory"]):
        raise ValueError("Invalid time/rank inventory")
    base = Path(receipt["localRoot"]).resolve()
    for name, expected in receipt["inputHashes"].items():
        file = (base / name).resolve()
        if not file.is_relative_to(base) or digest(file) != expected:
            raise ValueError(f"Input escapes collection or changed: {name}")
    origin = receipt.get("axialOrigin_m", 0)
    if not isinstance(origin, (float, int)) or not np.isfinite(origin) or not 0 <= origin <= .02:
        raise ValueError("Invalid explicitly recorded axial origin")
    if origin:
        manifest_name = f"cases/{receipt['case']}/direct-g2-input.json"
        if manifest_name not in receipt["inputHashes"]:
            raise ValueError("Nonzero origin requires a hash-bound case manifest")
        manifest = json.loads((base / manifest_name).read_text())
        if manifest.get("observations", {}).get("axialOrigin_m") != origin:
            raise ValueError("Display origin differs from executing case observations")
    plan = dict(readOnly=not args.apply, collectionSha256=digest(args.collection), sourceJob=receipt["sourceJob"], time_s=receipt["time_s"], out=str(args.out.resolve()))
    if not args.apply:
        print(json.dumps(plan))
        return
    polygons, centers, values = load_cells(receipt, base)
    if origin:
        polygons = [polygon - np.array([origin*1000, 0]) for polygon in polygons]
        centers = centers - np.array([origin*1000, 0])
    args.out.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12})
    norm = plt.Normalize(80, 3600)
    fig, axes = plt.subplots(2, 1, figsize=(13, 6), layout="constrained")
    extent = (min(p[:, 0].min() for p in polygons), max(p[:, 0].max() for p in polygons))
    limits = [extent, (extent[0], 20)] if origin else [(-4.5, 200), (-4.5, 20)]
    for axis, xlim, ylim in zip(axes, limits, [(0, 25), (0, 7)]):
        collection = PolyCollection(polygons, array=values, cmap="inferno", norm=norm, edgecolors="none", rasterized=True)
        axis.add_collection(collection)
        axis.set(xlim=xlim, ylim=ylim, xlabel="Distance from injector exit (mm)" if origin else "Axial position x (mm)", ylabel="Radius r (mm)")
        axis.set_aspect("equal")
        axis.set_facecolor("#e7e7e7")
    fig.colorbar(collection, ax=list(axes), label="Temperature (K)", pad=.02, extend="both")
    status = ('Rejected nonlinear state, not an accepted timestep or paper mean'
              if qualification == 'rejected-nonlinear-state'
              else 'Instantaneous startup, not a developed paper mean')
    fig.suptitle(f"Inlet-resolved G2 | job {receipt['sourceJob']} | t = {receipt['time_s']*1e6:g} μs\n{status}", fontsize=14)
    image = args.out / "temperature-field.png"
    fig.savefig(image, dpi=180)
    plt.close(fig)
    np.savez_compressed(args.out / "cells.npz", T_K=values, center_x_r_mm=centers, polygons_mm=np.array(polygons, dtype=object))
    evidence = dict(**plan, cells=len(values), Tmin_K=float(values.min()), Tmax_K=float(values.max()), imageSha256=digest(image), plottingCodeSha256=digest(Path(__file__)), mappedCellsExactlyOnce=True, fieldMethod="Piecewise-constant actual finite-volume polygons; no smoothing or interpolation", inputHashes=receipt["inputHashes"], CFDStartTime_s=0, isTimeMean=False, scientificAcceptance=False)
    evidence['stateQualification'] = qualification
    evidence['axialOrigin_m'] = origin
    evidence['displayedMeshExtent_mm'] = [float(v) for v in extent]
    if failure is not None:
        evidence['failureRecord'] = failure
    (args.out / "evidence.json").write_text(json.dumps(evidence, indent=2)+"\n")
    print(json.dumps({key: value for key, value in evidence.items() if key != "inputHashes"}))


if __name__ == "__main__":
    main()
