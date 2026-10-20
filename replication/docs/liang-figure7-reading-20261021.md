# Liang Figure 7: profile reading and plot calibration

21 October 2026, Asia/Shanghai. State: extracted and compared; scientific
acceptance remains pending.

The completed author-pair hydrogen flames have temperature-transition widths
consistent with Figure 7's reading bounds. The earlier gallery's visibly
broader profiles were caused by a factor-of-two horizontal plotting error.
After translation at 1500 K without stretching, Case 5's temperature and
major-species profiles are close to the paper. Its HO₂ and H₂O₂ peaks remain
about 5–6% high; their lower-temperature tails also differ. This does not
establish which physical model causes the remaining differences.

## Source and visible information

Source: Liang et al., [DOI 10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070),
PDF page 5, printed page 1737. Figure 7 describes a stoichiometric
hydrogen/air flame at 100 atm. It shows one visible curve each for temperature,
H₂, O₂, HO₂ and H₂O₂, with no case legend. No separate concealed case curves
are inferred or reconstructed.

Unlike Figure 6, Figure 7 contains vector line segments. PyMuPDF
`get_drawings()` indices 276–305, 306–352, 353–388, 389–410 and 411–433
identify the five curves in the order above. Their centers were recovered
directly. Repeated segment endpoints differ by roughly 0.001 PDF point;
these duplicates were combined by median y at x rounded to 0.001 point.
The original and trace overlay were visually checked, including crossings.
The minor-species tails stop at the visible plot boundary; no tail is
extrapolated.

The horizontal axis is **cm**. Eight labeled major ticks run from 0.978 to
0.9815 cm in steps of 0.0005 cm. The temperature axis is linear; the species
axis is logarithmic and explicitly gives mole fractions.

## Calibration and the gallery defect

Fits to the original vector tick centers give these page-coordinate maps:

```text
x_pt = 37015.746343701074 * x_cm - 35905.778840562176
y_pt = 192.3287139892578 - 0.05093020629882814 * T_K
y_pt = 60.47498357863653 - 22.38328486851282 * log10(X)
paper x(T = 1500 K) = 0.980127068315757 cm
```

`figure7-reference/calibration.json` records every original tick's printed
label, physical value, page center and drawing index, plus fit residuals and
reading allowances. It provides independent anchors for renderer checks.

The pre-correction `replication/development/liang-hydrogen/plot.py` used:

```python
xp = 369.648 + (100*(xx-xref) + .98018-.9800)/.00025*18.51
```

The denominator must correspond to a 0.0005 cm interval: 18.51 page points
span that interval, not 0.00025 cm. The expression doubled every simulated
width. Its approximate 1500 K target, 0.98018 cm, also differed by 0.5293 µm
from the extracted crossing before the erroneous scale was applied. The
species-axis approximation `59.85 - 22.45*log10(X)` had a smaller offset
error. The prior assertion that physical width was unchanged was therefore
incorrect; the renderer correction is handled separately from this note.

The gallery evidence at `output/pdf/liang-hydrogen-20261021-0030/evidence.json`
selects author-pair **Case 5, job 125068936**, for Figure 7. It is a single
calculated case, not six cases. The independent diagnostics in this record
compare all six completed author-pair stoichiometric cases.

## Reading bounds and alignment

The curve stroke is 0.681 point wide. A conservative ±0.4-point allowance
covers half the stroke and axis/read uncertainty. This gives approximately
±0.108 µm, ±7.85 K and ±0.01787 decade in mole fraction, or roughly ±4.2%.
These are graphical reading bounds, not numerical-solver uncertainty or
statistical confidence intervals.

Each calculated profile is translated by its own 1500 K crossing. No
horizontal scale factor, temperature rescaling or species scaling is used.
Widths use the original physical distance. The temperature-transition width
is the distance from 500 to 2000 K, avoiding an inferred asymptotic burned
temperature. Minor-species FWHM is measured in linear mole fraction, even
though the source axis is logarithmic. Bounds propagate the endpoint/peak
reading allowances; flat peak tops make peak-position bounds relatively wide.

| Paper quantity | Reading | Graphical bounds |
|---|---:|---:|
| Width, T = 500–2000 K | 4.726 µm | 4.422–5.025 µm |
| HO₂ peak mole fraction | 1.2476×10⁻³ | 1.1973–1.3001×10⁻³ |
| H₂O₂ peak mole fraction | 8.5717×10⁻⁴ | 8.2262–8.9318×10⁻⁴ |
| HO₂ FWHM | 2.464 µm | 2.056–2.866 µm |
| H₂O₂ FWHM | 2.434 µm | 2.046–2.811 µm |
| HO₂ peak position relative to 1500 K | +0.002 µm | −0.445 to +0.546 µm |
| H₂O₂ peak position relative to 1500 K | −0.593 µm | −1.133 to −0.142 µm |

## Completed profiles

Inputs come from `manifest-complete-0029.json`, selecting `phi=1` and
`transport=pairs`. Mass fractions were converted using the pinned species
molecular weights:
\(X_i=(Y_i/W_i)/\sum_j(Y_j/W_j)\).
No mechanism, initial state, model parameter or flame solve was changed.

| Case | Job | T width, µm | HO₂ peak, ×10⁻³ | H₂O₂ peak, ×10⁻⁴ |
|---|---:|---:|---:|---:|
| Paper, case unspecified | — | 4.726 | 1.2476 | 8.5717 |
| 1 | 125068730 | 4.620 | 1.3568 | 9.4008 |
| 2 | 125068903 | 4.585 | 1.3676 | 9.4432 |
| 3 | 125068909 | 4.695 | 1.3271 | 9.1891 |
| 3star control | 125068920 | 4.672 | 1.3319 | 9.2195 |
| 4 | 125068929 | 4.784 | 1.3345 | 9.2272 |
| 5 | 125068936 | 4.864 | 1.3129 | 9.1259 |

All six temperature widths lie within the graphical bounds. Case 5 is
2.9% wider than the paper's central reading, not twice as wide. Its HO₂ and
H₂O₂ FWHM values, 2.403 and 2.318 µm, also lie within the bounds.

For Case 5, the HO₂ peak is at +0.0156 µm and 1506 K, compared with the
paper's +0.0019 µm and about 1501 K. H₂O₂ peaks at −0.5887 µm and 1256 K,
compared with −0.5930 µm and about 1260 K. The positions agree closely;
the peak mole fractions are 5.23% and 6.47% higher, slightly outside the
vertical reading bounds.

At 1500 K, Case 5 H₂/O₂ mole fractions are 2.6%/2.8% above the paper.
At 500 K, its HO₂/H₂O₂ mole fractions are about 20%/24% below the paper;
these are lower-amplitude preheat tails. `species-at-temperature.csv` and
`species-versus-temperature.png` expose these differences without horizontal
alignment effects. They support a focused species-profile check rather than
a claim of a gross flame-thickness or flame-position failure.

The paper's upstream plateau is 297.93±7.85 K, consistent with the assumed
298 K inlet. Its rightmost visible temperature is 2452.08 K at +16.588 µm.
At that **same finite position**, Case 5 gives 2453.99 K, only 1.91 K higher;
Cases 3, 3star and 4 give 2454.50, 2455.82 and 2454.46 K. Comparing this
finite paper point with the simulations' far-downstream temperature near
2470 K would create an artificial temperature discrepancy.

Figure 7's transport-region markers also need qualification. On its own
temperature curve, the black and red vertical markers correspond to about
404 and 1082 K. These differ from Figure 6's independently read 5% crossings,
359 and 1299 K. They should be treated as approximate annotations, not
additional exact fitting targets.

## Reproduction evidence

Ignored artifacts are under
`state/liang-hydrogen-20261020/figure7-reference/`:

- `extract.py`: default plan; `--apply` reads the PDF/manifest/profiles and
  writes only the artifact directory.
- `calibration.json`, `summary.json`: independent tick anchors, coordinate
  maps, uncertainty, selected jobs and complete input hashes.
- `raw-vector-points.csv`, `aligned-profiles.csv`: source vertices and all
  paper/calculated profiles with translation only.
- `metrics.csv`, `species-at-temperature.csv`, `transport-markers.csv`:
  quantitative comparisons and source-annotation checks.
- `figure7.png`, `trace-check.png`, `comparison.png`,
  `species-versus-temperature.png`: original crop and checked diagnostics.
  The comparison plot focuses on −8 to +12 µm; CSVs retain all visible data.

| Input | SHA-256 |
|---|---|
| Original Liang PDF | `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe` |
| Completed-run manifest | `3dd3c91c6cf23286bae57e5b071e23e0de16db5f4300df2037c8a5a27e67b3ce` |
| Species parameters | `b093c29ac896bef71f36f5fbfc1f799bdc200f259efcf9b383138076253c3346` |
| Case 5 profile | `42142e5224e32f98ff4e6204303b3a8444b9fa30f376a6f66e49b308752860d3` |

All six profile hashes are in `summary.json`. Verification included plan/apply,
vector-trace inspection, comparison-plot inspection and bounds/format checks.
This research made no solver edits, job submissions or commits.
