# Cavalieri et al. (2025) Fig. 1 — pure O2 and CH4 properties at 56 bar

Target `cavalieri2025-fig-1`: density, isobaric heat capacity, dynamic viscosity and
thermal conductivity of pure O2 (solid curve) and pure CH4 (dashed curve) at 56 bar
between 100 K and 400 K, with NIST reference points, computed with an SRK equation of
state and the Chung high-pressure transport model.

## What is computed, and from which equations

| quantity | model | source of the equations |
| --- | --- | --- |
| density, enthalpy, cp | Soave–Redlich–Kwong, Graboski–Daubert alpha | paper Eqs. (2)–(4) |
| ideal-gas cp, h | NASA7 (GRI30 coefficients, O2 and CH4) | retained `replication/validation/inputs/property-thermo.inputData` |
| viscosity, conductivity | Chung, Ajlan & Lee (1988) dense-gas correlation | paper Eqs. (9)–(12); coefficients from Chung et al., *Int. J. Thermophys.* 9 (1988) Tables II and IV |

`srk_chung.py` is pure Python 3 standard library: no Cantera, no numpy, no compiled
extension, so every coefficient is auditable in the file that runs. The Chung coefficient
tables were transcribed from the published tables and cross-checked against this
repository's own OpenFOAM port
(`src/thermophysicalModels/specie/transport/chungKinetic/chungKineticTransportI.H`),
which carries the same ten A-coefficient sets and seven B-coefficient sets; that port was
*not* used at run time (it is C++ inside a solver library), it is the independent check
that the transcription is right.

Constants are the paper's Table 1:

| fluid | Tc (K) | pc (bar) | omega | vc (cm3/mol) | M (g/mol) |
| --- | --- | --- | --- | --- | --- |
| O2 | 154.58 | 50.430 | 0.0222 | 73.529 | 31.9988 |
| CH4 | 190.60 | 46.100 | 0.0110 | 98.600 | 16.0428 |

Both fluids are nonpolar, so the dipole moment and the association factor are zero. The
alpha coefficient of Eq. (4) is `c = 0.48508 + 1.55171 w - 0.15613 w^2`, which gives
0.519451 for O2 and 0.502130 for CH4.

### Two ambiguities, declared instead of silently resolved

- **Eq. (2) prints `0.427`.** The Soave constant is 0.42748, and it is 0.42748 that makes
  the printed `b = 0.08664 R Tc / pc` give the SRK critical compressibility 1/3.
  `A_COEFF = 0.42748` is used and `A_COEFF_PRINTED = 0.427` is kept, so the size of the
  rounding is measured rather than argued: it moves density by at most 0.007 %, cp by
  0.025 %, viscosity by 0.005 % and conductivity by 0.005 % over 100–400 K (recorded in
  `sweep.json` → `sensitivity`).
- **Acentric factor.** The repository mechanism carries `omega = 0.025` for O2, the paper
  tabulates 0.0222. The figure uses the paper's value; the repository value is the
  declared sensitivity (0.08 % in density, 1.1 % in viscosity, 0.9 % in conductivity).
  CH4 agrees exactly (0.011 both).

**One calorie conversion, thermochemical.** Chung et al. publish the correlation in
thermochemical calories, so the module now derives `R_CAL` and the ideal-gas `cv` from
the single constant `CAL_PER_JOULE = 1/4.184`. Round 3 converted the heat capacity with
the International-Table value `0.2388458966 = 1/4.1868` while using `R/4.184` in the
denominator of Eq. (9); that mix biased `cv_cal` by 6.68e-04 relative and, with it, the
reported conductivity by at most 4.59e-04 relative (CH4 at 400 K). Both calorie
definitions are 0.07 % apart, far below the 1.5 % conductivity tolerance, so the earlier
verdicts stand; the corrected numbers are what this round reports.

Note that at exactly `(Tc, pc)` the published five-digit constants do **not** give
`Z = 1/3`: the reduced cubic there is a near-triple root, so a 1e-7 coefficient residual
is amplified to ~2e-2 in Z. The test therefore checks the equation of state residual at
the critical point to 1e-12 and only brackets `Zc`, rather than pretending the printed
constants are exact.

## Contents

- `digitise_fig1.py` — stdlib-only extractor for the embedded vector form. Writes
  `figure1-vector.json` (committed: it is the reference vector, 195 kB).
- `srk_chung.py` — SRK + Chung model, SI molar units.
- `test_srk_chung.py` — 12 tests / 23 subtests; ideal-gas limits, `cp` against a
  numerical `dh/dT`, `h_dep` against a pressure integral, `cv < cp`, single-phase root
  selection at 56 bar, the dilute Chung limit, Chung viscosity against Chapman–Enskog
  with independent Lennard-Jones parameters, conductivity against Eucken, coarse physical
  ranges, and provenance of every NASA7/critical constant against the retained mechanism
  file.
- `sweep_properties.py` — 0.25 K grid, 100–400 K, 1201 samples per fluid, 56 bar →
  `sweep.csv` (16 columns, every column named with its unit) and `sweep.json`
  (`forge-property-sweep-v1`, the renderer's input, plus constants and sensitivities).
- `compare_reference.py` — residuals against the two reference sets, kept apart (below).
- `render_figures.mjs` — four `renderPaperComparison` calls composed into one `<svg>`.
- `checks.py` — the five campaign checks, computed from the files the job produced. It runs
  in two phases (`--phase compute`, `--phase render`) because the two environments are not
  the same environment; see *Compute and render are separate phases* below.
- `job.sh` — the batch payload: the compute phase only (bash, correct under the adapter's
  `set -euo pipefail`).
- `probe_models.py` — **deprecated**. An earlier plan used Cantera's `RedlichKwong` and
  high-pressure transport; this trial's Cantera qualification is C++ SDK only, and the
  paper's alpha function (Graboski–Daubert) is not one of Cantera's options, so the model
  is implemented directly from the paper instead. The file is kept as the record of that
  probe, not as part of the pipeline.

## Two reference sets, never merged

- **Published curve** — the model curve drawn in the paper, from the PDF path geometry.
  A deviation here measures how faithfully this implementation reproduces the paper's own
  SRK+Chung model.
- **Published symbols** — the NIST comparison points printed in the same panels. A
  deviation here is a model-versus-data difference, i.e. the paper's result, not this
  implementation's.

`figure1-vector.json` holds both, `cavalieri2025-fig-1-data.json` tags every series with
`origin: paper` or `origin: computed`, and `compare_reference.py` reports the two residual
families separately — plus a third number, the printed symbols' own deviation from the
printed curve, which is what the model-versus-data residual must be compared against
before blaming the implementation.

## Measured figure geometry (declared)

| panel | quantity | frame (pt) | y range | y ticks |
| --- | --- | --- | --- | --- |
| (a) | density | 27.388 171.921 168.268 273.46 | 0–1200 kg/m³ | 7 (step 200) |
| (b) | cp | 206.257 171.921 354.589 273.46 | 0–25 kJ/(kg K) | 6 (step 5) |
| (c) | viscosity | 21.797 32.839 168.268 134.378 | 0–2, ordinate = µ ×10⁴ Pa s | 5 (step 0.5) |
| (d) | conductivity | 211.846 32.839 354.589 134.378 | 0–0.25 W/(m K) | 6 (step 0.05) |

All four panels share x = 100–400 K with 7 ticks (step 50). Frames and ticks are
0.323 pt grey `(0.149,0.149,0.149)` = `#262626`; the model curves are 0.621 pt black;
markers are filled circles of 2.856–2.859 pt outer diameter with a 2.111–2.114 pt inner
disc at the same centre (476 of them); axis glyphs are 4.5–4.9 pt tall, i.e. about
6.5 pt type. The dashed CH₄ curve uses dash array `[1.9881, 1.9881]`.

### Axis units, and the mistake they caused

Panel (c) is drawn on the paper's own scale: the ticks run 0, 0.5, 1, 1.5, 2 and the
published axis text carries the multiplier, `µ [Pa s] · 10⁻⁴`. The plotted ordinates are
therefore **µ × 10⁴**: the sweep stores SI `mu_Pas` = 1.0e-5…1.6e-4 and
`render_figures.mjs` multiplies by `1e4` when it builds the series. The first revision
of the renderer re-typeset the title as `Viscosity (Pa s)` and dropped the multiplier,
so the figure claimed that an ordinate of 1.5 was 1.5 Pa s — four orders of magnitude
wrong — while the numbers in the data file were right. That is exactly the failure mode
a self-check must not excuse, so the verdict is now derived from two measurements
rather than from the label:

1. `source_and_units` takes the largest `mu_Pas` in the sweep for each fluid, multiplies
   it by 1e4 and divides by the maximum of the *published* panel (c) curve. The ratio is
   **0.99996 (O₂)** and **0.99999 (CH₄)**: the scaling is the paper's. If the figure
   plotted raw Pa s the ratio would be 1e-4 and the check fails.
2. In the render phase the same check walks every one of the 2 402 plotted panel (c)
   ordinates and requires `y == mu_Pas × 1e4` to a relative 1e-9, and `figure_fidelity`
   requires the string `1e-4 Pa s` in both the panel (c) recipe and the composed SVG.

Retained negative controls (`/workspace/forge-out/runs/cav-fig1-r3-preflight/negatives-c`)
run the *new* verifier over the *old* artifacts: the r3 SVG without the multiplier fails
`figure_fidelity`, and a copy whose panel (c) ordinates are raw Pa s fails
`source_and_units`. The old SVG (`db9d45b5…`), its verification (`db8cc968…`) and the
failed render job's receipts are kept untouched; the corrected figure is a new file.

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
9.3 % relative). Those residuals are kept and reported.

## Composite rendering (`render_figures.mjs`)

`renderPaperComparison` renders one panel per call, so the composite calls it four times
with identical `canvas`/`viewBox` (the form's own coordinate system, `BBox` plus a 2 pt
pad) and inlines the four bodies under a single root `<svg>`. Declared deviations from
the published layout, all of them layout-only:

- **Legend strip.** The published legend sits inside panel (a) at
  `[141.06, 248.773, 165.037, 270.056]` (PDF pt, y up), on top of the density curve, and
  it labels both fluids and all three origins. That box cannot be reused, so the legend
  is moved into a 60 pt strip added *below* the paper's drawing area (which ends at SVG
  y 278.108). Row `i` is drawn at `y = 284.5 + i·8.6`; `rowHeight` must exceed the 6.5 pt
  type size or the row baselines collide, which is why the strip is taller than the
  published legend box. Panels (b)–(d) pass `x = y = -1000` so their rows are emitted
  outside the viewBox instead of being drawn four times.
- **Panel titles.** `(a)`/`(b)` frames start only 2.65 pt below the top of the form, so
  the re-typeset quantity titles would be clipped. The canvas is extended upward by
  12 pt; the viewBox starts at that negative y so the titles are inside it.
- **Tick labels.** Extracted tick positions can fall a fraction of a point outside a
  frame, which printed a spurious `-0.000492` label beside the real `0`. Ticks are
  clamped onto the declared limits and de-duplicated before labelling. Tick baselines
  are pushed 6.8 pt below the frame and the axis title 14.6 pt below it, because 6.5 pt
  type does not fit in a 5 pt offset.
- **Panel letters.** The published figure sets `(a)`–`(d)` *beneath* the x-axis title,
  centred on their frame. A first revision put them above each frame at the left edge;
  they are now placed at `x` = frame centre and `y` = frame bottom + 22.4 pt, which
  clears the 6.5 pt axis title by 7.8 pt. The glyphs are re-typeset, not extracted.
- **Y-axis titles stay horizontal.** The published titles are rotated 90° in the left
  margin (`ρ [kg/m³]`, `c_p [kJ/kgK]`, `µ [Pa·s]·10⁻⁴`, `λ [W/mK]`).
  `renderPaperComparison` emits only horizontal `<text>` elements — it accepts `labels`
  as `{x, y, text}` and applies no `transform` — so the re-typeset titles sit above their
  frames instead. This is a **declared, unresolved** difference: it is not measured
  fidelity, and the axis *content* is preserved (quantity, symbol and unit) even though
  the placement is not.
- **Typography.** Labels are re-typeset in a Times serif at the measured 6.5 pt; the
  paper is Computer Modern. A metric-substituted font is used for raster previews and
  the substitution is reported by `svg-render.mjs`, not hidden.
- **Legend shape.** Three in-frame rows (solid O₂, dashed CH₄, open circle NIST) in panel
  (a) become one external 6-row strip, because the renderer emits one row per series and
  the two origins have to stay visibly distinct. Declared.

## Compute and render are separate phases

The scheduler container has `python3` and `node`, but it does not mount `/forge`, and
`/forge/plots/paper-style.mjs` — the campaign renderer both this module and the campaign
contract use — lives only there. A first attempt to render inside the job therefore died on
`ERR_MODULE_NOT_FOUND` after the numerics had already succeeded. The honest repair is not to
vendor a copy of the renderer (that would fork the plot contract) and not to call the job a
failure when its numerics are complete; it is to split the verifier into two phases whose
outputs are joined by hashes:

| phase | where | command | produces |
|---|---|---|---|
| compute | batch (`cantera32`) | `job.sh <source-root> <run-dir>` | `out/sweep.{csv,json}`, `out/comparison.json`, `repro/out/` second sweep, `verification-compute.json` |
| render | agent environment | `node render_figures.mjs … && checks.py --phase render --base verification-compute.json` | `out/cavalieri2025-fig-1.svg`, `verification.json` |

`checks.py --phase compute` needs the repeat sweep and checks `source_and_units`,
`reference_coverage`, `numerical_comparison` and `reproducibility` on the pairs it can
actually measure; `figure_fidelity` is reported `unknown` there, citing the missing mount.
`--phase render` takes `--base verification-compute.json`, re-checks `figure_fidelity` and
the render pair, and copies the compute checks forward. If any input hash disagrees between
the phases it exits with a hard error — `the render phase is not looking at the files the
compute phase produced`.

`unknown` is not a failure: `checks.py` exits 0 while a check is merely deferred to the other
phase and prints `checks deferred to the other phase: …`; only a measured `failed` returns 3.
That keeps a compute job green when its numerics are right and its figure is deferred, which
is what actually happened.

## Batch payload

`job.sh <source-root> <run-dir>` runs, in this order: file-hash inventory, the unit tests,
the sweep, the reference comparison, a second independent sweep into `repro/out` for the
reproducibility pair, the compute-phase campaign checks, and an output inventory; it writes
`rc.txt` with every stage status (`payload_rc= hashes_rc= tests_rc= sweep_rc= compare_rc=
sweep_repro_rc= checks_rc=`) and exits nonzero if any stage failed. It reads no file outside
`<source-root>` and writes nothing into the repository. It is written for
`bash -euo pipefail` with no pipeline whose reader can close early, because the control
adapter runs it under exactly those options, and it says out loud that the figure build is
deferred (`figure build deferred to the render phase (no /forge mount here)`) instead of
attempting it and failing.

## Status

Model, tests, sweep and comparison are complete and replay byte-identically; the two-phase
verifier is exercised end to end — the compute phase on the artifacts of scheduler job
`125197601`, the render phase natively on the same files, byte-identical sweep
(`a777b603…`) in both environments, 5/5 checks after joining. The figure is built from the
sweep produced in the same scheduler job and joined to it by input hash; the computed curves
are never mixed with the extracted reference vectors.
