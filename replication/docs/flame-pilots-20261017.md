# Laminar startup pilots — 2026-10-17

All four bounded startup pilots passed mesh checks, selected ode/seulex, reached
1 microsecond, and passed final finite-property and species-sum checks. These are
execution and setup results. No steady counterflow profile or premixed flame
speed has been established.

| Case | Job | Cells | Slurm elapsed | Final T range (K) | Max species-sum error |
| --- | --- | --- | --- | --- | --- |
| CH4/O2-CO2, 1 atm | 124660430 | 320 | 3 min 42 s | 1790.671–1800.367 | 9.09e-13 |
| CH4/O2-CO2, 200 atm | 124660583 | 320 | 4 min 34 s | 1794.674–1803.120 | 9.45e-13 |
| CH4/air, 100 atm | 124660669 | 320 | 5 min 14 s | 1781.188–1801.194 | 1.40e-12 |
| Premixed CH4/air, 100 atm, phi=1 | 124660912 | 200 | 2 min 16 s | 298.000–1809.895 | 6.33e-13 |

Each job reserved two CPUs with a 30-minute limit and ran one solver process.
All exited 0:0. The four allocations consumed approximately 0.526 CPU core-hours
by allocated CPUs multiplied by elapsed time; this is not a billing quotation.
Solver wall time for the 1-atm counterflow was 197 s for 100 steps, excluding
setup. Its species sum criterion was 1e-8. Positive T, p and rho were checked;
the species-sum check is not an integrated conservation balance.

## Inputs and reconstruction

All pilots use the unchanged upstream solver compiled in job `124657926`,
SRK/rfJanaf/chungTaka, pinned 53-species GRI30, `ode`/`seulex`, and fixed dt=1e-8 s.
The counterflow source is `9c97b9d5f09a6fbb9bd2b241afcfc5806859ba70`; the premixed
source is `f66a0a00dda187d0e58c5a08cc3145e9be32fe66`. Build-product hashes and
custom-library resolution were verified before each run. Input and execution
details live in `validation/flames/README.md` and the per-job receipts.

Counterflow pilots use eight radial by 40 axial cells and a uniform 1800 K,
50/50 mass mixture of the inlet streams as a declared startup state. This is
far coarser than the paper mesh and is not a developed flame initialization.
Inlet densities come from the compiled thermophysical model. At 1 atm, the
resulting fuel and oxidizer speeds are 0.4680652194 and 0.5319347806 m/s; these
match the author's tutorial to its printed precision and give strain 100/s.
The 200-atm oxy-fuel case uses the same strain/equal-momentum constraint with
its 5 mm domain. The 100-atm air case instead uses 1 m/s fuel speed and matched
mass flux, following the cited 2017 case 6.

The premixed pilot reconstructs a 2 mm planar domain with 10 micrometre cells,
298 K unburned mixture and a central 0.2 mm, 1800 K ignition region. These domain
and kernel choices are not supplied by the 2022 paper. Pressure uses the OF8
waveTransmissive condition with unburned Cp/Cv=1.560461913 from the runtime
library, constant far-field pressure and a declared 2 mm relaxation length.
The unburned density is 113.1464034 kg/m3. The boundary model's constant gamma
and the domain/kernel choices need sensitivity checks. A 1-microsecond run does
not demonstrate non-reflection or two developed flame fronts.

## Qualification limits and next work

The baseline property inversion failures remain open; no upstream numerical
correction was made. Full source comparison against the upstream pin confirms
no changes under `src/` or `applications/`.

Before claiming replication, obtain converged profiles, perform timestep and
grid studies, reconcile reference data, and calculate the specified density-
weighted OH displacement speed. The [next batch plan](next-batch-plan.md)
describes MPI correctness/scaling and budget accounting. Its compute cap is
awaiting the owner's choice; the successful pilots do not authorize an unbounded
paper-resolution campaign by inference.

Raw pilot cases, fields, logs and scheduler receipts are retained in
`results/flame-pilots-20261017-evidence.tar.gz` under the SCNet trial. Its verified
hash is recorded in the project ledger and artifact manifest. Reproduce a pilot
using `validation/submit.sh plan` then `apply` with the corresponding stage,
source release and build job; see the validation module README.
