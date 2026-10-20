# Liang Figure 8(a): seven comparisons and new clean-start campaign

The [current figure section](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnSSnHgwGcFEVThXv7DJEXNf)
contains one Cantera overview, one developed realFluidFoam solver overview,
and one comparison for each Case 1–5. Each individual comparison includes
only its digitized paper case and available computed data. Supporting time
histories follow the seven comparisons. The original panel and caption remain
beside each computed panel. Original panel dimensions are 204 by 175 points.

The developed-solver overview excludes stock reactingFoam and DeepFlame. Those
controls appear in the individual Case 1 plot. All CFD symbols show the latest
valid temperature-front speed relative to gas. They do not imply steady state.
There are no matched CFD results for Cases 2–5; the figures say so explicitly.

## Frozen evidence

The CFD snapshot was captured at 13:05 CST on 20 October. The constant-pressure
chemistry job 124950538 timed out at 221.942 microseconds. Its temperature/OH
speeds are 7.318467/7.382935 cm/s. Other curves retain the completed 300-microsecond
or explicitly labelled earlier controls. No history was spliced or restarted.

The plotting inputs beside this document are:

- `liang-figure8a-current-20261020.json`: 65 Cantera results, including corrected Table 2.
- `liang-figure8a-digitized-v2.json`: source PDF hash, calibration, paper data and image uncertainty.
- `liang-cfd-controls-20261020-1305.json`: solver controls, job IDs, sampled times and input hashes.
- `liang-cfd-sweep-20261020-1305.json`: eleven current-species-enthalpy Case 1 conditions.

Run `development/cantera-liang/figure_gallery.py plan|apply` with those four JSON
files, the original PDF, and a new output directory. The argument order is
PDF, Cantera, digitized reference, controls, sweep, output. The combined PDF has
seven pages. Cases 2–5 contain only paper and Cantera series. Their missing CFD
curves are not extrapolated from Case 1. Phi=0.90/1.44 are outside the printed
horizontal axis and remain in the manifest rather than being drawn outside it.

Verification checked seven pages, all series inclusion rules, nonempty series,
the original PDF hash, legends and rendered individual cases. Lark was fetched
after publication to verify each of the seven images occurs once.

## Temperature-inversion qualification: submission history

20 October, 17:30 CST amendment: build 125018291 completed and its small-increment
check passed, but property check 125018498 failed one of 450 states. Both startup
jobs and all eleven flames listed below were cancelled before execution. They
are historical submissions. The subsequent bisection fix passed 288 increment
and 450 property checks; two new short diagnostics use the qualified library.
See [the diffusion and inversion record](liang-diffusion-and-inversion-20261020.md)
for the current jobs, model variants and updated per-case figure inputs.

The first correction retained the final Newton update. Build 124957984 compiled,
but corrected-library checks 125003821 and 125003825 failed their unchanged
temperature error limits. That build is not qualified for this sweep.

The second draft also changes Newton's relative step tolerance from 1e-4 to
1e-9. Physical property models and the bisection fallback are unchanged. Source
`e1c86a38a32c9729bb55772e7059bfd2aa32e83e` is isolated on
`draft/temperature-inversion`; it is not merged into `develop/reacting`.

An initial archive attempt converted scripts to CRLF. Build 125004465 stopped
before library compilation; all dependent jobs were cancelled without running.
The replacement archive used `git -c core.autocrlf=false archive`. All 1,647
regular-file contents were verified against Git blob hashes before upload.

| Gate | New job | Dependency |
|---|---|---|
| Full native library build | 125018291 | None |
| SRK/PR small increments | 125018497 | Library build |
| SRK/PR property inversion | 125018498 | Library build |
| Eight-rank ideal mixture and 100-ns smoke | 125018502 | Both property checks |
| 32-rank ideal mixture and 100-ns smoke | 125018508 | Both property checks |

| Equivalence ratio | New eight-rank flame job |
|---:|---|
| 0.90 | 125018514 |
| 0.95 | 125018517 |
| 1.00 | 125018528 |
| 1.05 | 125018537 |
| 1.10 | 125018541 |
| 1.15 | 125018556 |
| 1.20 | 125018559 |
| 1.25 | 125018576 |
| 1.30 | 125018602 |
| 1.35 | 125018614 |
| 1.40 | 125018642 |

Each full flame depends on the eight-rank smoke, which also checks ideal-mixture
small increments. Failed dependencies cancel children. Runtime checks verify
the test receipts and their library identity before case creation.

Every case generates its original time-zero fields. There is no checkpoint
input, latestTime selection, or relabelling of saved fields. Each full case has
a 300-microsecond endpoint, a 12-hour wall limit and eight distinct CPU bindings.
The full sweep has a worst-case allocation of 1,056 core-hours. A longer wall
limit prevents the earlier eight-hour truncation; it does not prove convergence.
The 32-rank smoke is diagnostic and does not authorize 32-rank full runs.

## Remaining CFD model coverage

The current Cantera-CFD bridge accepts only Case 1. It supplies conductivity,
diffusion, and optional constant-pressure chemistry. Native CFD thermodynamics
still supplies density, compressibility, sensible enthalpy and heat capacity.

| Case | Missing matched CFD implementation |
|---|---|
| 2 | SRK density and pressure derivatives consistently used throughout the pressure and continuity equations, with ideal calorics |
| 3 | SRK calorics, energy inversion and species diffusion enthalpy consistent with the selected Cantera model |
| 4 | The same Case 3 model plus the qualified dense-conductivity increment |
| 5 | The same Case 4 model plus corrected Takahashi diffusion |

These cases are not submitted under misleading model labels. Each requires
frozen-state property checks and energy/pressure coupling qualification before
a flame sweep. Cantera's complete staged curves do not establish equivalent
CFD implementations. The nonideal Case 5 rich-flame discrepancy and CFD steady,
mesh, time-step and domain convergence remain unresolved. No new 2-D campaign
is launched from this 1-D qualification record.
