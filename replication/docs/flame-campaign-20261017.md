# 2022 flame continuation preparation, 2026-10-17

The owner requested completion of the remaining 2022 numerical figures and matching
paper figure styles. Figures 8-11 require converged counterflow fields; Figure 12
requires developed premixed fronts and a phi sweep. No new converged result exists
at this checkpoint. The owner-selected compute cap is still pending.

## Prepared initial batch

| Configuration | Purpose | Ranks | Wall limit | Reserved core-hours |
| --- | --- | ---: | ---: | ---: |
| mpi-baseline | Compare same 320-cell/100-step case with serial pilot | 2 | 20 min | 0.667 |
| oxy-1-timestep | Fixed 1 microsecond step through 100 microseconds | 2 | 60 min | 2 |
| oxy-200-timestep | Same timestep test at 200 atm | 2 | 60 min | 2 |
| air-100-timestep | Same timestep test at 100 atm | 2 | 60 min | 2 |
| premixed-development | 400 cells, 0.1 microsecond step through 100 microseconds | 2 | 120 min | 4 |

Total worst-case allocation: 10.667 core-hours. Submit the MPI baseline first;
compare reconstructed fields against serial job 124660430 before subsequent jobs.
The larger timestep is an experiment, not a validated production setting. All
case physics remain SRK/rfJanaf/chungTaka, GRI30 and SEULEX. Fresh runs preserve
pilot records. Refinement, longer duration and sensitivity checks follow measured
results within the approved cap, not automatic assumptions of convergence.

The budget ledger conservatively reserves each job's full CPU-times-wall limit,
including failed jobs, and refuses a submission exceeding the explicit cap. The
read-only plan has no ledger side effects. Actual use can only release unused
reservations after accounting is inspected and recorded.

## Plot changes

Figures 8-11 now use the source crop dimensions in PDF points, Times typography
where available, corresponding panel placement and paper limits. Figure 8 uses
radius horizontally and axial distance vertically, hot temperature colours,
cyan streamlines and horizontal colourbars. Figures 9/10 retain species colours
and OH scaling. Figure 6 is resized to its source crop dimensions. Drawing styles
are close reconstructions, not pixel-identical originals. Startup status remains
visible, and out-of-range samples are explicitly counted rather than silently
misrepresented. These style changes do not establish new numerical replication.

Verification: five valid configurations and invalid timestep/rank/wall-limit
rejections; fresh premixed and counterflow generation; expected mesh/time/MPI
settings; Python and shell syntax; existing environment lock validation. No live
campaign or MPI scientific check has passed yet.

Owner authorization received during this session: use a 1,000-core-hour cap for
the counterflow replication work. This supersedes the pending-budget statement
above for the counterflow campaign. Initial priority is MPI correctness, then
counterflow timestep development and measured refinement. Premixed setup remains
prepared; do not let it consume the counterflow allocation without recording the
scope decision. All actual and worst-case reserved usage must be tracked.

The release archive a5ec7be0735dd1189b2f550bd3e9477907294591 was verified against
all 1278 Git blobs, staged under the SCNet trial root and passed the read-only
submission plan. Archive SHA-256:
`609195bea7e5dc203e7e50de7bd9298942f4d7bfbc0f8b4220d99c9f9ece6fad`.
The initial dry-run's 100-core-hour argument was illustrative, not approval.
The subsequent plan/apply uses the approved 1,000-core-hour cap.

MPI baseline job 124665381 completed in 194 seconds on two allocated CPUs
(0.10778 core-hours). The same-mesh reconstructed temperature relative infinity
norm difference from serial pilot 124660430 is 5.72e-10 (criterion 1e-5). Velocity
relative infinity norm is 3.69e-6. Pressure, density and species differences are
recorded in `mpi-comparison-20261017.json`. This passes the declared short-run MPI
check; it is not a steady-flame or strong-scaling result.

Next submitted jobs: 124665830 (oxy-1), 124665841 (oxy-200), 124665857 (air-100).
Each uses two ranks, 320 cells, dt=1e-6 s, endTime=1e-4 s, and a 60-minute wall
limit. Combined worst-case reservations including the MPI check are 6.667
core-hours. They were submitted only after inspecting serial/MPI agreement.

Prepared next hold point: same-mesh continuation to 1 ms, dt=10 microseconds,
eight ranks, 60-minute limits, source jobs 124665830/124665841/124665857. Each
continuation may be submitted only after its source passes field checks. This
larger timestep remains a stability/splitting experiment, not a validated setting.
Source fields and mesh hashes are preserved by the restart receipt.

Job 124665830 passed final field checks at 100 microseconds: T=1262.31-1780.16 K,
positive p/rho, maximum species-sum error 9.93e-13. It completed in 235 seconds
on two CPUs (0.13056 core-hours). It remains a developing coarse flow.
High-pressure two-rank cases have much larger chemistry cost per step. Identical
eight-rank repeats are prepared to measure scaling while preserving the two-rank
runs for direct comparison. No numerical settings other than rank count change.

A separate localized-ignition refinement branch is prepared with 8 radial by 400
axial cells (3,200 total), 16 ranks, dt=1e-6 s and endTime=1e-4 s. It uses cold
streams and a localized 1800 K ignition region around the analytical stoichiometric
mixture fraction of a tanh mixing layer; the initial strain velocity is based on
library-derived inlet speeds. No paper output curve is used to initialize fields.
The paper does not specify this ignition profile. Initial-condition sensitivity
must therefore be checked before accepting steady results. Uniform-hot runs are
retained. The localized branch changes initialization and mesh, not solver physics.

Local fixture checks confirm finite bounded temperature and species-sum error
1.11e-16. Actual OpenFOAM cell centres are used; no cell ordering is assumed.

The localized 3,200-cell oxy-1 job 124666858 passed field checks at 0.1 ms:
T=300.00-1730.58 K, species-sum error 1.28e-12. Its ignition has not yet developed
into the published steady flame. High-pressure localized jobs 124667801 and
124667802 were submitted next, reserving 16 core-hours each. Total conservative
reservations are 78.667 of the owner-approved 1,000 counterflow core-hours.
Two submission attempts on login04 failed before sbatch because python3 was
absent from PATH; explicitly loading apps/python/3.8.10 resolved the control
dependency. The simulation continues to use the pinned container's Python.

Next configurations extend the localized 3,200-cell case and uniform-hot
320-cell case to 10 ms with dt=10 microseconds. These are development experiments;
the different meshes prevent treating their comparison as a pure ignition-state
sensitivity test. They reserve 32 and 8 core-hours respectively if submitted.
Final fields are reconstructed completely for restart. Intermediate reconstruction
is limited to the twelve fields needed for figures/history; complete per-rank
output remains archived remotely. This changes I/O only, not the solver physics.

Jobs 124668179 (localized 3,200 cells) and 124668183 (uniform 320 cells) now run
the 10 ms experiments from source f3eb8daea5a2fbd5bf23b0c647566f382d8388e7.
Archive SHA-256 is 13478dbd3684322ccd81358df4c642a449e0e53c607e52edd1a8b8e051b9c5ce.
Reserved allocation is 118.667 core-hours; the first eight completed jobs used
5.93778 allocated core-hours according to Slurm CPUTimeRAW (not process CPU time).
Seven analysis archives were retrieved and verified against remote SHA-256;
complete raw fields remain in their remote job directories.

The longer high-pressure MPI comparisons fail the strict 1e-5 temperature
relative infinity-norm criterion: oxy-200 gives 2.88e-5 (0.0508 K), and air-100
gives 9.06e-4 (1.7495 K). The short startup MPI pass therefore does not qualify
these longer settings. Histories, all field differences and archive hashes are
in `counterflow-development-20261017.json`. Development runs remain useful for
cost/stability checks, but cannot establish replicated figures.

Diagnosis hypotheses, in test order: (1) rank-dependent stopping of intermediate
linear solves; setting their relative tolerance from 0.1 to zero should reduce
the difference; (2) splitting sensitivity; reducing dt should reduce it if the
linear experiment does not; (3) chemistry tolerances; tighter ODE integration
should reduce the difference if chemistry error dominates. The first experiment
repeats air-100 at two and eight ranks with only relative linear tolerance changed.
Absolute linear tolerance remains 1e-7, dt remains 1e-6, and chemistry is unchanged.
Writing only the final time reduces I/O, not the numerical integration.
The existing comparison is a deterministic postprocessing failure signal; full
solver replay takes minutes, an unavoidable exception to a seconds-only debug
loop. No solver-source fix is asserted before these controlled experiments.
