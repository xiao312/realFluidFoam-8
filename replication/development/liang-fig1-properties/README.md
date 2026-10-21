# Liang et al. (2019) Fig. 1 — density and thermal conductivity of O₂ at 100 atm

Target `liang-1` of the Forge V&V ladder. Reference: Liang, Li & Law, *Proc. Combust.
Inst.* 37 (2019) 1513–1521, doi `10.1016/j.proci.2018.06.070`, PDF sha256
`24163be0…aca6fe`, page 3. Caption: “Comparison of model and experimental data of (a)
density and (b) thermal conductivity for oxygen at 100 atm”.

Everything here is standard library / repository headers. No numpy, no PyMuPDF, no
matplotlib: the batch image has none of them (job 125185651) and the local image has no
numpy either.

## Files

| file | role |
| --- | --- |
| `fig1_probe.cpp` | C++17 sweep of the repository's own SRK kernel and Ely–Hanley conductivity over 150–1000 K at 100 atm; writes the CSV |
| `job.sh` | builds and runs the probe in a scheduler job (`sh job.sh CASE RUN`) |
| `pr_density.py` | sweeps the independent Peng–Robinson module `../oxygen-properties` at the same pressure |
| `digitize_fig1.py` | measures the published curves and symbols out of the PDF's embedded raster |
| `render_figures.mjs` | builds `forge-series-v1` data and two `forge-paper-style-v1` recipes, then renders the composite SVG |
| `checks.py` | six checks and the `forge-campaign-checks-v1` verification file |

## Why the probe is C++

`replication/development/liang-properties/SrkKernel.h` and `ElyHanley.H` are header-only
and SDK-free, so the Liang workflow's own `liang::evaluate` and
`rfElyHanley::conductivity` are used verbatim instead of a re-derivation. The Peng–Robinson
variant stays in Python (`../oxygen-properties`) so `numerical_comparison` compares the
SRK curve against an *independent* equation-of-state implementation.

Constants (pure O₂): `Tc = 154.581 K`, `Pc = 5.043e6 Pa`, `Vc = 0.0734 m³/kmol`,
`W = 31.9988 kg/kmol`, `ω = 0.022`; `p = 100 atm = 10 132 500 Pa`. Ideal-gas cp is the
NIST Shomate fit in both of its ranges; the two ranges agree to 0.002 % at the 700 K
splice, which is reported at run time (`shomate_join_700K` on stderr) and re-checked by
`checks.py`.

Probe CSV columns: `T_K, rho_srk_kg_m3, Z_srk, v_srk_m3_kmol, cp_ideal_J_molK,
cp_res_J_molK, cp_J_molK, lambda_eh_W_mK, cpR_ideal`. `SrkKernel.h` returns the *residual*
cp only, so `cp_J_molK = cp_ideal + cp_res`.

### Units of the ideal-gas Cp ratio

`SrkKernel.h` is kmol-based: `liang::R = 8314.46261815324 J/(kmol K)`, while the Shomate
fit returns J/(mol K). The dimensionless `Cp/R` needed by `ElyHanley.H` (its `Species::cp_R`)
and reported in the `cpR_ideal` column is therefore `1000·cp_ideal/liang::R`. The first
version of this probe omitted the factor 1000, which made `Cp/R = 0.00353` at 300 K, tripped
the repository's own `Cp/R < 2.5` guard in `ElyHanley.H` for every temperature and produced a
header-only CSV while still exiting 0 (job `125192215`, run
`/workspace/forge-out/runs/liang-fig1-probe2-5c20c46/`, retained as failed evidence).

The probe now pins the conversion twice and refuses to report an incomplete sweep:

* `unit_check` on stderr: `liang::R` must equal 8314.462618 J/(kmol K) to 1e-4 and
  `Cp/R(300 K)` must be 3.53 ± 0.05 (0.00353 and 3530 both fail); exit status 2 otherwise;
* every state must have `3.30 ≤ Cp/R ≤ 4.20`, the audited O₂ window 150–1000 K;
* every printed value is checked finite;
* `coverage rows N expected M rejected K` is reported, and any rejection, `N = 0` or
  `N ≠ M` exits with status 3 so `job.sh` (which propagates the payload status) fails too.

## Why the published data are digitised

Fig. 1 is a raster XObject inside the PDF — there is no vector path to extract, unlike
Müller & Pfitzner Fig. 1. The chain is:

1. the PDF text/objects are parsed, the figure's image XObject is extracted as a
   775×1371 DeviceGray DCTDecode JPEG (sha256 `b28ef871…68c9ea`) — byte-identical to the
   `image_sha256` recorded in `../liang-properties/figure1-calibration.json`;
2. that JPEG is decoded to RGBA (sha256 recorded in the digitisation JSON);
3. the retained axis calibration is refitted from its own tick list (residual ≤ 0.75 px,
   agreement with the retained coefficients 2.4e-13) and applied to the pixels;
4. the model curves are traced by Zhang–Suen thinning of the line mask plus an ordered
   per-component walk; the published triangles are found as 3×3-erosion cores with a shape
   filter (25–600 core pixels, bbox ≥ 5×5, aspect 0.5–2.0) after rejecting the frame,
   inward ticks, tick labels and the near-vertical stroke at the left.

Stretches where a filled triangle hides the model line are recorded as **gaps**, never
interpolated. Declared uncertainty: 1 px ≈ 1.19 K / 0.38 kg/m³ in panel (a) and ≈ 1.34 K /
2.3×10⁻⁴ W/(m·K) in panel (b); line centre ±1 px, triangle centre ±2 px.

Measurable ranges are limited by the figure, not by the extraction: panel (a) model only
for T ≳ 238 K (below that the curve overlaps the axis frame and the inward ticks), panel
(b) model peak clipped by the top frame at ≈ 0.155 W/(m·K) so the reading starts at
≈ 171 K.

## Figure geometry

Pixel → point: `x = 50.733 + 0.24·px`, `y = 54.012 + 0.24·py` (top-down), from the
placement rectangle of the 775×1371 raster on the page. ViewBox
`[50.733, 44.0, 190.0, 339.0]`, canvas 792×1413. Panel (a) frame
`[72.333, 54.012, 230.733, 198.852]`, x `[219.04, 1004.64]`, y `[0, 230.60]`; panel (b)
frame `[72.333, 224.412, 230.733, 369.132]`, x `[116.2, 1000.9]`, y
`[0.01079, 0.15039]`.

The composite SVG is one root element whose children are the unmodified bodies of the two
`renderPaperComparison()` calls (`/forge/plots/paper-style.mjs`), both drawn on the same
canvas and viewBox. Nothing is re-projected, so each panel is byte-reproducible from
`data.json` + its panel recipe in `raw/`.

Declared fidelity gaps, all caused by the renderer, not by the data:

* axis text is placed as measured text (`labels[]`), not the paper's own vector glyphs —
  the raster has none;
* the y-axis titles are horizontal, because the renderer has no rotation;
* the published triangles are drawn as circles, because the renderer has only circle
  markers;
* the paper's inward minor ticks are not drawn, and the grid is left empty rather than
  inventing grid lines the paper does not have;
* legend text is shortened to fit inside the frame and the legend rows are moved to empty
  regions of each panel; the paper's legend order is kept.

## Runs

```sh
sh job.sh "$PWD" /path/to/run          # env cantera32, 1 rank, OMP/OPENBLAS = 1
python3 pr_density.py --out run/liang-1-pr-100atm.csv
node render_figures.mjs --probe run/fig1-probe.csv \
     --digitised liang-fig1-digitised.json --pr-csv run/liang-1-pr-100atm.csv \
     --out-dir run --source-commit "$(git rev-parse HEAD)" --run-job-id "$JOB"
python3 checks.py --probe run/fig1-probe.csv --digitised … --data … --plot … \
     --recipe … --out run/verification.json --commit "$(git rev-parse HEAD)"
```

`digitize_fig1.py` is not part of the job: it measures the paper once and its output
(`liang-fig1-digitised.json`) is retained as raw evidence with the RGBA dump digest inside
it. It is re-runnable from the PDF alone.
