"""Bounded paper-condition flamelet continuation; never an evolved CFD restart."""
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
from common import inputs, sha256, write_json


def arguments(parser):
    parser.add_argument("--branch-config", type=Path, required=True)
    parser.add_argument("--case-id")
    parser.add_argument("--seed-receipt", type=Path)
    parser.add_argument("--upstream-patch-receipt", type=Path)
    parser.add_argument("--upstream-cold-patch-receipt", type=Path)


def validate(settings):
    if settings.get("schema") != "spitfire-paper-continuation/v1":
        raise ValueError("Unknown paper-continuation settings")
    for name in ("steady_tolerance", "physical_timescale_count", "minimum_relaxation_s",
                 "maximum_relaxation_s", "first_step_s", "max_step_s", "temporal_tolerance",
                 "nonlinear_tolerance", "soft_wall_seconds", "hard_wall_seconds"):
        if type(settings[name]) not in (float, int) or not math.isfinite(settings[name]) or settings[name] <= 0:
            raise ValueError(f"{name} must be finite and positive")
    for name in ("grid_points", "newton_iterations", "max_steps"):
        if type(settings[name]) is not int or settings[name] < 3:
            raise ValueError(f"{name} must be an integer >= 3")
    if settings["soft_wall_seconds"] + 15 > settings["hard_wall_seconds"]:
        raise ValueError("Reserve at least 15 seconds after the soft limit for state export")
    if settings["minimum_relaxation_s"] > settings["maximum_relaxation_s"]:
        raise ValueError("Relaxation interval is reversed")
    known = set()
    for case in settings["cases"]:
        if set(case) != {"id", "chi_st_s_inverse", "seed"} or not re.fullmatch(r"[a-z0-9-]+", case["id"]):
            raise ValueError("Each case needs a safe id, chi_st_s_inverse and explicit seed")
        if case["id"] in known or (case["seed"] is not None and case["seed"] not in known):
            raise ValueError("Case IDs must be unique and seeds must name earlier cases")
        if not math.isfinite(case["chi_st_s_inverse"]) or case["chi_st_s_inverse"] <= 0:
            raise ValueError("Scalar dissipation must be positive and finite")
        known.add(case["id"])
    if not known:
        raise ValueError("At least one case is required")


def run_sequence(args, receipt, settings):
    started = time.monotonic()
    receipt.update(fresh_start=False, scope="Flamelet parameter continuation only; no CFD fields",
                   branch_settings=settings, branch_config_sha256=sha256(args.branch_config), cases=[])
    write_json(args.out / "receipt.json", receipt)
    for case in settings["cases"]:
        output = args.out / case["id"]
        command = [sys.executable, str(Path(__file__).resolve()), "--config", str(args.config.resolve()),
                   "--branch-config", str(args.branch_config.resolve()), "--case-id", case["id"],
                   "--mechanism", str(args.mechanism.resolve()), "--mechanism-sha256", args.mechanism_sha256,
                   "--source-commit", args.source_commit, "--environment-sha256", args.environment_sha256,
                   "--out", str(output.resolve())]
        seed = args.out / case["seed"] / "checkpoint.json" if case["seed"] else None
        if seed is not None and seed.is_file():
            command += ["--seed-receipt", str(seed.resolve())]
        for name in ("upstream_patch_receipt", "upstream_cold_patch_receipt"):
            if getattr(args, name) is not None:
                command += ["--" + name.replace("_", "-"), str(getattr(args, name).resolve())]
        before = time.monotonic()
        with (args.out / (case["id"] + ".log")).open("w") as log:
            try:
                completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                           timeout=settings["hard_wall_seconds"])
                row = {"exit_code": completed.returncode, "hard_wall_limited": False}
            except subprocess.TimeoutExpired:
                row = {"exit_code": None, "hard_wall_limited": True}
        row.update(case=case, elapsed_s=time.monotonic() - before, seed_receipt_present=bool(seed and seed.is_file()))
        if (output / "receipt.json").is_file():
            actual = json.loads((output / "receipt.json").read_text())
            row.update(receipt_sha256=sha256(output / "receipt.json"),
                       status=actual["status"], diagnostics=actual.get("final_state_diagnostics"),
                       steady_numerically_converged=actual.get("steady_numerically_converged", False))
        row["checkpoint_retained"] = (output / "checkpoint.json").is_file()
        if row["hard_wall_limited"]:
            row["steady_numerically_converged"] = False
            row["classification"] = "Process wall limit; checkpoint is evidence, not a completed profile"
        receipt["cases"].append(row)
        write_json(args.out / "branch-summary.json", {"cases": receipt["cases"], "scientific_acceptance": False})
        write_json(args.out / "receipt.json", receipt)
        print(json.dumps(row), flush=True)
    receipt.update(status="continuation_finished_with_recorded_outcomes", elapsed_s=time.monotonic() - started,
                   artifacts={"branch-summary.json": sha256(args.out / "branch-summary.json")})
    write_json(args.out / "receipt.json", receipt)
    return 0 if all(row["exit_code"] == 0 for row in receipt["cases"]) else 5


def main():
    args, config, receipt = inputs(__doc__, arguments)
    settings = json.loads(args.branch_config.read_text())
    validate(settings)
    if args.plan:
        print(json.dumps({"settings": settings, "continuation_is_CFD_restart": False,
                          "maximum_case_wall_seconds": len(settings["cases"]) * settings["hard_wall_seconds"]}, indent=2))
        return 0
    if args.case_id is None:
        return run_sequence(args, receipt, settings)
    selected = [case for case in settings["cases"] if case["id"] == args.case_id]
    if len(selected) != 1:
        raise ValueError("Unknown case-id")
    from paper_case import solve_case
    return solve_case(args, config, receipt, settings, selected[0])


if __name__ == "__main__":
    raise SystemExit(main())
