# Ideal-gas planar flame baseline

This module compares our reacting solver with Liang Fig.8(a), Case 1, and
Cantera 3.2.0 FreeFlame. It changes the runtime thermo/chemistry family, not
the solver equations. It does not claim transport equivalence or convergence.

Inputs: pinned author GRI30 reactions and NASA7 coefficients, ideal HP seeds,
the qualified diagnostic solver, and the OF8 environment lock. Outputs: isolated
Slurm cases, source/input hashes, speed histories, Cantera profiles and figures.
Configuration uses phi=0.90 through 1.40, pressure=10132500 Pa and Tu=298 K.
Liang's supplied main article does not specify Tu numerically; 298 K follows
Nguyen. All comparisons must retain this unresolved reference condition.

Our runtime family is idKineticMixture / perfectGas / janaf /
sutherlandKinetic / sensibleEnthalpy, with idKineticStandard chemistry,
SEULEX and laminar combustion. It uses Sutherland viscosity, Eucken-style
conductivity and kinetic mixture diffusion. Cantera uses mixture-averaged
transport, mole-fraction gradients and no Soret. Its transport species data
come from bundled gri30.yaml; these are not assumed identical to our transport.
The Cantera adapter reads author NASA7 and reaction parameters directly.
Atomic weights and physical constants retain each program's definitions.

The CFD setup retains the 4-mm, 8000-cell, two-front products-slab experiment.
Each phi has its own ideal HP equilibrium seed. This seed is an initial state,
not a measured flame speed. Eq.(40), density-weighted front tracking, heat release
and profile evolution establish the subsequent comparison. maxCo=0.1,
maxDeltaT=50 ns, endpoint=0.2 ms are declared numerical choices.

Dependencies: premixed-paper preparation/finalization, qualified solver build
124870644, library build 124657926, property probe, environment runner, Slurm,
Python, and Cantera 3.2.0 for the independent calculation only. Plotting uses
numpy/matplotlib. Dependents: the paper comparison record and later staged
real-gas tests. Credentials remain outside source; outputs stay in the project.

Commands, from the repository root:

```
python replication/development/ideal-baseline/cantera_run.py plan OUTPUT
python replication/development/ideal-baseline/cantera_run.py apply OUTPUT
python replication/development/ideal-baseline/prepare.py plan phi110 OUTPUT smoke
bash replication/development/ideal-baseline/submit.sh plan ROOT IMAGE RELEASE phi110 smoke
```

Plan commands are read-only. Apply refuses existing output. Production requires
a passing ideal-family smoke. Each full job requests 8 cores for at most 6 hours;
the entire 11-point sweep reserves at most 528 core-hours plus startup checks.
No automatic continuation is enabled. Source release, binary and library hashes
must remain traceable even if a later documentation commit is newer.

Verification: `python -B -m unittest discover -s replication/development/ideal-baseline`,
shell syntax, `git diff --check`, scheduled model selection/property checks,
diagnostics-on/off equality and finite normalized endpoint fields. Cantera saves
successive refinement results; a small speed change is a numerical indicator,
not proof of matching the unpublished PREMIX inputs.
