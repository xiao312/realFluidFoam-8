# Heat-release monitoring

Native field qualification: `submit.sh plan|apply ROOT IMAGE RELEASE native`
builds the premixed draft solver in an isolated job, replays the completed products
startup for one identical step with the old and new binaries, and compares all
original fields. The new `Qdot` must equal independently observed `Qdot_used` in
every cell; saved-field integrals must match the CSV. It does not deploy or restart
production. The existing observer-only command omits `native`. Each check reserves
eight cores for at most 30 minutes. Source, executable and library hashes identify
the result; a successful check establishes source-output equivalence only.
Reservation identity includes both source SHA and qualification stage, so observer
and native checks can run once each from the same revision. Legacy three-column
ledger rows conservatively block repeat submissions for their source SHA.

Observe the chemistry source used by the running premixed energy equation without
restarting or changing the solver, chemistry or time controls. This module owns a
loadable OF8 function object, scheduled qualification and a guarded controlDict
attachment. It does not reconstruct unsaved historical rates, change ignition,
or claim flame convergence. Branch ancestor: premixed-ignition c276385.

Inputs: qualified library build 124657926, existing diagnostic solver/cases,
explicit module revision and monitored case paths. `rfHeatReleaseMonitor` reads
the registered basicChemistryModel and calls its const Qdot() accessor only.
No chemistry solve/calculate/correct call is made. Qdot is -sum(Hf_i*RR_i), in
W/m3; RR contains integrated rates from the species solve. Positive heat release
and negative heat absorption remain signed. This is not instantaneous end-step
chemistry or total energy balance (diffusion/work terms are separate).

The function dictionary specifies type rfHeatReleaseMonitor, the absolute
container library path, crossSectionArea (1e-10 m2), and ordinary OF8 execution/
write controls. CSV rows every ten timesteps and field-write times record time,
dt, min/max Qdot, peak x, net/positive/negative integrated power, each half-domain
power, power per cross-sectional area, Tmax and pressure bounds. The total
includes both fronts; do not equate it with a single-front flame speed.
`Qdot_used` fields are written only at existing field-write times. CSV resides
in processor0/heat-release-used.csv. Data start at attachment; there is no
backfilled in-situ history. Startup time zero is skipped.
The observer does not deduplicate times across process restarts. Continue into a
separately identified case segment with fresh CSV paths; in-place history reuse
is not qualified. Its raw chemistry source equals the combustion source for the
current laminar model; PaSR/EDC or other closures need separate qualification.

Dependencies: pinned OF8/custom chemistry headers and libraries, wmake, MPI and
the contained Slurm runner. Dependents: flame comparison plots and project logs.
No credentials are read. Compilation and test runs occur only on compute nodes;
libraries, temporary state and evidence remain under the selected job directory.
Existing library products and solver binaries are never overwritten.
The qualification job's monitor-lib directory becomes a live runtime dependency
after attachment. Preserve that directory while any attached run remains active.

Verification: scheduled wmake and dependency checks; replay a copied completed
startup with the monitor on/off, compare all original written numerical field
bodies, and independently integrate saved Qdot_used values to check CSV totals.
Only after PASS may attach.py plan/apply CASE QUALIFICATION_JOB_DIRECTORY add the
monitor. It saves the original controlDict plus before/after hashes and uses an
atomic file replacement. It changes only a function-object entry. Reload happens
through the case's existing runTimeModifiable setting. Verify new CSV output and
absence of function-object errors in every live run. This is qualification of
an observer, not acceptance of a chemical model or simulation result.

`plot.py MANIFEST OUTPUT` consumes reviewed CSV snapshots through a JSON list of
`{job, label, csv}` entries. It exports signed heat-release, total power per area
and temperature histories with visible legends and input hashes. Sampling starts
at live attachment, so the figure never extends a curve back to ignition. Plotting
alone depends on the project's numpy/matplotlib analysis environment. Example:
`python plot.py histories.json OUTPUT`; expected outputs are PNG/PDF and provenance.
