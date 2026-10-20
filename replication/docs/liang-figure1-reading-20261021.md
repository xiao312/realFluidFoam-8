# Liang Figure 1: model-line and marker readings

21 October 2026, 00:24 Asia/Shanghai. Status: extracted and compared; scientific
acceptance remains open. This follows the
[Figure 1/2 source audit](liang-figure12-followup-20261021.md).
No property model, coefficient, case, or remote job changed.

The density model line is reproduced closely by the current SRK calculation:
**0.272% RMS relative difference** across 68 visible readings near a 10 K grid.
The paper's five density triangles are a different target: their RMS
differences are **7.79% against SRK and 8.35% against current NIST**.
For conductivity above 300 K, the mass-density shortcut follows the black line
more closely, but agrees less well with the triangles than the correctly
mapped variant. These findings do not justify changing the density mapping.

## What was read

The unchanged embedded JPEG was extracted from PDF page index 2, image xref 29,
at its original **775 by 1371 pixels**. Axis labels, the `Model` and
`Experiments` legend, and panel labels remain intact. The source is the
owner-provided [Liang, Li and Law paper](https://doi.org/10.1016/j.proci.2018.06.070).

The retained evidence contains 563 density-line readings, 935 conductivity-line
readings, five density triangle centers, and ten conductivity triangle centers.
The eleventh conductivity triangle touches the left axis: its visible location
is marked, but no numerical center is assigned. Three density symbols touch
the line; their manually inspected vertices have enlarged reading bounds, and
the corresponding line segments are omitted. No curve is reconstructed beneath
a marker or beyond a visible clipped boundary.

The retained density-line range is approximately 240.5–997.4 K. Its near-axis
upper-left portion is excluded. Conductivity-line readings span approximately
169.8–992.9 K; the near-vertical cold segment is read by image rows rather than
columns. The top boundary clip is excluded. These are reading coverage limits,
not newly inferred physical validity limits.

### Calibration and reading bounds

Tick centers were measured from source-pixel ink at grayscale thresholds
64, 128, and 192. A linear fit to all major ticks defines the nominal axis
mapping. Extreme mappings use the complete endpoint-tick ink extents plus
half a pixel, rather than assuming exact tick-center positions.
Maximum internal tick residuals are 0.416 K and 0.0765 kg/m3 for the density
panel, and 0.536 K and 0.000174 W/(m K) for conductivity.

Model-line bounds include threshold-dependent stroke extent and half-pixel
sampling. Triangle nominal positions use the geometric vertex centroid.
Their intervals include the alternative bounding-box center because the
original plotting package's symbol anchor is unknown. Isolated symbols also
have measured connected-component centroids and bounding boxes at all three
thresholds. The three overlapping density symbols instead use manually inspected
vertices with a conservative two-pixel bound; this is a reading estimate, not
an experimentally measured uncertainty.

After axis propagation, full horizontal interval widths are approximately
6.0–8.5 K for column-sampled density readings, 6.7–12.4 K for conductivity-line
readings, and 7.3–11.4 K for triangle centers. These intentionally conservative
bounds include finite stroke width and calibration uncertainty. They are not
statistical confidence intervals.

All original-size extraction overlays were inspected. Cyan follows the visible
black model lines; magenta marks triangle centers and their pixel intervals.
The orange box identifies the excluded conductivity triangle. The original
source image is retained separately, without annotations.

## Quantitative comparison

Native results remain property job **124887485**, source
`e208396bdba48592aacbf6bb9a1c41b8eca3d9bb`, library build **124657926**.
The comparison uses its existing 1 K oxygen sweep and the frozen 19 October
NIST 5 K table, both at **100 atm = 10.1325 MPa**.

Predictions are linearly interpolated on their existing grids to each retained
paper reading; paper readings are never interpolated across excluded regions.
For curve summaries, the nearest visible reading within 1 K of each 10 K
target is selected. Missing targets are omitted. This avoids giving excessive
weight to the row-sampled vertical branch. Pixel readings are not independent
experimental observations.

Relative error is `100*(prediction/paper_reading - 1)`. For interval comparisons,
each prediction's minimum and maximum across the reading's temperature interval
are compared with the paper value interval. The reported overlap count uses
**reading uncertainty only**, without adding reference-model or experimental
uncertainty. Interpolation truncation error has not been separately quantified,
which matters most on the cold, curved portion.

| Paper model line, T >= 300 K | Readings | RMS relative difference, % | Maximum absolute difference, % | Reading intervals overlap |
| --- | ---: | ---: | ---: | ---: |
| Density: native SRK | 64 | 0.270 | 0.814 | 64/64 |
| Density: frozen NIST | 64 | 0.730 | 1.458 | 64/64 |
| Conductivity: native molar-consistent mapping | 69 | 6.457 | 16.368 | 23/69 |
| Conductivity: native mass-density shortcut | 69 | 1.102 | 2.657 | 69/69 |
| Conductivity: frozen NIST | 69 | 13.003 | 22.591 | 0/69 |

For density across all 68 retained 10 K targets, SRK RMS is 0.272% and NIST RMS
is 0.795%; both overlap all conservative reading intervals. Agreement within
these image bounds does not establish accuracy at the NIST reference level.

| Paper triangle markers | Readings | RMS relative difference, % | Maximum absolute difference, % | Reading intervals overlap |
| --- | ---: | ---: | ---: | ---: |
| Density, all: native SRK | 5 | 7.793 | 11.353 | 2/5 |
| Density, all: frozen NIST | 5 | 8.348 | 12.308 | 0/5 |
| Conductivity, T >= 300 K: native molar-consistent mapping | 5 | 6.904 | 10.469 | 0/5 |
| Conductivity, T >= 300 K: native mass-density shortcut | 5 | 16.720 | 27.211 | 0/5 |
| Conductivity, T >= 300 K: frozen NIST | 5 | 4.195 | 6.981 | 2/5 |

Across all ten readable conductivity triangles, frozen NIST RMS is 4.558%,
maximum difference 8.681%, and six reading intervals overlap. Native
conductivity below 200 K uses extrapolated NASA heat capacity and remains
unqualified; its cold-point errors are preserved in the CSV, not pooled into
the non-extrapolated-range summary.

These results establish the practical distinction between reproducing the
paper's model curve and comparing with its experimental markers. The paper
does not identify the individual marker datasets, their uncertainties, or its
NIST database version. The observed marker discrepancies cannot be attributed
to one of those causes from this image alone.

## Triangle coordinates retained

Values are rounded here for readability; the CSV retains pixels, nominal
coordinates, both coordinate intervals, and threshold evidence. Conductivity
has units W/(m K), density kg/m3.

| Marker | T, K | T reading interval, K | Property value | Property reading interval |
| --- | ---: | ---: | ---: | ---: |
| D1 | 282.1 | 275.8–287.2 | 140.58 | 138.87–143.21 |
| D2 | 446.0 | 441.7–449.0 | 76.66 | 75.38–78.78 |
| D3 | 567.0 | 561.3–571.2 | 63.67 | 62.02–66.16 |
| D4 | 692.7 | 687.5–697.0 | 51.07 | 49.43–53.54 |
| D5 | 820.3 | 816.1–823.4 | 51.07 | 49.81–53.15 |
| K1 | — | partial marker at axis | — | excluded |
| K2 | 156.4 | 152.1–160.7 | 0.07367 | 0.07286–0.07491 |
| K3 | 171.9 | 167.6–176.0 | 0.05175 | 0.05093–0.05306 |
| K4 | 184.1 | 179.8–188.2 | 0.04041 | 0.03958–0.04173 |
| K5 | 198.2 | 193.9–202.2 | 0.03107 | 0.03023–0.03237 |
| K6 | 235.5 | 231.5–239.5 | 0.02698 | 0.02614–0.02832 |
| K7 | 312.6 | 308.5–316.6 | 0.03176 | 0.03093–0.03306 |
| K8 | 402.9 | 398.8–407.0 | 0.03639 | 0.03556–0.03769 |
| K9 | 517.0 | 512.9–520.9 | 0.04589 | 0.04506–0.04717 |
| K10 | 687.9 | 683.8–691.8 | 0.05769 | 0.05687–0.05896 |
| K11 | 853.5 | 849.2–857.3 | 0.06958 | 0.06876–0.07087 |

## Current WebBook reference attribution verified

The official result page was fetched on 21 October at 00:19:56 Asia/Shanghai.
Its references explicitly identify **Schmidt and Wagner (1985)** for the
oxygen EOS and **Lemmon and Jacobsen (2004)** for thermal conductivity.
The page also gives the conductivity uncertainty as 3% at 270–300 K and
5% elsewhere, with unknown uncertainty above 100 MPa; its 2% estimate is
specifically for dilute gas. The ten displayed 100 K increment density and
conductivity values exactly match the frozen table's decimal values.
[Official WebBook oxygen output and references](https://webbook.nist.gov/cgi/fluid.cgi?Action=Load&ID=C7782447&Type=IsoBar&Digits=12&P=100&TLow=100&THigh=1000&TInc=100&TUnit=K&PUnit=atm&DUnit=kg%2Fm3&HUnit=kJ%2Fkg&WUnit=m%2Fs&VisUnit=Pa*s&STUnit=N%2Fm&RefState=DEF#Refs).

Thus the previous conductivity uncertainty attribution is now directly
supported for the named backend correlation. The server binary/version is
still not exposed. The EOS page's 0.1% density statement must not be extended
uncritically beyond the underlying equation's original range; the separate
NIST assessment of approximately 0.5% density extrapolation to 1000 K remains
the relevant high-temperature qualification.
[Lemmon et al. (2000), Section 7.2](https://trc.nist.gov/refprop/Documents/Air.pdf).
These are reference-correlation assessments, not tolerances for a paper-marker
match or permission to change coefficients.

## Evidence and rerun

All raw evidence and scripts remain in the ignored operator directory:
`state/liang-hydrogen-20261020/figure1-reference/`, relative to the outer
realfluidfoam project. Its README describes inputs, output files, exclusions,
dependencies, and the read-only plan. No downloaded article or source raster
was added to Git.

```powershell
& 'D:/xiaok/work/FlamePilot/projects/realfluidfoam/state/analysis-venv/Scripts/python.exe' -B `
  'D:/xiaok/work/FlamePilot/projects/realfluidfoam/state/liang-hydrogen-20261020/figure1-reference/read_figure1.py' plan
```

Expected: 1513 readings and 3971 comparison rows. Replacing `plan` with `apply`
reproduces the generated evidence locally. Inspect `extraction-overlay.png`;
it is a reading audit, not a replacement scientific comparison figure.

| Artifact | SHA256 |
| --- | --- |
| `read_figure1.py` | `23173335f1b2c3dc009f06484024c60400280d9e9f9cd49303c00e9dcb411d34` |
| `figure1-original.jpeg` | `b28ef871c4ad92031d7eeaf24e8a20d0fde6e83f9842c88c0f98ea645068c9ea` |
| `paper-readings.csv` | `9915f5039360792239a41437931fca9f6547fc1d771c2ba21507f533c778db58` |
| `comparisons.csv` | `118176dd9f1350b15980168e3bf6043b531135d0c7c9f3ee67caf96d0629bd6d` |
| `curve-10K-visible-comparisons.csv` | `d3b2af2420d2071229aace8f9de47d03acbc8438eb4c5733db94f3db146fb140` |
| `extraction-overlay.png` | `38819b6d024853c32674a125612fa8be9e9085a8aa328efaaea43949ab0a3f26` |
| `webbook-oxygen-output.html` | `d6d9c6ea661a1da5210c3325699636edff63f59ace689874c6b45b229a3a5ce4` |

`reading-manifest.json` pins the original PDF, native property output and frozen
NIST table, alongside axis calibration and source vertices. Separate retrieval
receipts and `webbook-attribution-check.json` preserve official-page provenance
and the ten-point parity check. No new numerical acceptance threshold is set.
