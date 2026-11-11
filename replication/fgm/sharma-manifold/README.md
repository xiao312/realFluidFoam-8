# Sharma Figures 1–2 manifold experiment

Compute unsteady CH4/O2 diffusion flamelets with Spitfire, then expose temperature
and species in the paper's mixture-fraction/progress coordinates. This is separate
from the Famou homogeneous-reactor closure challenge and does not run OpenFOAM.

Inputs: author-deposited Zhukov–Kong YAML, pressure, stream temperatures and a new
output directory. `--plan` reports the contract without writing. Outputs preserve
each actual transient, failures, an equilibrium normalization, 100×100 diagnostic
table, f=0.1/0.2/0.4/0.6 slices and coverage/ambiguity diagnostics.

The source paper specifies 60 bar, 100×100 table nodes and CO2+CO progress with
equilibrium normalization. It does not supply its flamelet generator settings or
raw tables. This experiment uses ideal-gas, adiabatic unity-Le Spitfire flamelets,
85 K oxygen and 288 K methane; these are explicit reconstruction assumptions.
An equilibrium initial field relaxes at each declared Peters scalar dissipation.
This samples genuine reaction/diffusion transients, not imposed temperature curves.
No transient is a continuation of evolved CFD fields. Missing table coverage stays
missing; incompatible temperatures at the same coordinate are reported, not hidden.

Dependencies: pinned patched Spitfire/Griffon, Cantera 3.2, NumPy and SciPy in a
prepared Linux environment. Heavy work runs through FlamePilot Slurm adapters.
This module neither submits jobs nor accesses credentials or networks.

Example: `python run.py --mechanism zk-author.yaml --out NEW_DIR --plan`.
Verification: mechanism import, production-rate parity at warm states, finite
actual trajectories, coordinate normalization and table coverage. Compare against
paper curves after execution. Failed branches are scientific evidence, not passes.
