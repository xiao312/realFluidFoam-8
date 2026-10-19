# In-situ planar flame tracking

Owner rule, 19 October 2026: new realFluidFoam-based runs start from original
time-0 initialization. The checkpoint generator now rejects plan/apply without
`--restart-authorization` recording actual explicit owner permission. Existing
checkpoint launchers therefore fail closed. Use `../fresh-start` for new cases.

`history.py SNAPSHOT OUTPUT` verifies local snapshot hashes and plots all three
retained measures with the ideal Cantera reference. It uses matplotlib and
does not contact or change running jobs. The output directory must be new;
histories retain both fronts and explicitly mark scientific acceptance false.

This module adds read-only OH and fixed-temperature front tracking to the
qualified reacting equations. It retains the timestep-averaged OH source
measure and removes instantaneous chemistry recalculation from this executable.
It does not change chemistry, transport, boundary conditions or solver coupling.

Inputs: the premixed-paper generator, ideal-baseline donor cases, saved Cantera
temperature anchors, qualified library build 124657926 and locked OF8 image.
Outputs: a separately named `rfTrackedReactingFoam`, source/input/binary hashes,
`front-tracking.csv`, the existing species-solve `flame-speed.csv`, native Qdot
fields and isolated continuation cases. All paths stay under the project root;
credentials are outside this module. No production executable is overwritten.

`constant/frontTrackingProperties` configures enabled, interval, windowSeconds,
temperatureLevels, ohLevels and freshTemperature. Temperature levels are fixed:
the first is the actual Cantera anchor and the others are 20%, 50%, 80% of the
reference temperature rise. OH levels are 1e-5, 2e-5 and 3e-5. Samples are taken
at completed timesteps, plus the initial checkpoint, after a global MPI gather.
Each front must have exactly one fresh-side crossing. Invalid or ambiguous
contours reset their tracking history and remain explicitly labelled.

The last five microseconds define a least-squares front velocity. Output retains
the fit window, sample count, position residual, gas velocity, density and signed
laboratory, fresh-relative and density-weighted speed. Density weighting uses
the window mean of `rho_local/rho_fresh * (Vfit - Ulocal)`, with the sign reversed
for the left front. A two-sample secant is also recorded, separately labelled.
Warmup rows do not claim a full-window speed. The outer 5% on each side supplies
fresh gas properties and must remain within 2 K of the configured fresh temperature.
Temperature fronts and OH fronts are different markers for the same measure;
the third measure is the source/diffusion formula already used in the species solve.

The generated observer never calls chemistry or writes fluid fields. Qualification
compares all common field bodies with the old qualified solver and with tracking
disabled over identical restart steps. A manufactured C++ test checks both signs,
local gas correction, density weighting, warmup and ambiguous-contour rejection.
An endpoint and finite-field check establishes operational health, not steady speed.

Dependencies: premixed-paper source generator, standard C++11, OF8, MPI, Slurm,
the environment/validation dispatcher and adaptive field reader. Dependents:
ideal-gas flame comparisons and their current Lark section. No new runtime library.

Commands: `instrument.py plan|apply RELEASE OUTPUT` previews/creates the solver.
`submit.sh plan ROOT IMAGE RELEASE qualify` is read-only. Apply requests eight
cores for 30 minutes. Production: `submit.sh plan ROOT IMAGE RELEASE phi110 BUILD`
uses a passing build receipt, copies one completed donor checkpoint, and reserves
eight cores for six hours to reach 200 us. Submission is locked and deduplicated.
Every original donor remains read-only. Cancel a superseded donor only after the
replacement starts with verified copied inputs; record both job identities.

Verification: Python compilation, shell syntax, C++ manufactured test, scheduled
build/link checks and old/new/disabled field equality. Inspect all eleven phi
conditions and all three measures after continuation warmup. Keep timestep, mesh,
domain and thermal-marker sensitivity distinct from operational qualification.
