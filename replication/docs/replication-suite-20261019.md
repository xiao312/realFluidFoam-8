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

The tested analysis revision is `ac8e6f4d635e6648f4931ae09fbc1391a5ae6a0b`.
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

Final local evidence is under `output/replication-suite-20261019-final` in the project workspace.
It contains 27 original figure/caption pairs, seven computed overlays, seven transparent
data layers, six standalone plots, an HTML gallery and a 27-page PDF.
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

All seven overlays retain 100% identical source pixels outside their data panels,
excluding a three-pixel frame-edge allowance. Rendering checks this automatically.
Original legends still describe original data; each gallery/PDF caption explains the added data.
The original temperature insets are retained and excluded from the new main-panel layer.
The contour colour map is sampled from the paper colour bar. Temperature uses real mesh edges.
Streamline seeds and the raster figure calibration remain approximations.
The 2025 axis measurement uncertainty is about one embedded-image pixel, or 0.24 PDF points.

## Numerical and software checks

- Seven suite tests passed: calibration, containment, invalid data, missing OH, irregular-time tracking,
  inadequate history and catalog targets.
- All 14 new or assembled Python modules parsed. Changed/imported shell entrypoints passed syntax checks.
- Environment-lock consistency and simulated Slurm spool dispatch passed.
- Premixed and paper-counterflow preparation plans passed without generating cases.
- Full analysis completed, rechecked its inputs and generated all declared outputs.
- The 27-page PDF was rendered for contact-sheet inspection; the comparison page was also checked at full size.
- The first contour attempt rejected centroid roundoff during structured-grid lookup.
  The corrected lookup uses the established 1e-10 m grouping tolerance; field values remain unchanged.

The methane SRK/PR inversion failures remain 185/225 and 208/225 at a relative tolerance of 1e-6.
Nitrogen SRK/PR failures remain 873/901 and 901/901. Property agreement and inversion checks are separate.
The clipped methane Cp segments remain disconnected; unresolved 1-atm paper density is not numerically scored.
Counterflow errors are calculated against both published line series without extrapolation or axial shifting.

The style review uses saved coarse counterflows at 70 ms and 58 ms, plus the prior 0.1 ms air smoke.
It does not present the running paper-grid jobs as converged results.
The premixed illustration uses two historical cancelled inlet-guess runs at phi=1.10.
Their finite-time OH estimates and temperature-front crosschecks are regenerated from actual saved times.
It does not present an inlet guess as a measured flame speed or fabricate the remaining phi sweep.
Direct source-term evaluation, convergence and mesh/time/domain sensitivity remain outstanding.
