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
python replication/development/ideal-baseline/cantera_refine.py plan OUTPUT FINE_OUTPUT
python replication/development/ideal-baseline/cantera_refine.py apply OUTPUT FINE_OUTPUT
python replication/development/ideal-baseline/plot.py FIGURE8_CROP FINE_OUTPUT FIGURE_OUTPUT
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

The mechanism test checks all grouped forward rates against bundled GRI30 at
500, 1000, 1800 and 2300 K. Author activation temperatures are slightly different
from bundled Ea/R. The largest observed difference is 0.7212% for HCN
dissociation at 500 K; both rates are below 1e-39 in that test mixture.
The adapter preserves author values. Molecular weights differ by at most
0.00501% because the programs use different atomic-weight definitions.

`cantera_refine.py` restores completed flames into a new output directory and
adds two grid levels. The last change is reported, not hidden by rounding.
`plot.py` requires the recorded 612-by-1218-pixel Fig.8 crop. It writes a
side-by-side comparison and a direct overlay that retains the original pixels.
Image-derived values have a declared approximate ±0.03 cm/s reading uncertainty.
Missing CFD results remain labelled pending; a seed is never plotted as CFD.

Startup job 124877695 passed on release 128d13d. All 1,360 common field bodies
matched with diagnostics enabled/disabled. The ideal-density identity differed
by 8.96e-7 relatively; normalized finite fields and native Qdot passed.
This qualifies startup and diagnostic noninterference, not flame speed.

## Running-case assessment

`history.py SNAPSHOT_DIR CANTERA_RESULTS_JSON NEW_OUTPUT_DIR` reads immutable
local copies of `flame-speed.csv`, `paper-case.json` and a job snapshot register.
It writes a JSON assessment and a history plot. It never modifies jobs or
selects a time window to obtain agreement with a reference value. The default
window is the last 5 microseconds covered by both sides at the primary OH
marker. Incomplete final CSV lines are discarded and counted. Invalid contours
remain gaps. Each window must have at least three valid samples.

The module reuses the `premixed-sensitivity` CSV reader and tracking formula.
Primary speed is density-weighted front tracking; the source used in the OH
species solve is a cross-check. Per the owner's 19 October decision,
instantaneous-source speeds are excluded from plots and acceptance criteria.
End-step rows still supply position, velocity and density for tracking, without
using their instantaneous chemistry rates. Missing secondary OH markers are
reported separately. No CFD point is declared converged or
added to the paper speed-versus-phi curve by this command. Transport, domain,
time-step and mesh independence remain separate requirements.

Verification: run the existing sensitivity unit tests and inspect the full
histories and reported window bounds. Cantera's solved inlet velocity is the
steady reference; density-weighted tracking uses local gas velocity, not raw
front motion in the laboratory frame.

`anchors.py plan|apply PROFILES MECHANISM OUTPUT_JSON` restores each completed
Cantera solution and exports its actual fixed-temperature anchor. It also
checks that density-weighted velocity there agrees with the solved inlet speed.
The reference coordinate is metadata only: CFD tracks the same temperature
at its own evolving position. Additional fixed temperatures at 20%, 50% and
80% of the reference temperature rise check marker independence. Do not update
these temperatures from the CFD's instantaneous peak temperature; doing so
would add threshold motion to the measured front speed.
