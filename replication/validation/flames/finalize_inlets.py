"""Set pilot velocities from densities evaluated by the actual runtime library."""
import csv
import json
import math
import re
import sys
from pathlib import Path

case = Path(sys.argv[1]).resolve()
config = json.loads((case/"pilot.json").read_text())
if config["velocities_finalized"]:
    raise ValueError("Inlets already finalized")
with (case/"inlet-densities.csv").open(newline="") as stream:
    densities = {r["patch"]: float(r["rho_kg_m3"]) for r in csv.DictReader(stream)}
fuel, oxidizer = densities["fuel"], densities["oxidizer"]
if not all(math.isfinite(v) and v > 0 for v in (fuel, oxidizer)):
    raise ValueError("Invalid runtime inlet densities")
if config["velocity_constraint"] == "mass":
    uf, uo = 1.0, fuel/oxidizer
else:
    ratio = math.sqrt(fuel/oxidizer)
    uf = 100*config["length_m"]/2/(1+ratio)
    uo = uf*ratio
text = (case/"0/U").read_text()
for patch, speed in (("fuel", uf), ("oxidizer", -uo)):
    text, count = re.subn(patch+r" \{.*?\}",
        f"{patch} {{ type fixedValue; value uniform (0 0 {speed:.16g}); }}", text)
    if count != 1:
        raise ValueError("Unexpected velocity boundary: " + patch)
with (case/"0/U").open("w", newline="\n") as stream:
    stream.write(text)
config.update(velocities_finalized=True, inlet_densities_kg_m3={"fuel": fuel, "oxidizer": oxidizer},
              inlet_speed_m_s={"fuel": uf, "oxidizer": uo},
              strain_per_s=2*(uf+uo)/config["length_m"])
(case/"pilot.json").write_text(json.dumps(config, indent=2)+"\n")
print(json.dumps(config, indent=2))
