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
