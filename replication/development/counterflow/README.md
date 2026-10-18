# Tutorial and paper counterflow variants

This draft makes the difference between the shipped 11,200-cell tutorial and
the paper meshes explicit. It prepares fresh two-stage cases; it does not change
the solver, chemistry tolerances or existing jobs. Dependencies: author-counterflow
and paper-campaign preparation, runtime density probe and OF8 mesh tools.
Dependent: future mesh/convergence comparisons. No secrets or external writes.

Inputs: condition `oxy-1|oxy-200|air-100`, variant `tutorial|paper`, new output
directory. Outputs: two-stage dictionaries, variant manifest and file hashes.
`plan` reports the mesh without writes; `apply` refuses existing output. Tutorial
means the existing author port (with declared high-pressure adaptations).
Paper means the published conditions plus a declared reconstruction of its mesh.

| Condition | R x L | Paper radial spacing | Near-flame axial spacing | Reconstructed cells |
| --- | --- | --- | --- | ---: |
| Oxyfuel 1 atm | 20 x 20 mm | 20 micrometres | 20 micrometres | 888,000 |
| Oxyfuel 200 atm | 5 x 5 mm | 5 micrometres | 5 micrometres | 816,000 |
| Air 100 atm | 20 x 20 mm | select 5 micrometres | 5 micrometres | 7,912,000 |

For air, the paper says 5-micrometre mesh in the flame zone without a directional
table. We select uniform 5-micrometre radial spacing as the conservative reading.
This supersedes the earlier draft assumption of 20 micrometres radially.
The original three-zone wedge geometry is retained. The central 40% of axial
length is uniform; outer blocks stretch away from it. The paper does not give
zone extents or stretching ratios: these are reconstructed and must be checked
against the actual flame location. For oxyfuel the outer endpoint spacings are
approximately 20–30 and 5–10 micrometres. Air stretches from about 5 to 100
micrometres outside the central zone. No claim of identical publication mesh.

Paper oxyfuel uses exact 21/79 molar O2/CO2 conversion, 300/1000 K streams,
strain=100/s and equal momentum using actual library densities. Tutorial uses
the original rounded Y(O2)=0.162 and fixed 1-atm velocities 0.467/0.533 m/s.
At the lateral paper outlet, p retains totalPressure while other primitive fields
use zeroGradient as described in section 5.2. Tutorial keeps its original mixed
inletOutlet/pressureInletOutletVelocity choices. Air retains the published-reference
adaptation (300 K streams, fuel 1 m/s, matched mass flux), which is documented
separately from the original 1-atm example. Source numerics/GRI30 remain unchanged.

Example: `python prepare.py plan oxy-200 paper OUTPUT` then `apply`.
Before CFD, run blockMesh/checkMesh and the library inlet probe plus
`validation/flames/finalize_inlets.py CASE` for each phase that has pilot.json.
Do not run large-grid GRI30 on a login node or apply tutorial resource limits
blindly. First qualify geometry and memory in Slurm, then map checked coarse
fields with documented interpolation and conservation checks.

Verification: all six plans, generated counts/spacing and preserved fvSchemes,
scheduled mesh checks, inlet strain/momentum/composition, field transfer and
centerline/radial sampling. Acceptance requires multiple resolutions, stable
profiles and comparison with the paper curves. The 100-atm chemistry failure
must be resolved in a separate numerical-control/solver draft before a large run.

`check_meshes.sh RELEASE JOB` runs inside the pinned container in a scheduled
allocation through validation stage `dev-counterflow-mesh`. It generates all
three paper variants, checks identical phase mesh dictionaries and requires
blockMesh/checkMesh success. It runs no chemistry and does not qualify flow.


## Corrected reacting runs

`refine.py plan|apply CONDITION JOB_DIR` prepares a new paper-resolution oxyfuel
case and copies only a pinned stable coarse checkpoint into a private donor.
It never modifies the source job. `run_refined.sh RELEASE JOB CONDITION` builds
our rename-only solver, qualifies the mesh, finalizes exact inlet composition
and momentum balance, and maps primitive fields with OF8 `mapFields`.
Only T, p, U and the 53 species are mapped; enthalpy, density and transport are
recomputed. Target boundary conditions remain those of the new paper case.
The mapping is a warm start, not a conservative restart or scientific result.
Hashes, field ranges and species-sum checks are recorded before time integration.

The first allocation is a bounded 10-microsecond qualification on 32 cores.
It measures memory, initialization and per-step cost on the actual fine mesh.
Controls: maxCo=0.2, maxDeltaT=1e-6 s, initial deltaT=1e-7 s. These are selected
numerical controls, not settings stated by the paper. Chemistry and PIMPLE
settings remain the original tutorial values. No steady-state claim follows.
Air is prepared separately but not launched at full resolution until its chemistry
failure is reproduced and resolved; the current coarse air state is not a valid
steady donor. Do not submit a long run before this qualification succeeds.

Verification: dry-run plans; checked source checkpoint hashes; identical GRI30
species lists; all generated species fields; preserved target boundary types;
mesh and normalized-field checks; isolated solver hash/ldd; timed Slurm run.
All generated state stays below JOB_DIR inside the project root. The runner
uses the existing environment, property probe and adaptive field inspector.

## Parallel inlet qualification

The fine-grid property initialization now runs on the same 32-rank decomposition
as the reacting solver. Each rank writes its own `processorN/inlet-densities.csv`.
`parallel_inlets.py plan|apply CASE RANKS --reference SERIAL_CSV` requires every
rank output, both inlet patches, finite positive properties and agreement across
inlet-owning ranks. It also compares rho/Cp/Cv to a small serial reference at
relative tolerance 1e-12. Plan validates without writing; apply emits the combined
CSV consumed by inlet finalization. It does not change thermophysical formulas.

The runner first creates a 112-cell fixture with identical inlet states and
species data, using `fixture-plan|fixture-apply FIXTURE 4 --fixture-source CASE`.
It compares serial and four-rank outputs before starting the 32-rank probe.
After inlet velocities are finalized and primitive fields mapped, OF8
`decomposePar -fields` refreshes processor fields using the existing mesh split.
This avoids leaving zero placeholder inlet velocities on processor boundaries.

Verification: serial/four-rank/32-rank density, Cp and Cv comparisons; generated
processor inlet velocities; normalized mapped fields; MPI solver startup.
Expected result: reference comparisons pass before integration begins. This
change addresses the serial thermodynamic initialization; mesh construction and
OF8 mapFields remain separate preprocessing utilities.

Timing uses Bash built-in `time` (wall/user/system seconds); the pinned image
does not provide `/usr/bin/time`. Observe memory through scheduler accounting
or a separate process measurement, not these timing files.

## Replay a qualified mapped initial state

`replay.py plan|apply SOURCE_JOB NEW_JOB` reuses a checked fine-grid time-zero
state after an allocation proves too short. It copies mesh, dictionaries and all
32 processor initial fields into the new job, verifying file hashes, and records
the source executable hash. It does not recover unsaved in-memory progress or
rerun the expensive mesh/property/mapping preparation. Inputs must be sibling
numeric job directories inside the project root. Existing destinations are refused.
The source must have passed mapped-field and inlet checks. No credentials are read.

`run_replay.sh RELEASE NEW_JOB SOURCE_ID` runs through validation stage
`dev-replay-SOURCE_ID`, using the source job's immutable executable and qualified
library build. The target remains 10 microseconds, maxCo=0.2 and maxDeltaT=1e-6 s.
Checkpoints are written every 1 microsecond with two retained; runtime control
rereading is enabled. Adjustable output alignment can change individual time steps.
Verification: read-only plan, copied-file hashes, initial processor-field/inlet
checks, 32-rank solver startup, intermediate output and endpoint checks. A replay
has a distinct job/source identity. Budget wall time from measured step costs.

## Checkpointed steady-flow continuation

`continue.py plan|apply SOURCE_JOB NEW_JOB` prepares continuation of a successful
10-us replay. Plan can describe a pending dependency; apply requires PASS and
finite normalized endpoint fields, then copies and hashes the saved checkpoint,
mesh and dictionaries. It verifies the reused executable hash. Source and target
must be distinct sibling numeric jobs inside the project root. No secrets are read.

`run_steady.sh RELEASE NEW_JOB SOURCE_ID` runs through `dev-steady-SOURCE_ID`.
Submit with Slurm afterok on the replay job and a 48-hour allocation. The physical
ceiling is 0.05 s (five inverse-strain times), not an assertion that it is steady.
maxCo=0.2 and maxDeltaT=1e-6 s remain unchanged. Checkpoints every 1e-5 s retain
three output times; runtime controls remain readable. The watcher asks for a
write-and-stop after 46 solver wall hours, leaving time before scheduler expiry.
A later batch must start from the latest validated saved state, never time zero.

`steady_metrics.py CASE REFERENCE_ROOT REFERENCE_TIME CURRENT_TIME` compares all
cells on identical decomposition. Project-selected candidate criteria are a
minimum 0.01-s physical observation window, max temperature change <=1 K,
velocity-component change <=0.001 m/s, density change <=0.1% of reference peak,
pressure change <=0.001% of reference peak, and each species change <=max(1e-8,
0.1% of its reference peak). All 53 species must remain bounded/normalized,
T/p/rho finite and positive, peak T >1000 K, and total inlet/outlet phi imbalance
<=0.1% of inflow. These are proposed numerical stability criteria, not paper values.

`steady_watch.py` checks a safely older retained checkpoint, requires three
passing comparisons separated by >=0.001 s against the same reference, and then
requests stopAt=writeNow. A failed window saves a new reference and resets the
count. Comparing full fields also detects flame movement; it does not replace
centerline figure comparison, energy-balance assessment or mesh/time sensitivity.
An automatic stop is labelled a steady candidate, not scientific acceptance.
Reference copies and JSON measurements remain inside the job. Unexpected parsing,
field or solver errors fail explicitly; no automatic successful-convergence claim.

Verification: dependency/discovery plans; source/copy hashes; scheduled checkpoint
and solver startup; synthetic steady/change/mass-imbalance metric checks; shell
and Python syntax. Dependencies remain the environment runner, the existing field
reader and qualified solver/library. Restarted trajectories have not yet been
proved identical to uninterrupted trajectories because the solver rebuilds caches.

Local metric verification: `python -B test_steady.py NEW_SCRATCH_DIRECTORY`.
Expected output: PASS for short-window rejection, identical steady fields,
temperature drift, mass imbalance, reference-copy hashes and atomic stop control.
