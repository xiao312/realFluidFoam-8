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
