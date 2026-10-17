# Expanded low-dimensional campaign, 17 October 2026

The owner authorized launching the remaining low-dimensional cases needed for
the 2022 paper comparison. This expands the single active original-input
counterflow run to the other two counterflow conditions and the premixed sweep.
All new allocations share the existing 1,000 core-hour cap. Runs are bounded;
their submission does not establish convergence or a completed paper replication.

## Source and case coverage

New case/runner release: `fecef1a844def139a6509687ed26310c988ca051`.
Archive SHA-256: `4b3add8dce340a7e9c367bb003bb94bddd5f730bb714d78afed840c93b3853f9`.
The solver and environment remain the qualified build `124657926`, source
`b1153ea9c64b9abf55f7be6c488549024c081279`, and the pinned OF8 container described
in [the project record review](project-record-review-20261017.md).
No `src/` or `applications/` source was changed.

| Paper comparison | Case coverage | Setup qualification |
| --- | --- | --- |
| Figures 8a and 9 | 1 atm CH4/O2-CO2, existing job 124672685 | Original OF6 tutorial, two chemistry stages; development mesh |
| Figures 8b and 10 | 200 atm CH4/O2-CO2 | Author tutorial adapted to 5 x 5 mm and runtime-density inlet velocities |
| Figure 11 | 100 atm CH4/air | Author tutorial adapted to 300 K streams and reference-case mass-flux constraint |
| Figure 12 | 100 atm, 298 K CH4/air; phi 0.90–1.40 in increments of 0.05 | 11 central-ignition cases, 0.5 micrometre spacing |
| Figure 12 sensitivity | phi=1.10, half timestep, half spacing with half timestep, and double domain | Separate configurations; no acceptance inferred before comparing results |

The two new counterflows retain the author's 11,200-cell mesh and numerical
settings, one-step initialization to 0.13 s followed by GRI30 to 0.07 s. The
original tutorial supplies only the 1-atm condition; the higher-pressure cases
are explicit adaptations. Counterflow paper-resolution refinement is still
required after obtaining developed states. Premixed cases use 4,000 cells in
2 mm (8,000 for finer or longer domains), dt=1e-8 s (5e-9 for the timestep/fine
tests), and a 1 ms target. Their domain length and 0.2 mm, 1800 K ignition kernel
are reconstructed choices. WaveTransmissive boundary sensitivity remains open.

## DeepFlame inspection

Inspected [DeepFlame revision 7cb3294](https://github.com/deepmodeling/deepflame-dev/tree/7cb3294b275525cb8829ada3d3fbc067ab9323eb)
and its [H2 and C2H4 planar flame examples](https://github.com/deepmodeling/deepflame-dev/tree/7cb3294b275525cb8829ada3d3fbc067ab9323eb/examples/dfLowMachFoam/pytorch/oneD_freelyPropagation).
The H2 dictionary uses a 40 mm domain with 880 graded axial cells and empty
transverse boundaries. Its documentation describes 60 mm, so the actual pinned
dictionary was used for this inventory. The examples invoke `dfLowMachFoam` with
Cantera mechanism files (`Burke2012_s9r23.yaml` or `Wu24sp.yaml`) and Torch enabled;
their Allrun scripts download neural-network models when absent.

These are useful planar-mesh and flame-structure examples but are not drop-in
cases for the 2022 methane experiment. We retain the paper's central ignition,
two outward fronts, real-fluid GRI30 model and pressure boundary type. No DNN
downloads, Cantera installation, DeepFlame executable or copied initial profile
is required. Figure 12 must be evaluated using density-weighted, gas-relative OH
displacement speed. A moving OH contour alone is not the laminar burning velocity.

## Verification and limits

Local preparation passed for both adapted counterflow conditions and the
phi=1.10 premixed case. Checks confirmed 100/200-atm initial pressure, the 5 mm
high-pressure oxyfuel domain, all eleven phi values, normalized premixed
composition and 0.5 micrometre spacing. Shell syntax and Git whitespace checks
passed. The full-case submission path requires a successful same-release smoke
receipt and reserves its maximum allocated core-hours under a file lock.

Startup checks were submitted for both counterflows and phi=0.90, 1.10, 1.40.
Each counterflow smoke tests both mechanisms and field transfer; each premixed
smoke tests the fine mesh, boundary finalization, ignition and ten solver steps.
Scheduled results and long-run identifiers are recorded below after inspection.

## Submitted runs and first observations

All five startup checks passed: oxy-200 `124674515`, air-100 `124674520`,
phi=0.90 `124674525`, phi=1.10 `124674530`, phi=1.40 `124674538`.
They passed mesh, solver completion and endpoint field checks; both counterflows
also passed one-step-to-GRI30 transfer. This is startup qualification only.
Slurm recorded COMPLETED, exit 0:0 for all five. Allocated elapsed times were
235/234 seconds on 8 cores for the counterflows and 82/75/92 seconds on 4 cores
for the premixed smokes (1.319 core-hours measured allocation in total).
The GRI30 inlet checks gave oxyfuel velocities 0.1107879/0.1392121 m/s (strain
100/s) and air-case velocities 1.0/0.6449237 m/s (matched mass flux). Final
counterflow species-sum errors were below 1e-12; pressures were in the intended
200-atm and 100-atm ranges.

At 18:07:27 Asia/Shanghai, all 17 longer runs below were RUNNING. The two new
counterflows had just started; the premixed runs had been running for 1–2 minutes.

| Case | Job | Cores | Wall-time cap |
| --- | --- | --- | --- |
| Oxyfuel 1 atm, original tutorial | 124672685 | 8 | 12 h |
| Oxyfuel 200 atm | 124674723 | 8 | 12 h |
| Air 100 atm | 124674728 | 8 | 12 h |
| Premixed phi=0.90 | 124674593 | 4 | 8 h |
| Premixed phi=0.95 | 124674594 | 4 | 8 h |
| Premixed phi=1.00 | 124674595 | 4 | 8 h |
| Premixed phi=1.05 | 124674598 | 4 | 8 h |
| Premixed phi=1.10 | 124674599 | 4 | 8 h |
| Premixed phi=1.15 | 124674601 | 4 | 8 h |
| Premixed phi=1.20 | 124674603 | 4 | 8 h |
| Premixed phi=1.25 | 124674604 | 4 | 8 h |
| Premixed phi=1.30 | 124674606 | 4 | 8 h |
| Premixed phi=1.35 | 124674607 | 4 | 8 h |
| Premixed phi=1.40 | 124674610 | 4 | 8 h |
| Phi=1.10, half timestep | 124674612 | 4 | 8 h |
| Phi=1.10, half spacing and timestep | 124674627 | 4 | 8 h |
| Phi=1.10, double domain | 124674633 | 4 | 8 h |

The total ledger reservation is 942.6667 core-hours, leaving 57.3333 unreserved.
This includes historical reservations, 14 core-hours for the five new smokes,
192 for the two new counterflows and 448 for the 14 premixed runs. The current
aggregate allocation is 80 cores. Reservations are conservative maxima, not
measured consumption; do not silently reclaim cancelled-job entries.
The machine-readable [job register](low-dimensional-jobs-20261017.json) records
each job's exact release and allocation. Lark revision 126 contains the updated
campaign table and resource-preservation checks: 62 images, four attachments and
27 comparison grids remain intact. The generated figures and PDFs have not been
replaced by results from these still-running jobs.

The base premixed runs initially cost about 3 seconds per 1e-8 s timestep:
phi=0.90 reached 3.2e-7 s with 100.33 s solver execution time, and phi=1.10 reached
2.3e-7 s with 72.26 s. At that startup throughput, 1 ms would take roughly
80–90 hours per base case, exceeding its 8-hour allocation. This is an early
cost estimate, not a forecast of later chemistry cost. Checkpoints are retained
every 1e-5 s; the first should be available around 19:00 if throughput holds.
The selected sensitivity runs may be slower still. No claim is made that this
batch will finish the full sweep or establish stationary fronts within the cap.

Review stability around 18:30 and the first premixed checkpoints around 19:00.
Use those observations to decide whether developed fronts are emerging and
whether a separately tested timestep change is justified. Any changed timestep
must use a new case revision and a comparison against the baseline; no live
control dictionaries were changed. Longer continuation requires budget accounting
and explicit reservations. Counterflow mesh refinement and premixed ignition/
boundary sensitivity remain necessary before scientific acceptance.

## When to inspect the original 1-atm run

At 17:57:38 Asia/Shanghai, job 124672685 had run for 24 min 2 s and reached
approximately 0.005032 s of one-step initialization. Recent throughput was about
3,600 steps per 1,000 wall seconds (dt=1 microsecond). A useful next checkpoint
is around 18:25–18:30 on 17 October, when the first 0.01 s output should exist.
At unchanged throughput, one-step completion would be around 03:30 on 18 October.
That is an extrapolation, not a convergence estimate; GRI30 has a different cost.
The requested/reported time limit is 12 hours, but one scheduler query returned
an earlier EndTime with TimeMin=01:10:00. Check live scheduler state rather than
relying on an overnight completion promise. No automatic continuation is installed.
