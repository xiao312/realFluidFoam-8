# Controlled 1-D time-step study — 19 October 2026

Three fixed-step segments are running from one equilibrium-products checkpoint.
The aim is to separate time-step error from spatial resolution and chemistry
integration effects before expanding the paper's operating-condition sweep.
No flame speed is accepted. Original ignition jobs remain unchanged.

## Inputs and job identity

Parent integration: `bfa3bfdbf95df845e2a1ca1b7c95a469a77db045`.
Case/runner release: `191fd8fe16a53dfd6fbdf043364875119a329f11`.
Archive SHA-256: `594916d732bb3b6ab5e5972fe9b5245624de8ccadbbfe2b03f5031303f5f4b95`.

The donor is job 124864929, saved time `7.99834968798e-05` s.
All segments end at `9.99834968798e-05` s, a 20 us interval.
They retain phi=1.10, 100 atm, 298 K, 8,000 cells, 0.5 um spacing, and eight MPI ranks.
GRI30, SRK transport/thermodynamics, laminar combustion, and SEULEX settings are unchanged.
The ODE tolerances remain absTol=1e-8 and relTol=1e-6.

| Case | Job | Fixed step | Steps | Wall cap | Maximum reserved core-hours |
|---|---|---:|---:|---:|---:|
| dt100 | 124873143 | 100 ns | 200 | 2 h | 16 |
| dt50 | 124873144 | 50 ns | 400 | 2 h | 16 |
| dt25 | 124873146 | 25 ns | 800 | 2 h | 16 |

The qualified executable is `rfSpatialReactingFoam`, build 124870644,
source `a438f6414a1d2820cbc3de3c0a4d3336afa434db`.
Binary SHA-256: `e3ef56491e44c2dfdd79826805f992ed8220901643ac14554c38ca8e81e6b385`.
Library build: 124657926. Environment: the locked OF8 directory image
`openfoam8-rootfs-7d4e96e0b1a9`; see [environment lock](../environment/lock.json).
Each new job verifies the binary and library hashes before execution.

The three original input maps each contain 1,457 files and are identical.
Only copied time/output controls and diagnostic frequency change.
Input-manifest hashes are recorded in [the job register](premixed-sensitivity-jobs-20261019.json).
Fresh case paths prevent diagnostic-history overwrite. The donor remains read-only.

Raw results: `jobs/<job-id>/case/processor0/` under the configured project root.
Local transport receipts: `state/sensitivity-20261019/` in the operator project.
These outputs remain outside Git.

## Failure measure and experiment order

The recorded 75–80 us baseline fails the new diagnostic screen:

- Main left contour, YOH=2e-5: median instantaneous Eq.(40) is 26.970 cm/s;
  the source used in the OH solve gives 5.586 cm/s.
- The largest instantaneous median spread across three OH levels is 198.237 cm/s.
- The largest source-stage gap across both sides and all levels is 138.985 cm/s.

Command: `python -B replication/development/premixed-sensitivity/gate.py
DONOR_CSV --end-us 79.9834968798`. It returns `UNRESOLVED`, exit 2.
The 0.5 cm/s threshold is a declared diagnostic threshold, not a paper tolerance.
The fast check operates on recorded solver results; new CFD tests still require minutes.

Ranked explanations and discriminating tests:

1. Time integration or sequential equation coupling: reducing the flow step should
   change the source-stage gap on the same mesh. Compare 100/50/25 ns first.
2. Chemistry integration tolerances: a tighter SEULEX branch at a fixed flow step
   should change the result if chemistry error dominates. This branch is not launched yet.
3. Spatial gradients and interpolation: refining 0.5 to 0.25 um should reduce
   marker dependence if resolution dominates. Select its time step after this study.
4. Restart or persistent transient behavior: the restarted 100 ns branch can differ
   from the uninterrupted donor. Track that difference instead of assuming restart equality.

Compare the last 5 us after at least 2 us of segment evolution.
Retain both fronts and OH=1e-5, 2e-5, 3e-5. Compare signed instantaneous Eq.(40),
the actual OH-solve source, and density-weighted tracked speed separately.
Require changes below 0.5 cm/s between the finest steps, then evaluate stage/marker
agreement separately. Failure means the issue remains unresolved; it does not identify a cause.

Tracking fits dx_front/dt over the same window and uses local velocity and density:
left `rho/rho_u * (U - dx_front/dt)`; right `rho/rho_u * (dx_front/dt - U)`.
At the main contour in the 75–80 us baseline, laboratory outward motion is
44.831 cm/s; the corrected value is 5.826 cm/s. They are different quantities.

## Startup evidence and completion-check correction

At 12:18:38 Asia/Shanghai, all three jobs were RUNNING:

| Case | Physical time | Segment advance | Latest maximum Co |
|---|---:|---:|---:|
| dt100 | 89.2835 us | 9.3000 us | 0.08264 |
| dt50 | 85.8335 us | 5.8500 us | 0.04150 |
| dt25 | 83.0585 us | 3.0750 us | 0.02078 |

These are operational observations, not matched-window flame-speed results.
The initial step reduction has not yet demonstrated improved Eq.(40) agreement.
Estimated slowest completion: about 13:00–13:10, if the measured rate persists.

The copied `uniform/time` restores time index 854. The modulo-based diagnostic
interval therefore gives different output phases among the branches.
The original runner's final check incorrectly requires a CSV sample at the exact endpoint.
It is expected to report a postprocessing failure even if the solver completes.
The immutable release and running jobs are retained; their scheduler exits must remain visible.

Corrected checker release: `de62ba41edc08f3248df7871a1e8f13f3cb43920`.
Archive SHA-256: `d53351b5ccdff0f180b04112cf90b6f9cdca1ee0c452f25f0acb8da7207d2025`.
Qualification job **124873486** waits for all three jobs with `afterany`.
It reserves one core for ten minutes and writes a separate qualification record.
It requires the solver log to reach the endpoint, with diagnostics/fields covering
their last scheduled intervals. It checks finite fields, species sums, positive
temperature/pressure/density, Courant limits, and native Qdot extrema/integral.
Scientific disagreement remains a separate gate, even when operational checks pass.

The local comparison interpolates only within common physical-time coverage.
Raw curves and medians remain available. Interpolation does not add simulated data.
The saved time index is not reset, and no running numerical input is changed.

## Verification and next decision

Five local tests passed: source/marker failure detection, signed density-weighted
tracking, phase-aligned comparison, read-only case planning/copy preservation,
and completion detection with inherited output phase.
Shell syntax and whitespace checks passed. The plotting pipeline was exercised
on a duplicate donor history; zero pair differences confirmed pipeline consistency only.

Wait for the three equal-duration segments and the separate qualification receipt.
If 50/25 ns still differ materially, halve the step before refining the mesh.
If temporal changes are small but marker sensitivity remains large, qualify a
0.25 um mapped mesh at the selected step. Do not expand the phi sweep yet.
No solver or library equation change is included in this study.
