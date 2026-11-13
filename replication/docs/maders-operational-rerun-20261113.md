# Maders operational rerun, 13 November 2026

Job127882841 is a fresh time-zero run of the reconstructed Maders Figure4 case.
It passed the earlier148ms failure region and reached174ms during inspection.
Long-time settling and agreement with the paper are still pending.

Executed source: a4058db5d4de4d799e79eea7fb6d7f82433c5c73.
FlamePilot adapter source:0d2a63b546e180facdb6f1c736077517daa5c78c.
Environment:f46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793.
The job uses8ranks/16GiB and a41400s allocation, with a39600s solver guard.
The new12hour operator window ends23:06:41Shanghai on13November. Prior use and
failed runs remain recorded. Famou execution remains deferred by the owner.

## Operational policy

The case selects one `boundsPolicy clamp` setting. Property queries saturate at
table endpoints. Split-source entry projects finite C into its local table interval.
An outward source event holds that endpoint for the remaining substep. These
operations are measured rather than treated as fatal roundoff violations.
The policy does not extrapolate chemistry or silently relabel a correction as reaction.
Strict mode remains available for targeted diagnosis; invalid tables and nonfinite
mathematical inputs remain errors.

Each source-stage evaluation reports affected cells, maximum C correction, signed
and absolute integrated rho*deltaC*V, endpoint events and maximum held duration.
These are weighted-progress mass measures, not loss of total mixture mass.
Repeated PIMPLE outer evaluations must not be summed as independent physical steps.

The case also removes excessive equation-solve precision. Pressure uses a normalized
residual tolerance1e-7 and relTol0.01; its final solve uses relTol0. The iteration ceiling
is200. Z/C use1e-10; velocity/energy use1e-9. Early observed pressure solves took
18–34iterations, whereas previous solves repeatedly reached1000. This is a changed
numerical protocol; the previous strict failure is not retrospectively passed.

## Collection and timing

Radial profiles at H10/H40mm and boundary mass flux are saved every5ms of physical
time. Full fields are saved every50ms. Source, energy and continuity diagnostics
remain in the solver log. Bulk results remain on SCNet.

The allocated Node monitor updates convergence.json every60s of wall time. It
reports literature RMS errors at the fixed digitized coordinates from the start.
The reference hash is35ad9e70fdd63fc0284e28fa6a149ad419ce7cb700e19d1550be7a58d777b249.
It also reports recent source-bound statistics and pressure iteration-ceiling hits.
The sampled line contains249valid points because its final requested point lies
outside the planar wedge boundary. The monitor uses this observed geometry.

The nominal domain traversal time is0.1m/0.23m/s=0.435s. This is a case estimate,
not a duration specified by the paper. The old148ms solution covered only about
one third of that nominal time. Solver residuals or a matching peak temperature
alone therefore cannot establish sufficient integration time.

Our provisional temporal screen uses these predeclared criteria:

- Earliest eligibility: two nominal traversals,0.870s.
- Compare complete profiles against snapshots50ms and100ms earlier at both planes.
- Maximum temperature change:10K; maximum CO mass-fraction change:5e-4.
- Require three successful checks spaced50ms apart, giving earliest success near0.97s.

The screen does not use paper RMS error. It can identify a settled but incorrect
solution. All startup and failed snapshots remain available for comparison.
After a successful screen the monitor requests `stopAt writeNow`; the original
and modified dictionary hashes are retained in a stop receipt. Actual graceful
OpenFOAM termination remains to be observed when the solution settles.
Otherwise the simulation targets1.5s within the allocation. Unsettled or oscillatory
results must be reported as such; do not select a transient frame for a better fit.

Before calling the physical case qualified, also inspect mass/energy histories,
the importance of bound corrections, profile shapes and later numerical sensitivity.
Temporal settling, paper agreement, code review and human acceptance remain separate.

## Checks completed

The library and solver were rebuilt in the allocated f46 environment. LibrarySHA:
1b0c27e3d4d458c2dfb9a70c7f517f65cd543c6e578dbfd28fd1d21ec666b897.
SolverSHA:4af6cf340aae500df15c32cae1c2a6cca5e8c4f15ca43483103224cc7ba0d6b8.
Smooke runtimeSHA:1ec0e04b2f01b06b344a920222625061f0c20df544ccd16d3ceebb4baa1cdd93.

The actual reader replayed job127801087's failing C=0.17343764148411 and bounded
it to0.17343752899662626. Strict diagnostic rejection, finite endpoint behavior
and invalid-input rejection also passed. Mesh checking, actual runtime Ha/Smooke
initialization at time zero and MPI8sum28 passed before simulation.

The monitor was tested on the retained30time history and reproduces its literature
metrics. Two focused logic tests check startup/steady/moving profiles and covered
reference coordinates. A clearly synthetic constant-profile control tested the
graceful-stop dictionary request; it is not physical validation.

At roughly174ms the simulation recorded98corrected cells in a second-half
evaluation, maximum deltaC1.92e-5 and absolute weighted-progress correction2.72e-16kg.
There were66endpoint holds. These remain visible while the case continues.
The previous roundoff-only policy would have prevented collecting this evidence.

At approximately90ms, new versus old saved profiles differ by at most1.13/4.28K
at H10/H40mm. The corresponding maximum CO differences are3.98e-5/5.79e-4.
The saved times differ by16.6microseconds. This early comparison is not a formal
timestep or tolerance-convergence study. The90ms paper RMS errors remain313/837K;
the solution is visibly transient and is not claimed as a match.

Operator inputs, requests, hashes and retained data are in state/maders-coflow-20261112.
The simulation uses cases/maders-cfd-r12 and build/maders-cfd-r12 under its recorded
project trial. No evolved CFD state was imported. Only unchanged compiled Smooke
code and the frozen physical table were reused. The source archiveSHA is
b2baaedf71fb86f4ec6a74ec8fdc13a706f92e9ea8c34553b71e340b0ed9ac11.

The local ladder now includes the200ms snapshot and41saved-time histories, with
the previous strict run retained as a separate view. Its temperature RMS errors
are345.59/700.29K at H10/H40mm. It remains a transient diagnostic, not agreement.
The source view and plot hashes retain their distinct executed/postprocessing identities.

## Terminal follow-up — 13 November 2026, 14:50 Asia/Shanghai

Job 127882841 completed normally at 13:42:03 Shanghai, exit 0:0, after
9147 seconds on eight ranks (20.33 allocated core-hours). Executed source remains
a4058db5d4de4d799e79eea7fb6d7f82433c5c73. The monitor requested stopAt writeNow
at 0.97002670227 s, and the solver ended at 0.97323097463284 s with exit 0.
This qualifies the real graceful-stop path; earlier synthetic controls alone did not.

All 195 saved profile times were collected. Three consecutive checks at approximately
0.870, 0.920 and 0.970 s passed the predeclared temporal screen. Maximum changes
across the final 100 ms were 0.0122/0.0301 K at H10/H40 and
9.85e-7/3.07e-6 CO mass fraction. These are time-settled measurement-plane profiles,
not proof of global exact stationarity or mesh convergence.

| Quantity | H10 mm | H40 mm |
| --- | ---: | ---: |
| Temperature RMS against digitized detailed reference, K | 346.97 | 696.84 |
| CO mass-fraction RMS | 0.010592 | 0.020744 |
| Computed peak temperature, K | 2014.26 | 2039.77 |
| Computed temperature-peak radius, mm | 6.625 | 5.962 |
| Reference temperature-peak radius, mm | 7.624 | 9.695 |

The remaining mismatch concerns profile position and width, especially H40; peak
temperature alone is misleading. More run time is no longer the main explanation.
The next investigation should audit inlet velocity interpretation, transport/table
assumptions and spatial discretization against the paper. No particular cause is
established and no new run was submitted during this status inspection.

Bounds corrections remain measured, not hidden. The final second-half source
stage bounded 463 cells, maximum deltaC 1.4007e-5, absolute weighted-progress
correction 6.749e-17 kg and 31 endpoint holds. These are stage-evaluation values;
they must not be summed across repeated PIMPLE evaluations as independent physical
steps. Final caloric closure maximum relative residual was 5.12e-16 and no invalid
state was reported. The monitor's optional energy-state field is null because its
log prefix differs from the actual `energyState` prefix; raw energy records remain
available. This reporting defect does not affect the profile-screen decision.

Terminal profile archive SHA256:
92df5e4bf4be504f4b2bdbf07d5063632a5b23f85792bd5d670f0d85ec6160c6.
Retained evidence: state/maders-coflow-20261112/r12-terminal-convergence.json,
r12-terminal-solver-tail.log, r12-convergence.json.stop-receipt.json,
comparison-r12-0970 and history-r12-terminal. Remote evidence remains in
results/maders-cfd-r12 under the registered SCNet trial. Final raw fields remain
on SCNet. Only profiles and small records were retrieved.

The local Forge target now shows the final paper-lines/CFD-markers comparison,
195-time history and previous failed strict run. All 71 targets, 12 papers and
captions are retained. Comparison/history metrics agree exactly; all three view
images passed HTTP and content-hash checks and the final figure was visually
inspected. The temporal-screen flag does not grant independent science review,
human acceptance or public publication. Famou remains deferred.
