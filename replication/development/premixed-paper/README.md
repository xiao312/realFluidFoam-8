# Paper-method premixed flames with in-situ speed

This module reconstructs Nguyen 2022 Section 5.3 and records Eq.(40) versus
time for both outward fronts. It does not claim the unpublished case files are
known, change the library physics, or promote a result to scientific acceptance.
Parent integration: `99d64f7cab456488f35df2df9c01f2b1cb1be6d7`.

Inputs: `cases.json`, pinned author GRI30/thermo inputs, named baseline solver,
qualified library build 124657926, and pinned OF8 runtime. Outputs: isolated
case/build, source/input/product hashes, two-front CSV history, plots and checks.
Dependencies: existing flame generator/property probe/field reader, OF8 wmake,
MPI, Slurm and Python. Plotting alone needs the existing numpy/matplotlib venv.
Dependents: paper replication analysis and later solver experiments. Credentials
are never consumed by module code; all writes stay in the chosen project job.

## Case definition and paper limits

Paper-stated: CH4/air at 100 atm and 298 K; central hot ignition; two fronts;
0.5-um uniform grid; GRI30, SRK/rfJanaf/Chung-Takahashi; waveTransmissive pressure
at both distant outlets; OH density-weighted displacement speed after ignition
transients decay (Section 5.3, p.11). No imposed inlet speed or products seed.

Declared reconstruction choices: phi=1.10 first; 4-mm domain/8,000 cells; zero
initial velocity; fresh composition everywhere including the hot kernel; a
compact cosine temperature kernel, 0.2-mm total width, peak 1800 K, applied
only in the initial field. Non-pressure outlet fields use zeroGradient;
transverse faces are empty. Pressure gamma is fresh-mixture runtime Cp/Cv and
lInf is the domain length. Air is 21/79 molar O2/N2; N2 is closure species.
The paper does not specify these domain/kernel/BC parameters or numerical
controls. Domain, ignition and numerical independence remain required tests.

Initial flow dt=1e-10 s, maxCo=0.1; compare maxDeltaT=1e-7 and 5e-8 s with
identical remaining inputs. Euler, limitedLinear convection, one outer/two
pressure correctors, SEULEX absTol=1e-8/relTol=1e-6 are declared choices.
Field writes use `runTime`, not `adjustableRunTime`, so output alignment cannot
cap adaptive step growth. In-situ sampling occurs every ten steps and at writes.
First production endpoint is 0.2 ms, not an assertion of relaxed flame speed.

## In-situ diagnostic

The generated draft solver also registers `Qdot` (W/m3, positive exothermic),
refreshes it immediately after `reaction->correct()` on every outer iteration,
and uses that same field in the energy equation. `AUTO_WRITE` saves it at ordinary
field-output times; `NO_READ` avoids reusing a stale source on restart. Before
the first chemistry correction it is zero. It contains the combustion model's
timestep-averaged source, not the instantaneous end-step diagnostic or transport
terms. The library accessor and baseline source remain unchanged. Qualification
in `../heat-release` compares the previous binary against this generated solver
and checks the saved field against the independent read-only source observer.
This does not qualify a same-directory restart: the flame-speed diagnostic
intentionally refuses an existing flame-speed.csv. Any continuation must preserve
the old history and create a separately identified segment with fresh output paths.
That continuation workflow needs a restart comparison before production use.

`instrument.py plan|apply SOURCE_SOLVER OUTPUT` creates `rfPaperReactingFoam`
with opt-in diagnostics and unchanged equations. The source accessor is the
registered `basicChemistryModel::RR(OH)` (already kg/m3/s), not a matrix source
with implicit sign/volume conversions. The species-stage diagnostic captures
the timestep-averaged source and explicit diffusion before OH solution, then
evaluates the implicit diffusion on solved/clipped OH. The end-step diagnostic
uses instantaneous `calculate()` rates and all four corrected diffusion terms
at the final fields. It saves/restores every RR field and never calls the
combustion corrector a second time. An on/off replay must prove field equality.
Both stage labels are retained; the paper leaves discrete source sampling
unspecified. The existing energy-equation YVi is not substituted for corrected
species diffusion.

On each front interpolate source, diffusion and |grad(OH)| at fixed OH mass
fractions 1e-5, 2e-5 (primary) and 3e-5. Divide their summed numerator by fresh
rho times the gradient magnitude; never take an absolute value of the speed.
Fresh rho/T/p/U are measured in the outer 5% on the corresponding side. CSVs
also retain the initial fresh density, contour location, local velocity/density,
gradient, signed contributions, number of crossings and invalid-status reason.
No crossing during ignition or multiple crossings yields an explicit invalid
row, not an invented speed. Left-front tracking is rho/rhou*(U-dx/dt); right
tracking reverses the velocity difference. Each side is reported independently.

## Commands and qualification

`python prepare.py plan phi110-dt100 OUTPUT full` is read-only.
`submit.sh plan|apply ROOT IMAGE RELEASE KEY smoke|full [SMOKE_JOB]` prepares
a bounded scheduled operation. Smoke compares diagnostics-on/off field bodies
on ten identical fixed steps and runs manufactured two-front sampling tests.
Full requires a passed smoke from the same source/configuration. There are no
automatic retries or follow-on allocations. One full job reserves eight cores
for at most 24 hours (192 core-hours); source/inputs/products are immutable.

Verification: `python -B -m unittest discover -s replication/development/premixed-paper`,
shell syntax and `git diff --check`, then scheduled C++ sampling tests, wmake,
library checks, checkMesh, on/off field equality and finite normalized fields.
Missing contours in a short ignition smoke are permitted and explicitly logged.
Production interpretation additionally requires two separated fronts, left/right
agreement, stationary travelling profiles and timestep/domain/kernel checks.
Plots always distinguish source stage, front and threshold, and show ignition
history rather than selecting a window merely because it matches the paper.

## Initialization sensitivity, 19 October

Draft `draft/premixed-ignition` extends paper-draft f020edc; its integration
ancestor remains 99d64f7. Existing dt100/dt050 jobs continue unchanged.
`phi110-cool1400` changes only the fresh cosine kernel peak to 1400 K relative
to dt100. `phi110-equilibrium` uses a uniform equilibrium-products slab in the
central 0.2 mm, with abrupt interfaces as in the earlier half-state setup.
It changes T and all 53 species together; pressure and zero velocity remain
uniform. Both variants retain 4 mm / 8,000 cells, two outlets, maxCo=.1 and
maxDeltaT=1e-7 s. Neither is claimed to reproduce unpublished paper inputs.

The versioned `equilibrium-seed.json` is the exact phi-110-liang input from
replication-suite commit 674b5e289e707918843ea7038b03af2f38170b09. Its provenance
includes Cantera 3.2.0, author NASA7 hash, mass fractions and HP conservation
checks. It is ideal-gas HP equilibrium, not real-fluid equilibrium; the real-fluid
solver must relax it. No Cantera runtime dependency is added. The top-hat
products seed and cosine hot fresh seed test distinct initialization recipes,
not a pure temperature perturbation of one another. No later external heating.

`prepare.py plan|apply` validates seed pressure/phi, fresh state, all species,
normalization and NASA7 input hash. Generated `initialization-check.json` records
symmetry, species-sum error, changed-cell count and seed hash. The existing
on/off smoke qualification is required independently before each full run.
Verify the generated initial fields, then compare temperature peaks, actual
timesteps, source-stage/marker sensitivity and post-ignition propagation.
The two new full allocations reserve at most 384 core-hours together; two
startup allocations add at most 16. They do not replace or cancel prior jobs.

For a slow but advancing startup, `queue-after-smoke.sh plan|apply ROOT IMAGE
RELEASE KEY SMOKE_JOB` can reserve the same full allocation before the check
finishes. It verifies the smoke source/key, uses Slurm afterok with invalid
dependencies cancelled, and independently requires the exact PASS receipt and
source before launching the existing job runner. It shares the duplicate-safe
reservation ledger. A queued dependency is not a qualification result; a failed
smoke cannot start production. Verify shell syntax, plan output, dependency and
recorded source/guard. The controller revision can differ from runnable RELEASE.
