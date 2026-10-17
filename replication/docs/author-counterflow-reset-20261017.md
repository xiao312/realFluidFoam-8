# Counterflow baseline reset, 2026-10-17

The owner requested cancellation of the reconstructed campaign and adoption of
the original OF6 counterflow examples using our existing qualified OF8 solver.
The baseline is now the 1-atm tutorial from `realFluidThermophysicalModels-6`
revision `61f86014ef3f4277d04a348c83777d6a20d24cf3`, not a new OF6 solver build.

## Previous runs preserved

Only job **124668502** remained active when inspected. It was cancelled and
Slurm confirmed `CANCELLED by 248796`, 2,352 elapsed seconds on eight CPUs,
18,816 allocated CPU-seconds. Jobs 124668183, 124668512, 124668515, 124668519
and 124668521 had already completed. No result files were removed or overwritten.
Previous reservations remain charged; no unused allowance was reclaimed.

## Adopted case

- 1 atm methane versus O2/CO2; original inlet temperatures, velocities and fractions.
- Original 5-degree wedge, 20 mm radius and separation, 80 radial by 140 axial
  cells in three blocks: 11,200 cells.
- Original inletOutlet temperature/species and total-pressure outlet conditions.
- One-step EulerImplicit initialization from the original 2,000 K CO2 state,
  run to 0.13 s; then GRI30/SEULEX for a further 0.07 s with its own time reset.
- Original fixed 1 microsecond timestep; GRI30 absolute/relative chemistry
  tolerances 1e-8/0.1; original discretization and linear tolerances.
- Eight radial MPI partitions. No recomputation or rounding adjustment of the
  original prescribed inlet velocities or species fractions.

The 200-atm oxy-fuel and 100-atm air reconstructions are no longer active baselines.
The author tutorial does not supply separate instances of those cases. Any later
extension will be a declared change from the established 1-atm case.

## Compatibility and provenance

The [module](../validation/flames/author-counterflow/README.md) stores 43 original
text inputs and byte hashes, excluding upstream meshes and compiled dynamic code.
Generation verifies all hashes before applying the documented OF8 dictionary
port. Solver and library remain the qualified build **124657926**, physics source
`48506de20ce67f35279c5347b09dcd86865a4c39`, in runtime
`openfoam8-rootfs-7d4e96e0b1a9`.

Transfer copies internal T, p, U and five shared species onto the identical GRI
mesh, preserves GRI boundary values and initializes additional species to zero.
GRI thermodynamics recomputes energy and density. The one-step enthalpy field is
not copied across mechanisms. This prescribed mechanism change is not evidence
of a steady flame or energy-equivalent chemistry representations.

## Verification record

Local preparation verified input hashes and generated both mechanisms. Shell
syntax checks passed. Imported whitespace is preserved under a scoped Git
attribute; authored files pass whitespace checks.

Smoke job **124671455**, source `e7b227b7f72269653f4a3e5b49e330b60a7a8157`,
generated the 11,200-cell mesh and loaded the one-step chemistry, but failed at
the first timestep because OF8 requests `YiFinal`; the OF6 dictionary defines
only `Yi`. Its 77 seconds on eight CPUs cost 616 allocated CPU-seconds.
The failure is retained. Revision `df45c2a6a859c23e8a8929d30314d72e7d7fe337`
widens the selector to `"Yi.*"` without changing tolerances. This revision also
checks finite velocity during transfer and preserves intermediate analysis fields
for full runs.

Smoke job **124671684** passed the one-step endpoint checks but failed when
decomposing GRI30: its original outlet `p0 $internalField` expanded to the newly
transferred volume-sized pressure field. The transfer now resolves original
uniform boundary aliases before replacing internal fields. Outlet pressure stays
101325 Pa, and the original outlet velocity initial value stays zero. This job
used 94 seconds on eight CPUs (752 allocated CPU-seconds); its outputs remain.

Smoke **124672292** then passed transfer and decomposition, but GRI30 startup
rejected the legacy `reversiblethirdBodyArrheniusReaction` type. OF8 registers
`reversibleThirdBodyArrhenius`. The adapter updates reaction type names, including
removal of the legacy `Reaction` suffix, without changing equations or coefficients.
This failed check used 105 seconds on eight CPUs (840 allocated CPU-seconds).

Smoke **124672539**, source `4c75ff5fdf0d8b5e4348df36cac085ffec0216a0`,
completed both ten-step mechanisms and the transfer: **PASS**. Slurm reports
183 seconds on eight CPUs, 1,464 allocated CPU-seconds. GRI endpoint internal
T = 1045.709–2126.334 K, p = 101197.830–101365.078 Pa, rho =
0.240956–0.413082 kg/m3; maximum species-sum error 9.03e-13. These are startup
checks, not steady flame predictions. The subsequent source change only increases
full-run checkpoint frequency; smoke settings and numerical physics are unchanged.

The smoke test runs only ten steps per mechanism. Passing it qualifies startup
and field transfer, not convergence or agreement with the paper. The full run
retains the original durations; its histories must still be evaluated before any
scientific result is accepted. All runs use the existing 1,000 core-hour cap.

The corrected GRI startup measured about 8.15 seconds per microsecond timestep
after the first step on eight CPUs. This is a startup observation, not a reliable
full-run cost prediction. If sustained, 70,000 steps alone would exceed 1,000
core-hours. The first full job therefore retains a 12-hour/96-core-hour bound;
GRI checkpoints are written every 1 ms instead of the tutorial's 10 ms. This
output-only change allows continuation from saved processor fields. Completion
of the original durations within the remaining budget is not guaranteed; review
cost and steady-state histories before additional reservations.
