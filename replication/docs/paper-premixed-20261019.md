# Central-ignition premixed experiment

19 October 2026, Asia/Shanghai. The owner selected Nguyen's central-ignition
method as the next primary 1-D replication experiment. The inlet/half-products
campaign remains a separately identified comparison. `develop/reacting` is
still the only integration branch; this work is isolated on
`draft/premixed-paper`, based on `99d64f7cab456488f35df2df9c01f2b1cb1be6d7`.

## Paper recheck and implementation decisions

Primary evidence: supplied Nguyen et al. 2022 PDF, Section 5.3 p.11 and
Section 4.2 p.9, [DOI](https://doi.org/10.1016/j.cpc.2021.108264). A second
source review checked these sections and the pinned laminar chemistry source.

| Item | Implemented value | Authority |
| --- | --- | --- |
| Mixture, pressure, fresh T | CH4/air, 100 atm, 298 K | Explicit §5.3 |
| Mechanism and property models | GRI30, SRK, realFluid-JANAF, Chung–Takahashi | Explicit §5.3 |
| Geometry and initiation | Full 1-D domain, central hot ignition, two fronts | Explicit §5.3 |
| Spacing | Uniform 0.5 micrometres | Explicit §5.3; measured flame thickness still needs at least 40 cells |
| Pressure outlets | waveTransmissive at both ends | Explicit §5.3 |
| Speed | OH Eq.(40), after ignition relaxation | Explicit §5.3; no quantitative relaxation time published |
| First equivalence ratio | 1.10 | Project diagnostic choice within Figure 12 range |
| Domain | 4 mm / 8,000 cells | Reconstruction; domain independence unproved |
| Ignition | Compact cosine temperature profile, 0.2-mm width, 1800-K peak at t=0 | Reconstruction; no sustained heating; fresh composition retained in kernel |
| Other boundaries / initial U | zeroGradient / zero | Reconstruction; no prescribed inlet |
| Air ratio / closure | 21/79 molar O2/N2 / N2 | Explicit project convention |
| Pressure BC parameters | gamma from runtime fresh Cp/Cv; lInf=4 mm | Reconstruction |
| Time / chemistry / coupling | maxCo=.1, initial dt=1e-10 s, max dt=1e-7 vs 5e-8 s; SEULEX 1e-8 absolute/1e-6 relative; one outer/two pressure correctors | Project choices, not claimed paper values |

The OF8 source differs historically from the publication's OF6 implementation.
This experiment keeps its existing equations and library products unchanged so
initialization and timestep effects can be interpreted independently of a patch.
The hot kernel is an initial perturbation, not an assumed equilibrium-products
state. Only later independence from kernel/domain choices can establish that
the reconstructed details no longer influence the reported speed.

## Source sampling and traceability

The numerical implementation is in
[premixed-paper](../development/premixed-paper/README.md). The initial runnable
source is `a6d35b7c721728b8694aa05845773a28984056ac`; library build 124657926
and the existing pinned image remain inputs. Later plotting/docs commits do
not change a submitted job's source identity.

The paper gives net mass production in Eq.(40), but not its discrete sampling
implementation. The registered chemistry model stores kg/m3/s directly.
`laminar::correct()` uses time-integrated rates by default; `calculate()` gives
instantaneous rates. Both are logged with explicit solver-stage names. Source
and diffusion contributions are kept separately; all species-equation diffusion
corrections are included. The diagnostic does not substitute the energy-equation
YVi field for the corrected species flux.

Each front is independently sampled at fixed OH=1e-5, 2e-5 and 3e-5. The primary
level remains 2e-5 from the earlier campaign. Fresh-state rho/T/p/U are sampled
on each side; the initial fresh density is also retained. Missing/ambiguous
crossings and contaminated fresh reference regions are marked invalid. Signed
speeds remain signed. Right-front Eq.(40) needs no sign reversal; its separate
kinematic cross-check does. No ignition or negative values are removed to make
a curve resemble Figure 12.

Every tenth timestep and every field write produces CSV samples. Field writing
uses `runTime` so it does not round adaptive steps to exact write intervals.
`plot.py` plots reviewed complete CSV snapshots without smoothing; source hash,
job, time range and invalid-row counts accompany PNG/PDF/SVG exports.

## Qualification and progression

Two startup jobs each compare ten identical fixed steps with diagnostics on
and off. The C++ manufactured-front test checks both flank signs, interpolation,
diffusion contribution, absent levels and retention of negative speeds. Only
after matching numerical field bodies, successful build/link and finite normalized
endpoints may production begin. These startup checks do not test flame convergence.

The first production pair targets 0.2 ms with eight ranks and a 24-hour limit
per job, at most 384 core-hours together. The pair changes only the timestep
cap. This first interval is a bounded diagnostic run, not the paper's unspecified
relaxation time. Follow-up length and kernel tests remain separate experiments.
Judge improvement using both-front consistency, stage/level sensitivity, travelling
profile evolution and comparison with the previous inlet case at comparable
relaxation. Do not infer successful replication from proximity of one sample
to Nguyen's approximately 6.8-cm/s digitized point.

## Launched jobs and first history

Both startup checks passed on 19 October: 124862114 (dt100 configuration) and
124862348 (dt050). Each compared 1,352 numerical field bodies with diagnostics
enabled/disabled and found no mismatches. Both passed manufactured sampling,
build/link, mesh and finite normalized endpoint checks. The 1-ns endpoint has
no OH contour above 1e-5; invalid samples correctly retain that status.

Production jobs 124862517 (maximum dt=1e-7 s) and 124863132 (5e-8 s) are running.
Their runnable source is a6d35b7, regardless of later analysis commits.
[Job evidence](paper-premixed-jobs-20261019.json) records source, binary hashes,
qualification results and the initial scheduler snapshot. Status is dated
evidence, not a live scheduler view.

The first plotted snapshot from 124862517 reaches 2.55899 microseconds: 84 rows
across both stages/fronts/levels, including 32 valid contour samples. CSV SHA-256:
`f3fc5a134187be26580d862f11c1ba0c568edf8e3dfe25d24fd89005edd28d02`.
Left/right curves nearly overlap. Large stage/level differences during this hot
kernel transient prevent interpreting the samples as a laminar burning speed.
There is no established improvement relative to the completed inlet case yet.

The existing Lark flame-speed section contains the first history and signed
contribution plot, with legends and an attached PDF. The history has a shared
symmetric-log speed axis, explicitly linear within +/-10 cm/s, and the full
recorded time extent including the period without valid contours. Markers keep
isolated samples visible. This diagnostic is not a replica of a paper time
history (none is supplied); Figure 12 retains the labelled inlet sweep.

At the next status check, job 124862517 reached 2.77554 microseconds and the
Courant controller reduced dt to 2.64 ns during ignition (peak T about 2851 K).
Thus the two maximum-dt settings alone are not a guaranteed twofold temporal
refinement: actual dt histories must be compared, and a maxCo refinement may
be required once the ignition response is understood. Do not extrapolate an
end time from the first few microseconds or call the cap comparison converged.
