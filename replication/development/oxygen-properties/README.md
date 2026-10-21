# Pure-O₂ real-gas properties: PR and volume-translated PR at 5.61 MPa

Inspectable re-implementation of the real-gas thermodynamic model used by
Müller & Pfitzner (2015), *Large-eddy simulation of transcritical LOX/CH₄ jet
flames*, §2.2 "Real-gas thermodynamics" (paper Eqs. 8–13), evaluated for the
exact conditions of their Fig. 1: **pure O₂, p = 5.61 MPa, T = 85–300 K**.

Everything here is Python 3 standard library only (no NumPy, no SciPy, no
Cantera): the whole model is a few hundred lines of arithmetic, so the
reproduction does not depend on any third-party numerical library version.

| Path | Purpose |
| --- | --- |
| `oxygen_properties.py` | model: PR EoS, Abudour volume translation, departure functions, cp |
| `test_oxygen_properties.py` | 15 self-checks: ideal-gas limit, analytic vs finite-difference derivatives, critical-point algebra, literature anchors |
| `run_properties.py` | production sweep → CSV samples, deviation statistics, environment/version record |
| `critical_tolerance.py` | independent derivation of `c1`/`δc` and the tolerance they carry into the plotted density |
| `job.sh` | scheduler entry point (serial, `OMP_NUM_THREADS=1`) |

## Model

Molar volume of the mixture PR EoS, Eq. (8):

    p = R T / (v_PR - b) - a(T) / (v_PR² + 2 b v_PR - b²)

with `a(T) = 0.45724 (R Tc)²/pc · α(T)`, `α = [1 + κ(1 - √(T/Tc))]²`,
`κ = 0.37464 + 1.54226 ω - 0.26992 ω²`, `b = 0.07780 R Tc/pc`.
The cubic is solved in the compressibility factor `Z = p v/(R T)`:

    Z³ - (1-B)Z² + (A-3B²-2B)Z - (AB-B²-B³) = 0,   A = a p/(R²T²),  B = b p/(RT)

because the `Z`-cubic is far better conditioned than the `v`-cubic (coefficient
magnitudes are O(1) instead of O(10⁻¹⁰)). Roots come from a trigonometric
Cardano solution; the physical root is the smallest positive root whose
pressure residual is below 1e-9 relative, which for a subcritical isotherm
selects the liquid branch — the branch Fig. 1(a) plots.

Volume translation, Eqs. (9)–(13):

    v_m = v_PR + c + δc · 0.35/(0.35 + d)                    (9)
    c   = (R Tc/pc) [ c1 - (0.004 + c1) exp(-2 d) ]          (10)
    c1  = Σ x_i c1_i,  c1_i = 0.4266 Zc_i - 0.1101           (11), (12)
    d   = -v_PR²/(R Tc) (∂p/∂v_PR)|_T                        (13)

Caloric properties use the departure-function formalism with the **uncorrected
PR volume**, exactly as the paper states ("it was not possible to find an
analytical solution for the departure function when the volume-translation
method is considered. Therefore, we use the uncorrected PR EoS in the
evaluation of the caloric properties"):

    h = h_ig(T) + h_dep(T, v_PR),  h_dep = p v - R T - (a - T a')/(2√2 b) ln[...]
    cp = cv - T (∂p/∂T)²_v / (∂p/∂v)_T,   cv = cp_ig - R + cv_dep
    cv_dep = -T a''/(2√2 b) ln[ (v + (1+√2) b) / (v + (1-√2) b) ]

`cp` is implemented both analytically (from the closed-form `h_dep`) and by a
4th-order central difference of `h(T, p)`; the two agree to <1e-7 relative at
every temperature in the sweep, including the pseudo-critical region, which
validates the algebra of both `h_dep` and `cv_dep` independently.

## Constants and provenance

| Constant | Value | Source |
| --- | --- | --- |
| `R` | 8.314462618 J/(mol K) | CODATA 2018 exact value of `N_A k_B` |
| `M_O2` | 0.0319988 kg/mol | IUPAC 2013 standard atomic weights |
| `Tc` | 154.581 K | NIST WebBook (the reference used by the paper) |
| `pc` | 5.043e6 Pa | NIST WebBook |
| `ω` | 0.022 | NIST WebBook |
| `Zc_PR` | 0.3074 | PR critical compressibility implied by Ωa, Ωb |
| `Zc_exp` | 0.288 | NIST WebBook critical compressibility of O₂ |
| Shomate O₂ | A=31.32234, B=-20.23531, C=57.86644, D=-36.50624, E=-0.007374, F=-8.903471 | NIST WebBook, 100–700 K |

Ideal-gas `cp`/`h` are integrated from the NIST Shomate correlation (100–700 K),
i.e. inside its stated validity range over the whole 85–300 K sweep except the
lowest 15 K, where it is used as the paper's "NASA polynomials at a low
reference pressure" analogue. Temperature in the Shomate formula is `t = T/1000`.

## One inference, stated explicitly

The paper prints Eq. (12) with `Zc_i` and Eq. (9) with `+δc`, but does not state
which `Zc` enters Eq. (12) (the PR value 0.3074 or the experimental 0.288) nor
the sign convention of `δc`. The choice is **not tuned**: it is fixed by the
requirement that the model be exact at the critical point, where `d → 0` and
Eq. (9) must return the experimental critical volume `Zc_exp R Tc/pc`. That
requires `c1` evaluated with `Zc_exp` and
`δc = (R Tc/pc)(Zc_exp - Zc_PR) < 0`, which gives at `(Tc, pc)`

    v_m = (R Tc/pc)(Zc_exp - 0.004),

i.e. the experimental critical volume up to the `-0.004` term that is part of
Eq. (10) itself (asserted in `test_translation_algebra_at_critical_point`).
With the alternative (`c1` from `Zc_PR`) the 85 K density comes out at
1081 kg/m³, 8 % below NIST, so the alternative is excluded by the data as well.

Sensitivity: matching the NIST 85 K density exactly instead of to 0.07 % would
require `Zc_exp = 0.28782` instead of 0.288 (a 0.06 % change, inside the spread
between NIST and other compilations for O₂). `Zc_exp = 0.288` is kept as the
published/reference value and the residual 0.07 % is reported, not fitted away.

`critical_tolerance.py` re-derives both constants from that one requirement and
bounds their effect on the plotted curve (rerun it to reproduce every number):

| Perturbation | Δρ at 85 K | Δρ at the 157 K knee |
| --- | --- | --- |
| `c1` from Eq. (12) with `Zc_PR` (paper read literally) | −7.20 % | −0.28 % |
| `c1` ± 5 % | ±0.60 % | ±0.02 % |
| `δc` ± 10 % | ±0.05 % | ±0.62 % |
| `δc` from the *exact* critical volume, i.e. including the `−0.004` residual | −0.11 % | −1.25 % |
| `Zc_exp` ± 0.0005 (NIST `Vc = 73.4 cm³/mol` quoted to 3 digits) | ±0.013 % | — |

Two consequences are recorded rather than hidden. First, the `−0.004` constant
inside Eq. (10) survives at the critical point, so the model maps `(Tc, pc)` to
`72.38 cm³/mol` instead of `Vc = 73.4 cm³/mol`; `critical_tolerance.py` reports
that −1.39 % residual explicitly. Second, removing it (the "exact critical
volume" row) moves the 157 K knee *further* from the published curve, whose
signed deviation there is already −1.35 %, so the retained form is the one the
published figure itself supports.

## Results at p = 5.61 MPa

Deviations of the computed curves from the **published vector curves** of
Fig. 1 (extracted from the PDF plot frame; see the figure-fidelity evidence for
the extraction provenance) and from the published NIST markers, `T = 85–299.5 K`:

| Quantity | vs published curve | 85–150 K | 150–165 K | 165–300 K |
| --- | --- | --- | --- | --- |
| ρ_PR | 1.20 % max (158.2 K), rms 0.18 % | 0.016 % | 1.20 % | 0.041 % |
| ρ_VTA | 1.35 % max (158.2 K), rms 0.21 % | 0.067 % | 1.35 % | 0.064 % |
| cp (PR) | 20.9 % max (85 K), rms 4.1 % | 20.9 % | 11.4 % | 0.157 % |

Every published NIST marker is compared at its own abscissa (all 48 density
markers, all 54 cp markers; the model is evaluated at the marker temperature,
no reference ordinate is moved, dropped or synthesised):

| vs NIST markers | max deviation | at | rms | at 85 K | 85-130 K |
| --- | --- | --- | --- | --- | --- |
| ρ_PR | 12.84 % | 85 K | 6.11 % | +12.84 % | +12.84 % to +8.59 % |
| ρ_VTA | 8.54 % | 160 K | 2.74 % | **-0.071 %** | -0.07 % to +0.94 % |
| cp (PR) | 22.8 % | 157 K | 7.71 % | -5.83 % | -5.83 % to +5.35 % |

The low-temperature band 85-130 K is the one the paper's argument rests on:
there ρ_VTA stays within **0.94 %** of every NIST marker and ρ_PR is
+8.6 % to +12.8 % high, i.e. the volume translation is doing exactly what the
paper says it does (+12.84 % → -0.07 % at 85 K). Our cp stays within
5.8 % of every marker in that band and changes sign near 112 K, whereas the
published cp **curve** is 22.1 % below its own 85 K NIST marker.

The three large marker deviations left in the table are all inside the
pseudo-critical knee (157-160 K), where markers 1 K apart differ by 2-40 % and
`dρ/dT` reaches -90 kg·m⁻³/K.

The 150–165 K band is the pseudo-critical region, where `dρ/dT` reaches
-90 kg/m³/K; the 1.2 % discrepancy there is equivalent to an **abscissa
difference of about 0.1 K**, i.e. at the resolution of the reference figure
(1 px = 0.437 K horizontally, 4.7 kg/m³ vertically in the 200 dpi crop), not a
model discrepancy. Outside that band the density agreement is 0.02–0.07 %.

## Open discrepancy: published cp below ≈130 K

The published PR `cp` curve in Fig. 1(b) is reproduced to 0.16 % for
`T > 165 K` and to 0.28 % at 150 K, but the published *curve* is itself
inconsistent with the published *markers* at low temperature: at 85 K the
curve reads 1298.8 J/(kg K), 22.1 % below the NIST marker 1667.6 J/(kg K) at
the same temperature. Our model gives 1570.3 there (-5.8 % vs the marker). In the pseudo-critical peak the comparison is limited by abscissa
resolution rather than by the model: at 157.5 K the published curve gives
16208 J/(kg K) and ours 17701 (+9.2 %), while at 156 K the published 9605 is
matched to -2.2 % by our 9397 and at 158 K the two agree to 0.1 %
(13901 vs 13914); `dcp/dT` there is of order 2×10⁵ J/(kg K)/K, so a 0.05 K
abscissa difference moves cp by ~10⁴ J/(kg K). The band 150–165 K is therefore
reported separately (max 11.4 %) instead of being quoted as a single number. Below ≈130 K our `cp` is
systematically higher, by 8.5 % at 100 K and 20.9 % at 85 K
(ours 1570.3, published curve 1298.8, NIST marker 1667.6 J/(kg K)).

Because `ρ_PR` is reproduced to 0.02 % over the same range, `a(T)`, `b` and
hence `α(T)` are pinned: the discrepancy cannot come from the EoS parameters,
and any change to them would destroy the density agreement. The remaining
candidates were tested explicitly and **all fail** to reproduce 1298.8 at 85 K:

| Variant | cp(85 K) | cp(100 K) | cp(300 K) | Verdict |
| --- | --- | --- | --- | --- |
| published PR curve | 1298.8 | 1510.0 | 1019.3 | reference |
| analytic PR departure (this module) | 1570.3 | 1649.8 | 1019.1 | +20.9 % at 85 K, 0.02 % at 300 K |
| all caloric terms at the translated volume | 2328.5 | 2304.4 | 1018.6 | wrong direction |
| `cv` instead of `cp` | 962.2 | 927.0 | 672.7 | far too low |
| `cv` with `+T(∂p/∂T)²/(∂p/∂v)` | 354.2 | 204.2 | 326.4 | far too low |
| `cv_dep` omitted (keeps `B`) | 1253.8 | 1372.5 | 1005.0 | closest at 85 K (-3.5 %), but 1.4 % low at 300 K and 9.1 % low at 100 K |
| `cp_ig + cv_dep + B` (no `-R`) | 1830.1 | 1909.6 | 1278.9 | wrong direction |
| numerical `dh/dT` with `h_dep` at the translated volume | 2266.0 | 2133.1 | 1018.5 | wrong direction |
| ideal-gas `cp` from NASA-7 extrapolated to 85 K | higher, not lower | | | wrong direction |

(all values J/(kg K))

A residual `cp` of 12.6 J/(mol K) at 85 K would be needed, versus 21.3 J/(mol K)
from the PR departure functions; no plausible ideal-gas source can absorb a
9 J/(mol K) difference at 85 K while keeping the 300 K agreement. The published
low-temperature `cp` is therefore reported as an **unresolved reproduction
gap**, not as an error in our implementation: our curve is in fact *closer to
the NIST markers* at low temperature than the published one (-5.8 % vs -22.1 %
at 85 K).

Two internal inconsistencies of the paper are recorded for the reviewer, with
the numbers we obtain:

1. The text states the uncorrected PR density deviates 10.33 % from NIST at
   85 K, but the paper's own plotted PR curve is 1328.5 kg/m³ = **+12.85 %**
   above NIST 1177.2 kg/m³ — our value 1328.34 reproduces the *plotted curve*,
   not the text figure.
2. The text states the PR-VTA deviation is 0.005 % at 85 K, matching the
   paper's plotted curve (1177.14 kg/m³); our PR-VTA value is 1176.36 kg/m³
   (-0.071 %), i.e. 0.84 kg/m³ lower. See the `Zc_exp` sensitivity above.

Note also that `1177.2 × 1.1033 = 1298.8`, numerically equal to the published
`cp` value at 85 K. This is almost certainly a coincidence of the printed
digits, but it is recorded because it is the only exact numeric link found
between the text's 10.33 % and any plotted quantity.

## Reproduction

```sh
python3 replication/development/oxygen-properties/run_properties.py --out <run-dir>
python3 replication/development/oxygen-properties/test_oxygen_properties.py
```

`run_properties.py` writes `oxygen-properties.csv` (1100 raw samples, no
smoothing), `deviations.json` (all statistics above, per-marker values) and
`environment.txt` (interpreter, module sha256, input sha256). The run is
deterministic: two invocations produce byte-identical CSV.

### Figures

```sh
node replication/development/oxygen-properties/render_figures.mjs \
  --density-csv <run-dir>/oxygen-properties.csv \
  --cp-csv <run-dir>/oxygen-properties.csv \
  --reference-dir /references/central-payload/assets \
  --out-dir <out-dir> --source-commit <commit> --run-job-id <job-id>
```

`render_figures.mjs` builds `forge-series-v1` data from the raw CSV samples and
the extracted paper series, and writes only the `.svg` string returned by
`renderPaperComparison` from `/forge/plots/paper-style.mjs`, so the Forge
service can replay the exact bytes. It uses the registered `props-r2` recipes
for 1(a) and 1(b): measured frame, axis domains and ticks, the vector axis
glyphs taken from the PDF, and the legend slot. Two consequences are stated
instead of hidden:

* The paper's inset *annotation* box (`rho_in,O2 = 1177.2 kg/m^3`,
  `T_in,O2 = 85 K`) and its leader line to the filled 85 K marker are part of the
  paper's figure annotation layer and are **not** present in the registered
  recipe, so the reproduced figure carries the series legend there instead.
* At the measured `cp` axis limit (0-25000 J/kg/K) the whole 130-300 K range is
  compressed into a few pixels, so the low-temperature `cp` discrepancy of
  Section *Open discrepancy* is not visible in the figure; the committed
  `deviations.json` carries it numerically.

Draw order is paper curves, then computed curves (thinner, so the reference
stroke stays visible where they agree), then the paper's NIST markers on top.

## What this does not claim

This module reproduces the *thermodynamic model* of the paper for one pure
fluid. It does not validate the LES, the flamelet model or any reacting-flow
result, and it does not reproduce the published low-temperature `cp`, which
remains an open discrepancy. Mixture properties (Harstad mixing rules, Eq. 8
for `a_m`, `b_m`) are not implemented here; only the pure-fluid limit is.
