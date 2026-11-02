# Schmitt Figure 21 G2 reference and comparison

This offline module extracts the clearly distinguishable blue G2 mean velocity
and mean oxygen curves from the supplied Schmitt (2020) Figure 21 image, then
compares them with retained `g2-window-average` outputs. It does not run CFD,
infer a missing velocity, convert startup into converged statistics, infer the
paper inlet speed, or award scientific acceptance. The crowded blue dashed
oxygen RMS is deliberately unavailable rather than guessed.

## Paper definitions and scope

The supplied PDF is *Large-Eddy Simulations of the Mascotte Test Cases Operating
at Supercritical Pressure*, DOI `10.1007/s10494-019-00096-y`, SHA256
`f138b430e2cac438acf139d9a7f56d38e53adb11513346c69922734c1c419879`.
Figure 21 is on printed page 180 (PDF page 22). It uses centerline Reynolds
mean `ux/u0` versus `x/d`, with d the oxygen-injector diameter (page 181).
The supplied text does not explicitly identify a numerical u0; Figure 9 uses
the separately named ubulk. Do not silently identify u0 with an O2 inlet speed.
Section 3.3 discards one oxygen convective time before averaging for 50 ms.
The G2 conditions are 56 bar and O2/CH4 at 83/300 K. The paper's 3D chamber
is 50 x 50 x 400 mm. These differ from the current 5.61 MPa, 85/288 K,
co-planar wedge and sample line at radius 0.1 mm. No paper diameter value is
invented to convert its x/d curve into millimeters.

The caption reads: “Fig. 21 Flame length. Centerline profiles of a mean axial
velocity and b mean (continuous) and rms (dashed) oxygen mass fraction”. The
paper defines flame length by centerline mean oxygen falling below 0.1, reported
approximately 12d for G2. Our finite-window near-axis crossing is only a
diagnostic, not that validated flame length.

## Interfaces and verification

`prepare.py --pdf PAPER --out NEW_REFERENCE` is read-only by default. `--apply`
extracts the PDF's original 1441 x 423 JPEG, a pixel/calibration audit, two CSV
curves, a reference receipt and an annotated extraction overlay. The exact PDF
and native image hashes are required. Calibration anchors are in `calibration.json`.
The blue classifier and separate curve regions are explicit. Velocity uses each
native image column; oxygen uses an upper plateau and then the rightmost blue
stroke in each selected descending row. This distinguishes the solid mean from
the left dashed RMS without connecting across missing pixels. Near the bottom,
the overlapping baseline is omitted. No regression or fitted curve is used.
Pixel brackets retain stroke width plus a conservative two-pixel calibration
allowance. They are reading uncertainty, not experimental confidence intervals.

`review.py --reference REFERENCE --statistics WINDOW --x-origin-m 0
--origin-note NOTE --out NEW_REVIEW` validates an applied saved-sample statistics
manifest and prints a read-only plan. `--apply` writes PNG/SVG plots and an HTML
page with the original figure and caption. Primary views keep our dimensional
axes separate from paper x/d and ux/u0. Missing U_0 leaves our velocity
unavailable. Optional `--inlet-audit-case CASE` uses the existing hash-bound
initialization consumer to add explicitly inferred normalized overlays. The
case plan's ideal-gas placeholder velocity is never used. Numeric agreement
scores and acceptance thresholds are intentionally absent.

```sh
python replication/validation/schmitt-fig21/prepare.py --pdf /papers/schmitt.pdf --out /derived/schmitt --apply
python replication/validation/schmitt-fig21/review.py --reference /derived/schmitt --statistics /derived/window --x-origin-m 0 --origin-note 'Measured co-planar exit; upstream taper omitted' --out /review/schmitt --apply
```

Dependencies: Python, NumPy, Matplotlib, Pillow and PyMuPDF; the consumer reuses
`g2-review/inputs.py` and `g2-window-average/inlet_scale.py`. Neither the solver
nor the window statistic producer depends on this module. Inputs remain
read-only; all outputs require new directories. There are no network, credential,
scheduler or publication operations. Downloaded papers and extracted data stay
outside Git.

Verification: run the read-only plan and extraction on the exact supplied PDF,
inspect the source overlay and both curves, then replay retained actual window
data and inspect every comparison. Check recorded input/source/output hashes.
Missing-U evidence must remain unavailable; a modified PDF/reference asset must
fail before output creation. These checks verify data handling, not CFD physics.
