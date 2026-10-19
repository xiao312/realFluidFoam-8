# Repeatable comparisons and paper figure styles

19 October 2026, Asia/Shanghai. Status: local workflow tested; scientific acceptance remains pending.

The suite gathers case preparation, probes, references and plotting into one reviewable checkout.
Use [the suite guide](../suite/README.md) and [case catalog](../suite/catalog.json) for the entrypoints.
Scheduler submission and Lark publication remain manual.

## Source assembly

The branch is `draft/replication-suite`, based on counterflow revision
`5ad5b643e4b73527be11d86f85bc135ba1e65c4d`.
It includes analysis commits `3b7d7f1` and `99d64f7` from `develop/reacting`.
The premixed module comes from `b54a8bf`; its existing runtime dispatch is included.
The historical profile extractor and plotter come from `99d64f7`.
The assembly changes no solver equations or library algorithms.
`develop/reacting` remains the sole integration branch; no draft was merged into it.

The initial analysis revision was `ac8e6f4d635e6648f4931ae09fbc1391a5ae6a0b`.
The latest completed-run review uses `d528bc09e8326e0df137284c3147fa816623265a`.
The checkout was clean during the final analysis. This record is a later documentation change.
Running releases were not edited or resubmitted.

## Reproduce the review

From the suite checkout, use the project's pinned analysis environment:

```sh
python -B replication/suite/run.py plan PROJECT PROJECT/state/replication-suite.local.json output/replication-suite-review
python -B replication/suite/run.py render PROJECT PROJECT/state/replication-suite.local.json output/replication-suite-review
```

Copy `campaign.example.json` to an ignored local configuration for another machine.
Set the read-only PDF paths and preserved evidence locations. Use a fresh output directory.
For a new solver revision, change the run identity and saved inputs together.
For a library revision, provide the new isolated build receipt and its hash.

Final local evidence is under `output/replication-suite-20261019-completed-v2` in the project workspace.
It contains 27 original figure/caption pairs, seven computed overlays, seven transparent
data layers, six standalone paper plots, three premixed diagnostic plots, an HTML gallery and a 27-page PDF.
Figure 8 supplies computed contours on the retained frame instead of a separate standalone plot.
`provenance.json` records 542 input hashes, source PDFs, plotting code hashes,
case releases, compiled-library source, product hashes and environment pins.

## Style verification

The overlay uses the original frame, with computed data mapped through measured axes.
No axial alignment, fitted scaling, curve smoothing or synthetic comparison points are used.
Standalone plots use the same geometry but reconstruct fonts and ticks; they are diagnostic plots.
The transparent layer allows another renderer to place the same data onto the original frame.

| Figure | Canvas, PDF points | Pixels at 360 dpi |
| --- | --- | --- |
| 2022 Figure 6 | 420 x 299 | 2100 x 1495 |
| 2022 Figure 8 | 255 x 348 | 1275 x 1740 |
| 2022 Figure 9 | 524 x 301 | 2620 x 1505 |
| 2022 Figure 10 | 524 x 302 | 2620 x 1510 |
| 2022 Figure 11 | 255 x 314 | 1275 x 1570 |
| 2022 Figure 12 | 255 x 151 | 1275 x 755 |
| 2025 Figure 6 | 390 x 248 | 1950 x 1240 |

All seven overlays retain 100% identical source pixels outside their data panels
and the measured new-legend bounds, including a small edge allowance. Rendering
checks this automatically. Original legends describe original data; each computed
image now has its own added-data key. The legend positions preserve the original
canvas size and avoid data and published labels. Dynamic premixed keys come from
the actual series, so a new campaign cannot inherit old job identifiers.
The original temperature insets are retained and excluded from the new main-panel layer.
The contour colour map is sampled from the paper colour bar. Temperature uses real mesh edges.
Streamline seeds and the raster figure calibration remain approximations.
The 2025 axis measurement uncertainty is about one embedded-image pixel, or 0.24 PDF points.

## Numerical and software checks

- Seven suite tests passed: calibration, containment, invalid data, missing OH, irregular-time tracking,
  inadequate history and catalog targets.
- The original 14 new or assembled Python modules parsed; the added premixed diagnostic module also ran in the completed review. Changed/imported shell entrypoints passed syntax checks.
- Environment-lock consistency and simulated Slurm spool dispatch passed.
- Premixed and paper-counterflow preparation plans passed without generating cases.
- Full analysis completed, rechecked its inputs and generated all declared outputs.
- The 27-page PDF was rendered for contact-sheet inspection; the comparison page was also checked at full size.
- The first legend render caught an edge-mask slicing error; clamping the verification mask to canvas bounds fixed it. The final run passed all seven frame checks.
- The first contour attempt rejected centroid roundoff during structured-grid lookup.
  The corrected lookup uses the established 1e-10 m grouping tolerance; field values remain unchanged.

The methane SRK/PR inversion failures remain 185/225 and 208/225 at a relative tolerance of 1e-6.
Nitrogen SRK/PR failures remain 873/901 and 901/901. Property agreement and inversion checks are separate.
The clipped methane Cp segments remain disconnected; unresolved 1-atm paper density is not numerically scored.
Counterflow errors are calculated against both published line series without extrapolation or axial shifting.

The latest review uses completed coarse oxyfuel endpoints at 70 ms for both pressures,
plus the prior 0.1 ms air smoke. The 200-atm near-axis temperature peak stays at
2.650 mm between 58 and 70 ms; its temperature changes from 2232.358 to 2232.132 K.
The paper's approximate peak is at 2.774 mm. The position mismatch persists.

All eleven completed Liang-inlet endpoints at 1 ms replace the historical two-run
illustration. The same fixed OH mass-fraction threshold, 2e-5, is used for every phi.
Fits cover 0.95–1.00 ms, using the actual six saved times; 100-microsecond fits and
threshold sensitivities remain in `data/metrics.json`. The former 5e-5 threshold
exceeds the final OH peak at phi=1.35/1.40, so it cannot represent the whole sweep.
Unavailable thresholds are explicitly rejected, without per-case substitution.
The largest OH change between 50/100-microsecond fits is 0.011 cm/s; the two front
methods differ by up to 0.671 cm/s. Short-window stability does not establish steady
burning velocity. Direct source-term evaluation and mesh/time/domain/seed checks
remain outstanding. The temperature-front diagnostic is visibly more variable.

| phi | Job | OH estimate, cm/s | Temperature-front estimate, cm/s |
| --- | --- | --- | --- |
| 0.90 | 124797642 | 4.8551 | 4.9690 |
| 0.95 | 124797644 | 5.4151 | 5.1637 |
| 1.00 | 124797648 | 5.8576 | 5.1863 |
| 1.05 | 124797650 | 6.2444 | 5.6040 |
| 1.10 | 124797651 | 6.3670 | 6.1347 |
| 1.15 | 124797654 | 6.2398 | 5.8492 |
| 1.20 | 124797656 | 6.0501 | 5.9717 |
| 1.25 | 124797657 | 5.8219 | 6.2237 |
| 1.30 | 124797665 | 5.6047 | 5.9336 |
| 1.35 | 124797666 | 5.4007 | 4.8668 |
| 1.40 | 124797667 | 5.1631 | 5.4586 |

All development endpoints use source `b54a8bf3297036e37e6c95732d25b7f8ab94b620`,
library build 124657926, and independently built `rfReactingFoam` products with SHA-256
`f2df3effff068d9acf08ee023dc73ec3137a619a32ceeed4b1539255b28e4f6e`.
The collected snapshot retains 6,204 individual field/addressing hashes, endpoint
receipts and source/build identities. Raw fields and plots remain outside Git.
All 22 Figure 12 estimate markers lie inside the source panel's limits.

## Scheduler status at 19 October 08:19 Asia/Shanghai

The eleven premixed jobs completed at 1 ms, and both coarse oxyfuel jobs completed
at 70 ms. All passed their finite normalized endpoint checks. Fine-grid replay jobs
124805217/124805218 timed out after three hours; all 32 ranks saved 9 microseconds.
Their 48-hour dependent jobs 124806101/124806108 were cancelled with Reason=Dependency
and never started. File sets are complete; field-level restart qualification remains
pending. None of these monitored jobs is running, and this update submits no jobs.

Local monitoring evidence is `state/status-suite-followup-20261019.json`; fine
checkpoint file discovery is `state/fine-checkpoints-20261019.txt`. These private
records remain in the project workspace. No steady-state result has been accepted.

## Lark publication

The existing inline comparison section now contains ten replaced computed images
(seven paper comparisons and three premixed diagnostics) and the new 27-page PDF.
All 27 original figure/caption entries and other resource tokens were preserved.
The top status and comparison register distinguish completed coarse/premixed runs
from stopped fine qualifications. The dated 18 October premixed PDF remains an
explicitly identified historical attachment. Publication was verified by a fresh
full document fetch; no duplicate comparison section was added.

Private receipts: `state/doc-revision-20261017/suite-completed-figure-verification.json`
and `state/doc-revision-20261017/completed-status-after.json`.
