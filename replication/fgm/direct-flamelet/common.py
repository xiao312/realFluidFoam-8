"""Validated, immutable inputs and receipts shared by the two science drivers."""
import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def inputs(description, extra_arguments=None):
    parser = argparse.ArgumentParser(description=description)
    if extra_arguments is not None:
        extra_arguments(parser)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--mechanism", type=Path)
    parser.add_argument("--mechanism-sha256")
    parser.add_argument("--source-commit")
    parser.add_argument("--environment-sha256")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    expected = {"case", "pressure_pa", "fuel", "oxidizer", "width_m", "fuel_mdot_kg_m2_s",
                "oxidizer_mdot_kg_m2_s", "max_grid_points", "max_time_steps", "refine",
                "equilibrium_points", "allow_thermo_extrapolation", "description"}
    if set(config) != expected:
        parser.error(f"config keys differ: missing={expected-set(config)}, extra={set(config)-expected}")
    for key in ("pressure_pa", "width_m", "fuel_mdot_kg_m2_s", "oxidizer_mdot_kg_m2_s"):
        if not isinstance(config[key], (int, float)) or not math.isfinite(config[key]) or config[key] <= 0:
            parser.error(f"{key} must be a finite positive number")
    for key, lower in (("max_grid_points", 48), ("max_time_steps", 1), ("equilibrium_points", 3)):
        if type(config[key]) is not int or config[key] < lower:
            parser.error(f"{key} must be an integer >= {lower}")
    for stream in ("fuel", "oxidizer"):
        entry = config[stream]
        if set(entry) != {"temperature_k", "mole_fractions"}:
            parser.error(f"{stream} requires temperature_k and mole_fractions only")
        if not isinstance(entry["mole_fractions"], dict) or not entry["mole_fractions"]:
            parser.error(f"{stream}.mole_fractions must be a nonempty object")
        values = [entry["temperature_k"], *entry["mole_fractions"].values()]
        if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in values):
            parser.error(f"{stream} values must be finite and positive")
    if type(config["allow_thermo_extrapolation"]) is not bool:
        parser.error("allow_thermo_extrapolation must be boolean")
    if set(config["refine"]) != {"ratio", "slope", "curve", "prune"}:
        parser.error("refine requires ratio, slope, curve, prune")
    refine = config["refine"]
    if not (refine["ratio"] >= 2 and 0 < refine["slope"] <= 1 and
            0 < refine["curve"] <= 1 and 0 <= refine["prune"] < min(refine["slope"], refine["curve"])):
        parser.error("invalid refinement criteria")
    if args.plan:
        print(json.dumps({"mode": "read_only_plan", "config": config, "fresh_start": True,
                          "thermo": "ideal-gas", "transport": "unity-Lewis-number",
                          "scientific_acceptance": False}, indent=2))
        return args, config, None
    for name, length in (("mechanism_sha256", 64), ("source_commit", 40), ("environment_sha256", 64)):
        if not re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", getattr(args, name) or ""):
            parser.error(f"--{name.replace('_', '-')} requires {length} lowercase hex characters")
    if args.mechanism is None or not args.mechanism.is_file() or args.out is None:
        parser.error("run requires --mechanism FILE and --out NEW_DIRECTORY")
    if sha256(args.mechanism) != args.mechanism_sha256:
        parser.error("mechanism SHA256 mismatch; no computation performed")
    if args.out.exists():
        parser.error("output path already exists; choose a fresh directory")
    args.out.mkdir(parents=True)
    receipt = {"schema": "direct-flamelet/v1", "case": config,
               "started_at": datetime.now(timezone.utc).isoformat(), "fresh_start": True,
               "source_commit": args.source_commit, "environment_sha256": args.environment_sha256,
               "mechanism_sha256": args.mechanism_sha256, "mechanism_path": str(args.mechanism),
               "config_sha256": sha256(args.config), "scientific_acceptance": False,
               "source_files": {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
               "status": "started"}
    write_json(args.out / "receipt.json", receipt)
    return args, config, receipt


def gas_and_streams(ct, args, config, receipt):
    if ct.__version__ != "3.2.0":
        raise ValueError(f"This driver is pinned to Cantera 3.2.0, found {ct.__version__}")
    gas = ct.Solution(str(args.mechanism), transport_model="unity-Lewis-number")
    if gas.thermo_model != "ideal-gas":
        raise ValueError(f"Expected ideal-gas phase, found {gas.thermo_model}")
    streams = {}
    for name in ("fuel", "oxidizer"):
        entry = config[name]
        gas.TPX = entry["temperature_k"], config["pressure_pa"], entry["mole_fractions"]
        if gas.T < gas.min_temp and not config["allow_thermo_extrapolation"]:
            raise ValueError(f"{name} T={gas.T} K is below mechanism range {gas.min_temp} K")
        streams[name] = {"Y": gas.Y.copy(), "h": gas.enthalpy_mass,
                         "density": gas.density, "temperature": gas.T}
    receipt["models"] = {"cantera": ct.__version__, "thermo": gas.thermo_model,
                         "transport": gas.transport_model, "species_count": gas.n_species,
                         "mechanism_temperature_range_k": [gas.min_temp, gas.max_temp],
                         "inlet_thermo_extrapolation": any(s["temperature"] < gas.min_temp for s in streams.values()),
                         "kinetics_temperature_extrapolation": "not qualified outside mechanism validity",
                         "density_model": "ideal-gas; not paper PR-VTA"}
    return gas, streams


def failure(args, receipt, error, elapsed_s):
    receipt.update(status="failed", error_type=type(error).__name__, error=str(error),
                   elapsed_s=elapsed_s, completed_at=datetime.now(timezone.utc).isoformat())
    write_json(args.out / "receipt.json", receipt)
