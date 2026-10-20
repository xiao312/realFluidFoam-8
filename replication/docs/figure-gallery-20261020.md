# Figure comparisons updated on 20 October 2026

The Lark gallery now groups results by target paper and figure. Liang Figures 1,
2 and 8(a) have separate entries before the Nguyen 2022 and 2025 figures.
Current ideal-gas CFD diagnostics belong to Liang Figure 8(a), Case 1.
They are not presented as completed real-fluid replication of Nguyen Figure 12.

Original images and caption resources were moved intact. Verification confirmed
all 54 original image tokens: 27 figures and their 27 caption images.
Current images and PDFs were replaced in place. Historical inlet-based spatial
plots, old initialization studies and duplicate diagnostic views remain in the
dated work log. Source and environment identity follow the comparison gallery.

## Current Cantera comparison

[Figure 8(a) section](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnSSnHgwGcFEVThXv7DJEXNf)
contains 65 points: five stages at 13 conditions each. Case 5 now uses the
corrected primary Takahashi Table 2 coefficient across the complete curve.
Cases 1–4 retain the earlier pressure-chemistry baseline. Their comparison errors
are unchanged. The input is `liang-figure8a-current-20261020.json` beside this file.

| Case | Compared points | RMS error (cm/s) | Maximum error (cm/s) | Outside screen |
|---|---:|---:|---:|---:|
| 1 | 11 | 0.01291 | 0.02611 | 0 |
| 2 | 10 | 0.01328 | 0.02552 | 0 |
| 3 | 10 | 0.00775 | 0.01620 | 0 |
| 4 | 10 | 0.01481 | 0.02550 | 0 |
| 5, corrected Table 2 | 11 | 0.06861 | 0.11966 | 3 |

The screen is `abs(error) <= max(0.05 cm/s, 1% reference) + image uncertainty`.
Case 5 fails at phi=1.30, 1.35 and 1.40. The largest relative difference is 2.12%.
The legacy coefficient's smaller error does not justify retaining the wrong table
entry. Publication parameter identity remains unqualified.

Fine-grid total-enthalpy diagnostics completed. Ideal partial-molar and pure-species
flux variants give identical profiles and 7.45755238 cm/s. At phi=1.10, smooth-SRK
Case 3 gives 7.02245326 and 7.01993913 cm/s. At phi=1.40, Case 5 gives 5.72790659
and 5.72572984 cm/s, versus digitized Liang 5.64273822. The rich discrepancy remains.

## Original-zero CFD snapshot

[Case 1 section](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnD4sxGHPxuts8zvttnmJrGh)
uses the frozen 09:45:20 CST snapshot. All native-family traces start from original
zero-time initialization. No new simulation or checkpoint continuation was submitted
during this document update.

| Phi=1.10 variant | Job | Time (microseconds) | T-front (cm/s) | OH-front (cm/s) |
|---|---|---:|---:|---:|
| Native | 124939663 | 300.018 | 7.35049 | 7.42768 |
| Current species enthalpy | 124939611 | 300.021 | 7.54552 | 7.61506 |
| Cantera transport | 124942608 | 299.992 | 7.39724 | 7.41369 |
| Cantera transport + CP chemistry | 124950538 | 194.942 | 7.28307 | 7.37987 |

The first three jobs completed; the last was running at capture. Endpoint values
do not establish steady or mesh convergence. The eleven-condition energy-corrected
sweep has nine completed jobs. Phi=1.00/1.15 timed out at 286.418/284.926 microseconds.
Their earlier CPU overlap was repaired without restarting either solver.

## Build and publication limits

Reported flames still use native library build 124657926. Temperature-inversion
draft c9b9e2e built successfully as 124957984. The old-library increment regression
124958247 failed 140/144 SRK and 143/144 PR checks. Corrected-library regression and
flame qualification remain pending. The new fix is not used in these plots.

The plotting change adds explicit stage labels to input JSON and the manifest.
The comparison keeps the original 204 × 175 point paper panel and caption.
The new labels identify corrected Table 2 without changing data or acceptance limits.
The phi=1.44 endpoint stays in data but is outside the paper's printed axes.

Verification: rendered the paper comparison, eight-history detail view and eleven-
condition history grid; inspected labels and legends; checked PDF page structure;
verified all original Lark resources, one current Figure 8(a) entry, and heading
hierarchy. The final Lark fetch confirms the current snapshot and updated attachments.
