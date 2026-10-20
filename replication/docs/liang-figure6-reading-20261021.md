# Liang Figure 6: reading and transport comparison

21 October 2026, Asia/Shanghai. State: digitized and checked; scientific
comparison remains unresolved.

The paper's visible conductivity curve cannot be reproduced by reversing our
current conductivity ratio. Inversion gives the same side of unity, but remains
outside the reading uncertainty through most of the visible temperature range.
At 300 K, none of the 13 currently defined species mixture-diffusion ratios
matches the paper's red curve.

## Source and method

Source: Liang et al., *Proceedings of the Combustion Institute* 37 (2019)
1733–1739, [DOI 10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070).
Figure 6 is on PDF page 5, printed page 1737. The caption specifies a
stoichiometric hydrogen/air flame at 100 atm. Its printed labels are:

- Black solid: \(\lambda_{\mathrm{ideal}}/\lambda_{\mathrm{real}}\).
- Red dashed: \((PD)_{\mathrm{real}}/(PD)_{\mathrm{ideal}}\).

The figure is an embedded JPEG, PDF xref 72, 775 by 661 pixels; it has no
extractable vector curve. The original JPEG was extracted without resampling.
The page and individual image were visually inspected. Median colored-pixel
positions were read column by column, excluding text and axes. Interpolation
between adjacent visible dash endpoints supplies red-curve samples in gaps.
`pixels.csv` preserves the observed positions separately from those samples.

Calibration uses these major-tick centers in original image coordinates:

| Quantity | Value | Pixel coordinate |
|---|---:|---:|
| Temperature | 500, 1000, 1500, 2000 K | x = 191, 377, 563, 750 |
| Ratio | 0.90, 0.95, 1.00, 1.05 | y = 604, 436.5, 269, 101.5 |

Least-squares axis mappings are \(x=0.3726T+4.5\) and
\(y=-3350r+3619\). A conservative three-pixel reading allowance combines
line thickness, pixel selection and axis calibration. It corresponds to
8.05 K horizontally and 0.00090 vertically. Sample ratio bounds include both
directions and the bounding dash endpoints. These are deterministic reading
envelopes, not statistical confidence intervals or model uncertainty.
Changing color thresholds shifted sampled ratios by at most 0.00015 for the
black curve and 0.00034 for the red curve, below those allowances.

The black curve is visible only from approximately 1155 to 1993 K. It exits
the panel at the top, whose calibrated ratio is 1.0803. **There is no
digitized conductivity value at 300, 500 or 1000 K.** The red curve is visible
from approximately 297 to 1977 K. No samples were extrapolated beyond either
visible curve.

## Readings

Selected samples; the state CSV contains all 24 samples and full precision.
Intervals reflect reading uncertainty and dash gaps.

| T, K | Black conductivity ratio | Red pressure-weighted diffusivity ratio |
|---:|---:|---:|
| 300 | Not visible | 0.9122 [0.9104, 0.9182] |
| 400 | Not visible | 0.9728 [0.9655, 0.9806] |
| 500 | Not visible | 0.9984 [0.9961, 1.0036] |
| 800 | Not visible | 1.0201 [1.0182, 1.0215] |
| 1000 | Not visible | 1.0252 [1.0239, 1.0266] |
| 1200 | 1.0704 [1.0676, 1.0731] | 1.0284 [1.0275, 1.0296] |
| 1400 | 1.0416 [1.0399, 1.0431] | 1.0291 [1.0282, 1.0301] |
| 1600 | 1.0278 [1.0263, 1.0294] | 1.0296 [1.0285, 1.0304] |
| 1800 | 1.0167 [1.0152, 1.0179] | 1.0316 [1.0301, 1.0325] |

The black curve crosses 1.05 at **1299 K**, with a reading envelope of
1287–1322 K. The red curve crosses 0.95 at **359 K**, with an envelope of
348–372 K. The envelopes include curve slope and dashed-line uncertainty;
they are wider than the horizontal pixel allowance alone.

## Comparison with saved calculations

The comparison uses `snapshot-0011/jobs/125069072/result/transport.csv`.
Its SHA-256 matches the earlier `snapshot-2309` transport input recorded by
the diffusion-definition check. Thus this snapshot is not a new flame state.
All comparisons interpolate saved data; no flame or property solver was run.

| T, K | Paper λ ideal/real | Current λ ideal/real | Current inverse, diagnostic only |
|---:|---:|---:|---:|
| 1200 | 1.0704 | 0.97833 | 1.02215 |
| 1300 | 1.0499 | 0.98059 | 1.01980 |
| 1500 | 1.0342 | 0.98407 | 1.01619 |
| 1800 | 1.0167 | 0.98750 | 1.01266 |
| 1990 | 1.0087 | 0.98901 | 1.01112 |

At 1200 K, inversion still misses the paper by 0.0482 in ratio, compared
with a reading interval only about ±0.0028. At 1500 K, the discrepancy is
0.0180, versus about ±0.0014. Over the nine selected visible black-curve
samples, unweighted ratio RMSE decreases from 0.06584 to 0.03142 after
inversion. This is a diagnostic comparison, not permission to relabel the
paper or a fitted correction.

The saved `conductivity-probe/states.csv` contains five flame-profile
mapping/reference/correction combinations. For their dense-increment form,
inversion gives RMSE 0.02896–0.03140 on these same nine samples. For the
full Ely–Hanley form, inverse RMSE is 0.11241–0.18539. None resolves the
visible discrepancy. These fixed variants were compared as supplied; no
parameters, temperatures or curve coordinates were fitted.

At the saved temperature 299.9983 K, `diffusion-definitions/ratios.csv`
contains all 13 species. Its minimum real/ideal ratio is **0.98219 for CO₂**
and maximum is **1.03651 for H₂**; all lie above the paper reading's upper
bound, 0.9182. The closest still misses by 0.0640 beyond that bound.
CO₂ has zero mass fraction at this sampled state, so this minimum is a
defined trace-species transport property, not evidence of a participating
diffusive flux. At equal pressure the pressure factors cancel in \(PD\)'s
ratio. The paper does not identify the represented species or pair, and its
composition trajectory is unavailable. This check rejects the current named
mixture coefficients at our sampled cold state as numerical matches; it
does not establish a replacement definition for the paper's \(D\).

## Artifacts and reproducibility

All derived data and images are outside Git in
`state/liang-hydrogen-20261020/figure6-reference/`:

- `embedded-72.jpeg`, `page.png`: original image and rendered page.
- `extract.py`: extraction and comparison, default plan; `--apply` writes
  only this state directory.
- `pixels.csv`, `samples.csv`, `summary.json`: observed positions,
  calibrated samples, bounds, source hashes and crossings.
- `conductivity-comparison.csv`, `conductivity-variant-scores.csv`,
  `diffusion-300K.csv`: saved-data comparisons.
- `trace-check.png`: traced pixels over the original figure, visually checked.
- `comparison.png`: paper curves and calculated ratios with explicit legends.
- `threshold-check.json`: color-selection sensitivity check.

Run the script with the project's analysis environment; inspect its default
plan before adding `--apply`. The PDF and comparison data are read-only.

| Input | SHA-256 |
|---|---|
| Original Liang PDF | `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe` |
| Embedded Figure 6 JPEG | `1fcb1aad74def3ffc5e6b8f592b662a1926e225a1954ae40c6b50f6af84112a5` |
| Job 125069072 transport CSV | `177c60f2125b6d0f577ed701714a4ee512ab652027140260e562d07e62d04960` |
| Conductivity probe states CSV | `eef621724e5c2782730a93d6bf0056b50a252bb728aba5836f14f39699fad2d9` |
| Diffusion definitions ratios CSV | `a15809d5a083c20a31d099382be010f8476ea49b7b77449492a47e67b400aca0` |

Verification: plan and extraction completed successfully; original-image trace
and comparison plot inspected; source hashes recorded; note checked for UTF-8,
LF and whitespace. No solver source edits, jobs, or commits were made.
