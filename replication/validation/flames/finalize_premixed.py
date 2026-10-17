"""Set waveTransmissive gamma from the unburned mixture's runtime Cp/Cv."""
import csv
import json
import math
import sys
from pathlib import Path

case = Path(sys.argv[1]).resolve()
config = json.loads((case/"pilot.json").read_text())
if config["boundary_finalized"]:
    raise ValueError("Boundary already finalized")
with (case/"inlet-densities.csv").open(newline="") as stream:
    rows = {row["patch"]: row for row in csv.DictReader(stream)}
gammas = [float(rows[name]["Cp_J_kg_K"])/float(rows[name]["Cv_J_kg_K"]) for name in ("left", "right")]
if not all(math.isfinite(value) and value > 1 for value in gammas) or abs(gammas[0]-gammas[1]) > 1e-10:
    raise ValueError("Invalid or unequal boundary Cp/Cv")
text = (case/"0/p").read_text()
if text.count("gamma 1;") != 2:
    raise ValueError("Unexpected pressure boundaries")
with (case/"0/p").open("w", newline="\n") as stream:
    stream.write(text.replace("gamma 1;", f"gamma {gammas[0]:.16g};"))
config.update(boundary_finalized=True, wave_gamma=gammas[0], unburned_density_kg_m3=float(rows["left"]["rho_kg_m3"]))
(case/"pilot.json").write_text(json.dumps(config, indent=2)+"\n")
print(json.dumps(config, indent=2))
