"""Audit executing/table temperature at retained internal cells; no CFD writes."""
import argparse
import csv
import importlib.util
import json
from pathlib import Path
import re

import numpy as np


def scalar_field(reader, file, count):
    text = reader.foam_text(file)
    match = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;", text, re.S)
    if match:
        values = np.fromstring(match[2], sep=" ")
        if len(values) != int(match[1]) or len(values) != count:
            raise ValueError(f"Wrong internal scalar count: {file}")
    else:
        match = re.search(r"internalField\s+uniform\s+([^;]+);", text)
        if not match:
            raise ValueError(f"Missing internal scalar field: {file}")
        values = np.full(count, float(match[1]))
    if not np.isfinite(values).all():
        raise ValueError(f"Nonfinite internal scalar field: {file}")
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--wedge-degrees", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not 0 < args.wedge_degrees < 30:
        raise ValueError("Explicit small axisymmetric wedge angle required")
    spec = importlib.util.spec_from_file_location("retained_renderer", Path(__file__).with_name("render-case.py"))
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    receipt = json.loads(args.collection.read_text())
    if receipt.get("schema") != "retained-cfd-cell-field/v1" or receipt.get("CFDStartTime_s") != 0 or receipt.get("isTimeMean") is not False:
        raise ValueError("Original-zero instantaneous collection required")
    base = Path(receipt["localRoot"]).resolve()
    bound = set()
    for name, expected in receipt["inputHashes"].items():
        file = (base / name).resolve()
        if not file.is_relative_to(base) or reader.digest(file) != expected:
            raise ValueError(f"Changed/escaping input: {name}")
        bound.add(file)
    case = base / "cases" / receipt["case"]
    required = [case / "constant/polyMesh" / name for name in ["points", "faces", "owner", "neighbour"]]
    for rank in range(receipt["ranks"]):
        part = case / f"processor{rank}"
        required.extend([part / "constant/polyMesh/cellProcAddressing", part / receipt["timeDirectory"] / "T"])
    if any(file.resolve() not in bound for file in required):
        raise ValueError("A consumed mesh, temperature or partition file is not hash-bound")
    points_file = case / "constant/polyMesh/points"
    text = reader.list_body(points_file)[1]
    xyz = np.array([list(map(float, m[1].split())) for m in re.finditer(r"\(([^()]*)\)", text)])
    angles = np.rad2deg(np.arctan2(xyz[:, 2], xyz[:, 1]))
    observed_angle = float(angles.max() - angles.min())
    if abs(observed_angle - args.wedge_degrees) > 1e-6:
        raise ValueError(f"Mesh angle {observed_angle} differs from requested angle")
    polygons_mm, centers, temperatures = reader.load_cells(receipt, base)
    volumes = []
    for polygon in polygons_mm:
        p = polygon * .001
        q = np.roll(p, -1, axis=0)
        cross = p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1]
        radial_moment = np.sum((p[:, 1] + q[:, 1]) * cross) / 6
        volumes.append(np.sin(np.deg2rad(args.wedge_degrees)) * radial_moment)
    volumes = np.asarray(volumes)
    if not (volumes > 0).all():
        raise ValueError("Nonpositive reconstructed wedge cell volume")
    fields = {"T": temperatures}
    for name in ["fgmTdiag", "fgmScSource", "rho", "Z", "c", "Ha", "p"]:
        values = np.full(len(volumes), np.nan)
        for rank in range(receipt["ranks"]):
            part = case / f"processor{rank}"
            address_file = part / "constant/polyMesh/cellProcAddressing"
            file = part / receipt["timeDirectory"] / name
            if address_file.resolve() not in bound or file.resolve() not in bound:
                raise ValueError(f"Required field/address is not hash-bound: {file}")
            ids = reader.labels(address_file)
            values[ids] = scalar_field(reader, file, len(ids))
        if not np.isfinite(values).all():
            raise ValueError(f"Unmapped field: {name}")
        fields[name] = values
    if not (fields["rho"] > 0).all() or not (fields["p"] > 0).all() or not (fields["fgmTdiag"] > 0).all():
        raise ValueError("Nonpositive thermodynamic input")
    delta = temperatures - fields["fgmTdiag"]
    weights = np.abs(fields["fgmScSource"]) * volumes
    total_source = float(weights.sum())

    def source_average(values):
        return float(np.sum(weights * values) / total_source) if total_source > 0 else None

    report = {
        "schema": "g2-internal-thermal-state-audit/v1", "sourceJob": receipt["sourceJob"],
        "time_s": receipt["time_s"], "cells": len(volumes), "mappedCellsExactlyOnce": True,
        "collectionSha256": reader.digest(args.collection), "auditCodeSha256": reader.digest(Path(__file__)),
        "wedgeDegrees": observed_angle, "volume_m3": float(volumes.sum()),
        "volumeMeanAbsoluteDeltaT_K": float(np.sum(volumes * abs(delta)) / volumes.sum()),
        "volumeRmsDeltaT_K": float(np.sqrt(np.sum(volumes * delta**2) / volumes.sum())),
        "maximumAbsoluteDeltaT_K": float(abs(delta).max()),
        "absoluteSourceIntegral_kg_s": total_source,
        "signedSourceIntegral_kg_s": float(np.sum(fields["fgmScSource"] * volumes)),
        "absoluteSourceMeanAbsoluteDeltaT_K": source_average(abs(delta)),
        "absoluteSourceFractionInCellsBelow500K": source_average(temperatures < 500),
        "absoluteSourceFractionWithDeltaTAbove100K": source_average(abs(delta) > 100),
        "boundarySamplesUsed": False, "sourceScalingApplied": False,
        "scientificAcceptance": False, "CFDStartTime_s": 0, "isTimeMean": False,
        "readOnly": not args.apply,
    }
    if args.apply:
        args.out.mkdir(parents=True, exist_ok=False)
        with (args.out / "cells.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["cell", "x_mm", "r_mm", "volume_m3", *fields, "deltaT_K"])
            for i in range(len(volumes)):
                writer.writerow([i, *centers[i], volumes[i], *(values[i] for values in fields.values()), delta[i]])
        report["cellsCsvSha256"] = reader.digest(args.out / "cells.csv")
        (args.out / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
