# Adaptive checkpoint continuations

Continue the 17 stopped low-dimensional cases with the qualified OF8 executable.
This module changes time/output controls only; it neither changes chemistry nor
claims convergence or resolves the observed premixed temperature plateau.

Inputs: `cases.json`, project root, key, new job directory, smoke/full mode.
Configuration records origin job, case subdirectory, ranks, cells, initial dt,
maxCo, maxDeltaT, physical end time and output interval. All source paths resolve
inside the project root. Outputs are new decomposed cases, SHA-256 input records,
logs and checked checkpoint summaries. Original jobs are never modified. No
credentials are consumed. Dependencies: Python 3, the environment runner, qualified
build 124657926, Slurm/MPI and stopped checkpoints. Dependents: figure comparisons
and convergence assessment. Architecture remains in replication/docs/architecture.md.

`python3 -B prepare.py plan ROOT KEY OUTPUT smoke` discovers a common saved time
on every rank without writes. `apply` requires an absent output, copies the
checkpoint/mesh/dictionaries and changes only controlDict. It retains all 53
species and validates positive finite T/p, saved rho when present, and bounded
normalized mass fractions. Fresh stage-zero input may omit rho because the solver
computes it; endpoint checks always require positive finite rho.
`check.py CASE` validates the latest common output and reports T/CH4/OH changes
relative to the restart state. These changes are diagnostics, not acceptance tests.

Counterflow uses maxCo=0.2, maxDeltaT=2e-5 s, target GRI30 time 0.07 s, and saves
every 0.0005 s. Premixed uses maxCo=0.2, maxDeltaT=2e-7 s, target 0.001 s, and
saves every 1e-5 s. The temporal sensitivity case uses maxCo=0.1/maxDeltaT=1e-7;
the refined mesh uses maxDeltaT=1e-7 and maxCo=0.2. This changes the former fixed
half-dt experiment into an adaptive-controller sensitivity experiment. Initial
dt remains at the old small value; OF8 limits subsequent growth to 20% per step.

Smokes advance 0.0001 s (counterflow) or 2e-6 s (premixed), saving at their endpoint.
They qualify restart, controller operation and finite fields, not temporal accuracy.
Full runs require a passed smoke with identical case configuration and qualified
build (validator-only release changes are allowed), and use 48-hour
allocations. Submissions are recorded in an additional reservation ledger; owner
authorization on 17/18 October supersedes the initial 1,000 core-hour cap. All 17
full allocations reserve at most 3,840 core-hours, plus 40 core-hours for smokes;
jobs stop on reaching their targets. No unattended extension is installed.

The author's code reconstructs some caches at restart, notably species enthalpy;
these continuations are not guaranteed identical to uninterrupted trajectories.
Preserve this qualification until restart consistency is separately tested.

Verification: Python syntax, shell `bash -n`, discovery plan, then scheduled smoke
for every case. Logs must show deltaT increasing, successful End and field checks.
Use `writeControl adjustableRunTime` so saves are tied to physical time, retain
Euler time discretization, and do not substitute localEuler/LTS for physical time.
