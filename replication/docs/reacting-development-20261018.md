# Reacting solver development baseline, 18 October 2026

The owner selected a single development integration line, independent concurrent
drafts, a one-front inlet–outlet premixed benchmark and counterflow inputs as
close as available evidence permits to the author repository and paper.
The target is agreement with the published 1-D/2-D flames after numerical checks,
not fitting model parameters to a curve. Existing runs remain historical controls.

## Branch and experiment identities

| Role | Branch | Source pin | Meaning |
| --- | --- | --- | --- |
| Sole integration line | develop/reacting | d29e89d | Renamed upstream solver and development rules |
| Inlet premixed draft | draft/premixed-inlet | dca0602 startup; 4ae4c07 full-run gate | New case topology, same solver equations |
| Counterflow mesh draft | draft/counterflow-mesh | 7e78004 | Tutorial/paper variants and mesh checks |
| Historical replication | work/2022-replication | 59f63f8 | Existing upstream runs and monitoring |

`rfReactingFoam` starts as an exact source copy of upstream
`realFluidReactingFoam` (48506de), except source/target naming. Both draft solver
builds link the same qualified library build 124657926 / b1153ea. Each new binary
gets its own job-local path, build log, SHA-256 and ldd receipt. Draft branches
are not accepted versions. Their only promotion target is `develop/reacting`.
See [development contract](../development/README.md).
Draft PRs [#1](https://github.com/xiao312/realFluidFoam-8/pull/1) and
[#2](https://github.com/xiao312/realFluidFoam-8/pull/2) target this integration line.

| Initial experiment | SCNet job | Maximum reservation |
| --- | ---: | ---: |
| Phi=1.10, inlet 0.10 m/s; renamed/upstream comparison | 124779617 | 4 core-hours |
| Phi=1.10, inlet 0.20 m/s; renamed/upstream comparison | 124779619 | 4 core-hours |
| Three counterflow mesh builds/checks, no reacting solve | 124779822 | 8 core-hours |
| Phi=1.10, inlet 0.10 m/s, full development run | 124780751 | 192 core-hours |
| Phi=1.10, inlet 0.20 m/s, full development run | 124780755 | 192 core-hours |

Archive hashes: inlet dca0602 =
`60aa1f13cf9f34b100ad5868a75cb1c929303eea6e896a3ee268f2b9aae50ced`;
counterflow 7e78004 =
`429e883e1d6c10d94322ab2e4affcf68cd8776d272aab4c5fd588875502a1d29`.
All use the existing environment lock and project-contained release/job directories.
Inlet submissions use `premixed-inlet/submit.sh plan|apply ROOT IMAGE RELEASE KEY`
for the dca0602 startup runner and append `full SMOKE_ID` for 4ae4c07 full runs.
Mesh qualification uses `sbatch --partition=kshcnormal --nodes=1 --ntasks=1
--cpus-per-task=8 --time=60`, project-local chdir/output/error paths, and
`environment/job.sh ROOT IMAGE RELEASE validation 124657926 dev-counterflow-mesh`.
Read-only plans for all three meshes precede that submission.
The initial tests reserve 16 core-hours; the two full runs add at most 384,
for 400 core-hours total. Existing production jobs were not modified.
The full-run runner is implemented separately at 4ae4c07. It requires the same
solver source, generator/runtime code, configuration and seed as a passed
renamed/upstream startup comparison, and allocates at most 48 hours on 4 cores.
It starts from fresh half-domain fields, not a restart with altered internal caches.
Full archive SHA-256:
`80e66c389a66921a49472acdde5e2870b11ee8b882fcff8ed66443cad2f3e2e6`.

Both startup jobs COMPLETED with exit code 0, in 10 min 56 s and 11 min 21 s.
Each matched 676 written endpoint field bodies against upstream at 2 microseconds,
excluding FoamFile headers. All 53 species normalized within 1.42e-12; T/p/rho
were finite and positive. Named-solver maxima were 2229.534 and 2229.258 K.
This qualifies the rename and initialization, not flame speed. The full jobs
passed the source/seed/configuration gate before submission and target 1 ms.
The [development status snapshot](reacting-development-jobs-20261018.json)
records scheduler state, binary hashes and the available receipts.

## One-front premixed setup

The [pinned DeepFlame example](https://github.com/deepmodeling/deepflame-dev/tree/7cb3294b275525cb8829ada3d3fbc067ab9323eb/examples/dfLowMachFoam/pytorch/oneD_freelyPropagation)
uses an inlet–outlet planar mesh and two-state T/species fields. H2 has 500 cold
cells at 500 K and 380 hot cells at 2485.8 K on its 880-cell graded grid, with
inlet U=5.36 m/s and p=1 atm. C2H4 likewise has two T states, 500/2458.6 K.
These fuel/pressure/speed values are not transferred to methane at 100 atm.

Our first draft uses CH4/air, phi=1.10, 298 K and 100 atm, GRI30, SRK/rfJanaf/
Chung–Takahashi, 0.5 micrometre spacing, a 2 mm domain and 4,000 cells. Exactly
half start unburned and half start as equilibrium products, with one interface
at 1 mm. Inlet speed guesses of 0.10/0.20 m/s are initial controls, not measured
flame speeds or calibrated predictions. The front can drift in either laboratory
direction while retaining a single reaction front.

Seed calculation uses [Cantera HP equilibrium](https://cantera.org/stable/examples/python/thermo/adiabatic.html)
with NASA7 coefficients from the pinned author file and GRI30 element definitions.
The phi=1.10 seed is 2229.488981 K; ideal-gas relative enthalpy residual is
3.17e-14. All 53 mass fractions are normalized after conversion using the author's
molecular weights. This is ideal-gas equilibrium initialization, not an SRK
fugacity-equilibrium state. Real-fluid relaxation and seed-independence are required.
Cantera is an offline preparation dependency; the CFD chemistry remains unchanged.

The actual library inlet probe gives rho_u=112.7998489 and rho_b=14.5757235 kg/m3,
and hot-side Cp/Cv=1.24795248. Initial product velocities are 0.7738885 and
1.5477770 m/s so rho*U is equal on both halves. T/Y/U are fixed at the cold inlet
and zeroGradient at the outlet; p is zeroGradient at the inlet and
waveTransmissive at the outlet. Adaptive controls start at 1 ns with maxCo=0.1,
maxDeltaT=0.1 microsecond. Startup tests advance 2 microseconds, not a developed flame.

The 2022 paper section 5.3 instead describes central ignition, two propagating
fronts and nonreflecting pressure outlets at both ends. Its results remain the
target and its methodology remains a separate check. A successful inlet case
must give a stable, seed/domain-independent burning velocity and agree with the
central-ignition method before it can stand in for that paper experiment.

For a front normal pointing toward the cold left side, track a fixed OH level
on the upstream branch and its laboratory velocity v_f. Compare the local
density-weighted displacement speed rho_f/rho_u*(u_f-v_f), using consistent normal
and interpolation, with a fuel-consumption balance. Imposed U_in alone is not
a result. Test multiple fixed markers and developed windows; exclude ignition,
startup relaxation and boundary-affected intervals. Preserve signs and units.

## Counterflow fidelity

The repository's 80x140 wedge is a tutorial mesh, not Table 1 of the paper.
The new draft preserves a tutorial variant and adds a paper-informed variant:

| Condition | Radial spacing | Fine axial spacing | Cells |
| --- | ---: | ---: | ---: |
| Oxyfuel, 1 atm; 20x20 mm | 20 micrometres | 20 micrometres | 888,000 |
| Oxyfuel, 200 atm; 5x5 mm | 5 micrometres | 5 micrometres | 816,000 |
| Air, 100 atm; 20x20 mm | 20 micrometres, chosen | 5 micrometres | 1,978,000 |

Oxyfuel outer cells stretch to about 30/10 micrometres respectively, consistent
with Table 1. Air radial spacing, axial zone extents and stretch ratio are not
specified by the paper; the draft declares them as reconstructions. Confirm that
the entire flame lies inside the fine zone before comparison.

Paper oxyfuel uses exact 21/79 molar O2/CO2, 300/1000 K streams, strain=100/s and
equal momentum evaluated with actual library densities. The tutorial uses rounded
Y(O2)=0.162 and fixed 1-atm inlet speeds. Paper-side primitive outlet fields use
zeroGradient as described; tutorial mixed-backflow choices remain separately
available. Keep total-pressure outlet, original mechanisms, Euler discretization,
PIMPLE and chemistry tolerances unchanged in this case-only draft.

Local checks passed for all six variants and preserved fvSchemes byte-for-byte.
Large-grid flow is not launched merely because a mesh passes. The air chemistry
failure requires a separate diagnosis. Before expensive runs, qualify mapping,
memory, conservation, cost and mesh sensitivity; do not transfer the old tutorial
budget or blindly regenerate 130 ms initialization on every mesh.

## Next algorithm drafts

First qualify the renamed baseline and new case initialization. Subsequent draft
questions are separate: temperature inversion and restart consistency; refresh of
species-enthalpy caches; chemistry failure beyond the 0.1 ms startup test; and
the placement of species/enthalpy relative to the pressure correction loop.
Each needs an explicit reproducer, conserved-quantity checks and a comparison
against the same benchmark inputs. No equation or library correction is included
in these initial case drafts. Nothing here establishes paper reproduction.

## Latest scheduled checks

At 2026-10-18T16:21:23.541690+08:00, the two full inlet jobs were RUNNING and
had entered their CFD time loops. The two oxyfuel paper-informed meshes passed
checkMesh. The 1,978,000-cell air mesh was built and its checkMesh topology
inspection was still running; it is not yet qualified. Observed mesh-check peak
resident memory was about 2 GB, which does not estimate a 53-species reacting
run’s memory requirement. No large-grid counterflow chemistry run was submitted.
