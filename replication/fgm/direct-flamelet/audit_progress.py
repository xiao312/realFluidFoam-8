"""Measure progress-coordinate overshoot and branch ambiguity in an actual raw trajectory."""
import argparse
import json
from pathlib import Path
import numpy as np
from common import sha256, write_json


def monotone_segments(values, threshold):
    differences = np.diff(values)
    # Ignore numerically insignificant increments when identifying direction changes.
    signs = np.sign(np.where(abs(differences) > threshold, differences, 0))
    segments, first, direction = [], 0, 0
    for index, sign in enumerate(signs):
        if sign and direction and sign != direction:
            segments.append((first, index))
            first = index
        if sign:
            direction = sign
    segments.append((first, len(values) - 1))
    return [(a, b) for a, b in segments if b > a and abs(values[b] - values[a]) > threshold]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    receipt = json.loads((args.run / "receipt.json").read_text())
    digest = sha256(args.run / "trajectory.npz")
    if digest != receipt["artifacts"]["trajectory.npz"]:
        raise ValueError("Trajectory hash mismatch")
    if args.plan:
        print(json.dumps({"input_sha256": digest, "task": "raw C versus fresh HP C and repeated-C states"}))
        return
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new path")
    raw = np.load(args.run / "trajectory.npz")
    species = list(raw["species"])
    z, times, temperature, y = raw["Z"], raw["time_s"], raw["T_K"], raw["Y"]
    c = y[:, :, species.index("CO2")] + y[:, :, species.index("CO")]
    initial, maximum = c[0], np.max(c, axis=0)
    cmax_to_ceq = np.divide(maximum, initial, out=np.full_like(initial, np.nan), where=initial >= 1e-6)
    observations = []
    for j in range(1, len(z) - 1):
        span = float(np.ptp(c[:, j]))
        threshold = max(1e-8, span * 1e-4)
        segments = monotone_segments(c[:, j], threshold)
        maximum_delta = {"T_K": 0.0, "Y_CO2": 0.0, "Y_H2O": 0.0, "Y_OH": 0.0}
        witnesses = []
        columns = {"T_K": temperature[:, j], **{"Y_" + name: y[:, j, species.index(name)] for name in ("CO2", "H2O", "OH")}}
        for n, (a, b) in enumerate(segments):
            for d, e in segments[n + 1:]:
                lower = max(min(c[a, j], c[b, j]), min(c[d, j], c[e, j]))
                upper = min(max(c[a, j], c[b, j]), max(c[d, j], c[e, j]))
                if upper - lower <= threshold:
                    continue
                query = np.linspace(lower, upper, 21)
                ia = np.arange(a, b + 1)[np.argsort(c[a:b + 1, j])]
                ib = np.arange(d, e + 1)[np.argsort(c[d:e + 1, j])]
                differences = {name: abs(np.interp(query, c[ia, j], field[ia]) - np.interp(query, c[ib, j], field[ib]))
                               for name, field in columns.items()}
                for name, error in differences.items():
                    maximum_delta[name] = max(maximum_delta[name], float(np.max(error)))
                worst = int(np.argmax(differences["T_K"]))
                witnesses.append({"branch_frames": [[int(a), int(b)], [int(d), int(e)]],
                    "C": float(query[worst]), "temperature_difference_K": float(differences["T_K"][worst]),
                    "crossing_times_s": [float(np.interp(query[worst], c[idx, j], times[idx])) for idx in (ia, ib)]})
        if witnesses:
            observations.append({"Z": float(z[j]), "Ceq_fresh_HP": float(initial[j]),
                "Cmax": float(maximum[j]), "Cmax_over_Ceq": float(cmax_to_ceq[j]) if np.isfinite(cmax_to_ceq[j]) else None,
                "direction_change_threshold": threshold, "monotone_segments": len(segments),
                "maximum_same_C_branch_difference": maximum_delta,
                "largest_temperature_witness": max(witnesses, key=lambda item: item["temperature_difference_K"])})
    result = {"schema": "physical-progress-audit/v1", "trajectory_sha256": digest,
        "source_commit": receipt["source_commit"], "physical_grid_points": len(z), "time_frames": len(times),
        "progress_definition": "C=Y_CO2+Y_CO; Sharma equation22 c=C/Ceq(fresh HP initial state)",
        "local_eta_definition": "(C-measured_Cmin)/(measured_Cmax-measured_Cmin); not Sharma c",
        "Ceq_ratio_mask_minimum": 1e-6, "maximum_Cmax_over_Ceq": float(np.nanmax(cmax_to_ceq)),
        "Z_with_Cmax_above_Ceq_by_0p1percent": [float(z[i]) for i in np.flatnonzero(cmax_to_ceq > 1.001)],
        "Z_with_repeated_C_branches": len(observations),
        "maximum_branch_temperature_difference_K": max((row["maximum_same_C_branch_difference"]["T_K"] for row in observations), default=0),
        "interpolation_scope": "Linear crossings within actual temporal monotone branches, not new physical solutions or synthetic sources",
        "interpretation": "Sorting by C can join distinct physical paths. Lookup-grid refinement alone cannot fix multi-valued states. Recheck after energy correction.",
        "scientific_acceptance": False, "observations": observations}
    write_json(args.out, result)
    print(json.dumps({key: value for key, value in result.items() if key != "observations"}, indent=2))


if __name__ == "__main__":
    main()
