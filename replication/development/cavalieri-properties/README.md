# Cavalieri et al. (2025) Fig. 1 — pure O2 and CH4 properties at 56 bar

Target `cavalieri2025-fig-1`: density, isobaric heat capacity, dynamic viscosity and
thermal conductivity of pure O2 (solid curve) and pure CH4 (dashed curve) at 56 bar
between 100 K and 400 K, with NIST reference points, computed with an SRK equation of
state and the Chung high-pressure transport model.

## Why this directory

The published figure is vector art embedded in the PDF (`/Title (gr1.eps)`, page index
6, `/BBox [0 0 360 276.108]`, 1400 stroked/filled paths, 476 marker circles, and all
axis text as glyph outlines — there is no `Tj`/`TJ` text operator anywhere in the
form). The reference markers and the two model curves are therefore recovered from the
path geometry, not from a raster, and the axis labels/limits are cross-checked against
the 921x718 page raster in `/references/library/objects/64d5178f...png`.

## Contents

- `digitise_fig1.py` — stdlib-only extractor for that form. Scans the PDF objects,
  decompresses the content stream, tokenises it with dash-array tracking, classifies
  every path (frame, tick, curve, marker, glyph, legend sample), finds the four panel
  frames and their tick grids, then walks the marker circles and assigns each one to
  the curve it lies on. Writes `figure1-vector.json`.
- `probe_models.py` — Cantera probe used to confirm which real-gas EoS and transport
  models this build actually accepts (`RedlichKwong`/`PengRobinson`, `high-pressure`
  transport) before the sweep is written. Runs only in the batch image.
- `job.sh` — batch wrapper for the probe (never writes into the repository).

## Measured figure geometry (declared)

| panel | quantity | frame (pt) | y range | y ticks |
| --- | --- | --- | --- | --- |
| (a) | density | 27.388 171.921 168.268 273.46 | 0–1200 kg/m³ | 7 (step 200) |
| (b) | cp | 206.257 171.921 354.589 273.46 | 0–25 kJ/(kg K) | 6 (step 5) |
| (c) | viscosity | 21.797 32.839 168.268 134.378 | 0–2 ×10⁻⁴ Pa s | 5 (step 0.5) |
| (d) | conductivity | 211.846 32.839 354.589 134.378 | 0–0.25 W/(m K) | 6 (step 0.05) |

All four panels share x = 100–400 K with 7 ticks (step 50). Frames and ticks are
0.323 pt grey `(0.149,0.149,0.149)` = `#262626`; the model curves are 0.621 pt black;
markers are filled circles of 2.856–2.859 pt outer diameter with a 2.111–2.114 pt inner
disc at the same centre (476 of them); axis glyphs are 4.5–4.9 pt tall, i.e. about
6.5 pt type. The dashed CH₄ curve uses dash array `[1.9881, 1.9881]`.

## Marker series

The markers are drawn on temperature grids, not on the curves: 59 O₂ points on a 5 K
grid starting at 105 K and 39 CH₄ points on a 7.5 K grid starting at 107.5 K in panel
(a); panels (c) and (d) carry 59 + 59 points on the same 5 K grid. Panel (b) has 133
in-frame markers because the two cp peaks are sampled at extra 0.5 K spacing.

Assignment rule: markers are grouped by abscissa (1.2 pt window), the upper marker of a
pair goes to whichever curve is upper at that temperature, and a lone marker uses the
midline. This is exact wherever the curves are separated and can only be ambiguous at
the panel (b) cp crossover, where the extracted split is 68/65 instead of 67/66 — one
marker of 133 — which is declared rather than tuned.

Markers whose distance to the assigned curve exceeds **40 % of the panel span** are
rejected as non-markers (glyph outlines, axis artefacts). The earlier 6 % limit was
wrong: it discarded genuine low-temperature NIST points that the paper's own SRK+Chung
curves do not follow (for example panel (c) at 105 K, curve 1.3258 vs marker 1.4483,
9.3 % relative). Those residuals are now kept and reported: the largest in-frame
residual is 7.8 % of span in (a), 21.6 % in (b), 6.8 % in (c) and 10.1 % in (d).

## Status

Digitisation is complete and reproducible (single run, ~1 s, no network, no third-party
packages). The SRK model sweep and the `forge-paper-style-v1` recipe are not written
yet; the Cantera model probe must resolve first because the sweep has to use the same
EoS and transport model that the build actually supports.
