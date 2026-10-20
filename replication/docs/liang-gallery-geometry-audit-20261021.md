# Liang Figures 2–6: independent gallery geometry audit

21 October 2026, Asia/Shanghai. State: inspected and tested; renderer changes
are handled separately.

Figures 2–5 use the correct axis scales and units. Their mapped major ticks
differ from the original PDF by less than 0.013 point. Figure 6 has a
horizontal calibration error: at 300 K the captured renderer places a point
2.345 points, equivalent to 26.23 K, too far right. Figure 4 also drops the
valid leftmost calculated points because its axis map and clipping boundary
differ by 0.0136 point. Neither finding explains the raw critical-pressure or
transport-property discrepancies.

This audit follows the separate [Figure 7 investigation](liang-figure7-reading-20261021.md).
It does not change any model, simulation, measured flame width or acceptance
criterion.

## Source and method

The source is Liang et al.,
[DOI 10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070),
PDF pages 3–5. Figures 2–5 contain vector ticks. Their original drawing
coordinates were read with PyMuPDF and checked against the printed labels.
Figure 6 is a 775 × 661-pixel embedded JPEG, xref 72 on PDF page index 4;
its tick centers were mapped through the PDF image rectangle.

All axes in Figures 2–6 are linear. Figure 2's right axis is pressure in
atm, with its first labeled tick at 10 atm; its lower boundary is not zero.
The logarithmic species axis belongs to Figure 7.

The inspected `plot.py` was copied before correction to ignored
`state/liang-hydrogen-20261020/geometry-audit/plot-inspected.py`.
This note identifies that captured source by hash; it does not claim that
subsequent renderer revisions retain the defects.

| Figure | Quantity | Maximum major-tick error, PDF point |
|---|---|---:|
| 2 | φ / critical temperature / critical pressure | 0.0082 / 0.0110 / 0.0103 |
| 3 | φ / flame speed | 0.0088 / 0.0010 |
| 4 | φ / fresh density / burning mass flux | 0.0010 / 0.0096 / 0.0127 |
| 5 | φ / burned temperature | 0.0104 / 0.0076 |
| 6 | temperature / transport ratio | 2.0237 / 0.3531 |

The Figure 6 temperature error in the table is evaluated at its labeled
500–2000 K ticks. The 300 K offset stated above uses the fitted tick map.
The source raster's three-pixel graphical reading allowance is approximately
0.72 PDF point. The horizontal error exceeds this allowance at low
temperature; the vertical error does not.

## Figure 6 calibration

The original image rectangle, in PDF points, is:

```text
(50.733001708984375, 261.98699951171875,
 236.73300170898438, 420.5369873046875)
```

Zero-based pixel index `i` maps to its center using
`origin + (i + 0.5) * scale`. The horizontal scale is 0.24 point/pixel;
the vertical scale is 0.23986382419511157 point/pixel.

| Axis label | Pixel center index | PDF coordinate, point |
|---|---:|---:|
| 500 K | x = 191 | x = 96.693002 |
| 1000 K | x = 377 | x = 141.333002 |
| 1500 K | x = 563 | x = 185.973002 |
| 2000 K | x = 750 | x = 230.853002 |
| 0.90 | y = 604 | y = 406.984681 |
| 0.95 | y = 436.5 | y = 366.807491 |
| 1.00 | y = 269 | y = 326.630300 |
| 1.05 | y = 101.5 | y = 286.453110 |

Least-squares fits to these centers give:

```text
x_pt = 51.93300170898439 + 0.08942400000000002 * T_K
y_pt = 1130.1741111859212 - 803.5438110536201 * ratio
```

The largest x fit residual is 0.096 point, smaller than one raster pixel.
The captured renderer instead assumes 200 K at x = 72.3 points and spans
1800 K in 158.5 points. Its left boundary actually corresponds to roughly
228 K under the tick calibration. The resulting horizontal scale is about
1.53% too small, in addition to the offset.

Use the calibrated maps for both overlay points and physical plot bounds.
Keep the printed ratio definitions unchanged. The previously extracted
Figure 6 curve values and crossing temperatures use their own raster
calibration; this finding changes overlay placement, not those readings.

## Unit and data checks

The producer `replication/development/liang-hydrogen/flame.cpp` writes
`speed_cm_s = 100 * velocity_m_s`, `rhou_kg_m3` and
`massflux_kg_m2s = density * velocity_m_s`. The renderer correctly:

- uses `speed_cm_s` directly in Figure 3;
- divides density by 1000 to obtain g/cm³;
- divides mass flux by 10 to obtain g/(cm² s);
- uses temperature in K directly.

Across the 122 completed author-pair runs selected from
`manifest-complete-0029.json`, the largest relative difference between
stored mass flux and `rhou_kg_m3 * speed_cm_s / 100` is
`4.44e-16`. There is no density/speed conversion discrepancy in these
inputs.

The critical-property producer `liang-properties/rfLiangPropertyProbe.C`
writes pressure divided by 101325, giving atm as labeled. The gallery uses
the existing `job-124887485/properties/critical.csv`; all 60 sampled
critical-property points lie within the Figure 2 plotting rectangle.
The unresolved critical-pressure disagreement is not an atm/bar error or
a plotted-axis error.

As a cross-check of the Figure 7 path, the inspected renderer obtains mole
fractions from all 13 species using
`X_i = (Y_i/W_i) / sum_j(Y_j/W_j)`. This conversion is correct. Its
independent geometry and profile findings are recorded in the linked
Figure 7 note.

## Clipping and line continuity

The captured `line()` first removes points whose centers fall outside the
rectangle, then draws one polyline through the remaining points. This can
connect across an omitted interior excursion. It also misses a segment
that crosses the rectangle when both sampled endpoints are outside.
Marker and stroke extents are not clipped merely by checking their centers.
Use segment clipping or separate contiguous pieces, and an actual clipping
path when exact stroke containment is required.

For the selected completed data there are **no interior omissions**.
The inspected galleries therefore have no demonstrated false bridge from
this behavior. Figure 3 omits two points per case outside the paper window;
Figure 6 omits the low-temperature portion of the calculated conductivity
ratio below the panel. These should remain explicit out-of-view data,
rather than being moved into the panel.

Figure 4 has a small but actual boundary inconsistency:

```text
x(phi = 0.6) = 296.925 + (0.6 - 1) * 60.614 = 272.6794 pt
rectangle left edge = 272.693 pt
difference = -0.0136 pt
```

This removes both density and mass-flux values at φ = 0.6 for Cases 1 and 2.
Their y values are inside the panel:

| Case / job | Density, g/cm³ | Mass flux, g/(cm² s) |
|---|---:|---:|
| 1 / 125072763 | 0.09589550 | 0.39363962 |
| 2 / 125072806 | 0.09376777 | 0.39906070 |

Use a consistent calibrated boundary or a small coordinate tolerance
covering the PDF's rounding, for example 0.02 point. Do not change φ or the
physical data to avoid the clipping check.

## Reproduction evidence

Ignored artifacts are under
`state/liang-hydrogen-20261020/geometry-audit/`:

- `audit.py`: default read-only plan; `--apply` writes only that directory.
- `calibration.json`: every tick value and coordinate, vector drawing
  index, raster mapping, fit residual, input hash and clipping count.
- `tick-errors.csv`: independent expected/observed coordinates.
- `plot-inspected.py`: frozen renderer being audited.
- `figure-2-source.png` through `figure-5-source.png`: inspected source crops.

From the project root, both commands completed successfully:

```powershell
& state/analysis-venv/Scripts/python.exe state/liang-hydrogen-20261020/geometry-audit/audit.py
& state/analysis-venv/Scripts/python.exe state/liang-hydrogen-20261020/geometry-audit/audit.py --apply
```

| Input | SHA-256 |
|---|---|
| Original Liang PDF | `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe` |
| Captured renderer | `b549464727411e152af9f9f5fad1fd65dcd61ac5488380aa3a8d7c50f78e2a35` |
| Completed-run manifest | `3dd3c91c6cf23286bae57e5b071e23e0de16db5f4300df2037c8a5a27e67b3ce` |
| Existing Figure 3–5 digitization | `a62b7930fd8c1e0cef978842ab5b49a21a832034eaab6328f92c10fd545cdf99` |
| Critical-property CSV | `f9665c641cc882c28bf77c9725b81a7890d5b025f99fd3c094bd13cb14ebe1bc` |

The captured gallery evidence did not independently hash all direct plotting
inputs, including the critical CSV, species parameters and selected manifest.
The renderer owner is adding those records with the geometry corrections.
This audit made no renderer or model edits, job submissions, or commits.
