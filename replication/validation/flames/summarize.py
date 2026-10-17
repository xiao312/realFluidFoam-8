"""Check final internal fields of an ASCII pilot; no convergence claim is made."""
import json
import math
import re
import sys
from pathlib import Path

case = Path(sys.argv[1]).resolve()
config = json.loads((case/"pilot.json").read_text())
cells = config["cells"]
times = []
for path in case.iterdir():
    if path.is_dir():
        try:
            times.append((float(path.name), path))
        except ValueError:
            pass
time, latest = max(times)
if time <= 0:
    raise ValueError("No advanced solution time")


def field(path):
    text = path.read_text()
    uniform = re.search(r"internalField\s+uniform\s+([^;]+);", text)
    if uniform:
        return [float(uniform.group(1))]*cells
    nonuniform = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;", text, re.S)
    if not nonuniform:
        raise ValueError("Unsupported scalar field: " + str(path))
    values = list(map(float, nonuniform.group(2).split()))
    if len(values) != cells or int(nonuniform.group(1)) != cells:
        raise ValueError("Field size mismatch: " + str(path))
    return values


summary = {"time_s": time, "cells": cells, "scope": "startup/cost pilot only", "fields": {}}
failures = []
for name in ("T", "p", "rho"):
    values = field(latest/name)
    if not all(math.isfinite(value) and value > 0 for value in values):
        failures.append("nonfinite/nonpositive " + name)
    summary["fields"][name] = {"min": min(values), "max": max(values)}
thermo = (case/"constant/thermo.inputData_GRI").read_text()
species = re.search(r"species\s+53\s*\((.*?)\)\s*;", thermo, re.S).group(1).split()
if len(species) != 53:
    raise ValueError("Expected 53-species GRI30")
sums = [0.0]*cells
minimum, maximum = math.inf, -math.inf
for name in species:
    values = field(latest/name)
    if not all(math.isfinite(value) for value in values):
        failures.append("nonfinite mass fraction " + name)
    minimum, maximum = min(minimum, min(values)), max(maximum, max(values))
    sums = [total+value for total, value in zip(sums, values)]
error = max(abs(total-1) for total in sums)
summary["mass_fractions"] = {"minimum": minimum, "maximum": maximum, "max_sum_error": error}
if minimum < -1e-12 or maximum > 1+1e-8 or error > 1e-8:
    failures.append("mass-fraction bounds/sum criterion")
summary["failed_checks"] = failures
(case/"pilot-summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
print(json.dumps(summary, indent=2, allow_nan=False))
sys.exit(3 if failures else 0)
