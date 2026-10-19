# Ignition status and integration review

19 October 2026, 11:06 Asia/Shanghai. All four jobs for the three initialization
recipes were RUNNING. No restart, cancellation or executable replacement was
performed. The first target is 200 microseconds, not a convergence criterion.

| Recipe / job | Latest complete diagnostic time (us) | Tmax from heat monitor (K) | Eq.40 source-used speed, left/right (cm/s) | Instantaneous-source speed, left/right (cm/s) |
| --- | ---: | ---: | ---: | ---: |
| 1800 K, max dt 100 ns / 124862517 | 7.43198 | 3000 | 26.828 / 26.973 | 235.667 / 235.889 |
| 1800 K, max dt 50 ns / 124863132 | 6.98305 | 3000 | 27.850 / 27.655 | 254.283 / 253.825 |
| HP products / 124864929 | 68.5835 | 2235.287 | 5.524 / 5.523 | 26.982 / 27.002 |
| 1400 K / 124865412 | 0.141830 | 1399.837 | No OH contour | No OH contour |

Speeds use OH mass fraction 2e-5. The last log times are 7.47249, 7.01876,
68.7835 and 0.509737 us respectively; the cooler log is ahead of its ten-step
sampling cadence. Missing contours are not zero flame speed. The temperature
values come from the latest complete heat-release rows, not a new reconstructed
field analysis. The paper's phi=1.10 speed is approximately 6.8 cm/s from the
digitized image; it is not an exact tabulated reference.

The products case is closest on the source-used estimator (about 19% below the
digitized reference), but is not steady. Over the last approximately 6 us,
that estimator ranged from 6.01 to 5.52 cm/s. The OH-front kinematic estimate
using a linear position fit over that window is about 5.8 cm/s, while the
instantaneous-source estimator is about 27 cm/s. These remain explicitly
different discrete sampling stages; their disagreement prevents accepting the
apparent paper agreement. Left/right symmetry is good for this case.

The hot starts remain strong ignition transients, with much higher temperature
and large source-stage disagreement. Their actual dt is about 4.5 ns, well below
either configured cap, so changing the cap alone has not produced a useful
timestep-refinement comparison. The cooler case still has no usable OH isoline.
It has advanced only 0.51 us in about 32 minutes; adaptive dt is growing, so an
endpoint estimate from the initial average would be misleading.

The products case advanced about 18 us in the preceding 11 minutes. At that
recent rate, reaching 200 us would take roughly another 80 minutes. That is an
endpoint estimate, not a steady-state ETA. The hot cases' present rate would
not reach 200 us within their 24-hour allocation if it persisted. Preserve the
ongoing comparisons and reassess as ignition relaxes; do not accept a speed
merely because one estimator crosses the paper curve.

Raw snapshot: project-local state/heat-release-20261019/status-1106; immutable
job/source/library identities remain in paper-premixed-jobs-20261019.json and
chemistry-heat-release-20261019.md. Current production executable SHA-256 is
687a2f1494346bdfe9e64f52fdc1fd8cf6569dd9528538850e5401d3d13b6d8a.

## Standards review

Reviewed merge-base 99d64f7 through draft 17b0455, including premixed diagnostics,
initialization cases and heat release. No blocking documented-standard violation
was found: upstream is preserved, generated solvers and jobs are isolated, and
source/input/product identities and failed checks are recorded.

The nonblocking submission-identity finding was corrected: reservation rows now
include qualification stage as well as SHA, allowing both observer and native
checks from one revision. Legacy rows conservatively retain their duplicate
guard. Local verification covers repeated stages, different stages/revisions,
and legacy rows. Shell syntax, module unit tests and whitespace checks pass.

The restart limitation is now explicit: the flame-speed diagnostic refuses an
existing CSV, and the heat observer does not deduplicate across process restarts.
Any continuation needs separately identified histories and a restart check.
Repeated pinned fixture job IDs are a minor maintenance concern, not a hidden
production dependency or a reason to block this integration.

## Specification review

No blocking mismatch was found for the current laminar, one-outer-corrector 1-D
campaign. Native Qdot refreshes after combustion correction and supplies EEqn
without an extra chemistry solve. End-step diagnostics restore every species
rate. Signed MPI reductions and the declared ignition recipes match the scope.
The observer reads raw chemistry Qdot; equivalence with the combustion source
has been qualified for laminar combustion only, not PaSR/EDC or other closures.

Qualification 124868494 compared old/new binaries on an identical replay:
all 1,352 original field bodies and flame-speed CSV were identical, native Qdot
equalled the independent observer cell by cell, and source integrals passed.
Earlier diagnostics-on/off startup tests passed for all three recipes. The
new solver hash is a1f5630d29a57237f060551f683735e18c8f3d6fb98e393bbc3788ec5f8d93c4.
Post-qualification changes affect submission bookkeeping and documentation only.

## Integration decision

Low risk for source integration: merge the reviewed cohesive branch into the
sole develop/reacting line. This promotes the diagnostic and experimental case
capability, not scientific acceptance of a flame solution. The existing named
baseline and upstream solvers retain their behavior; the instrumented executable
is generated separately. No live binary is replaced by the Git merge. The
unresolved source-stage, ignition, timestep/domain and paper-agreement questions
remain qualification requirements for numerical results.
