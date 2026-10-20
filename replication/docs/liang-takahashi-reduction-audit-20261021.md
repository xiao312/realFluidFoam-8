# Takahashi reduced-property definitions in Liang's citation chain

21 October 2026, Asia/Shanghai. State: source audit and prescribed-state
checks completed; no model change accepted.

The inspected primary sources support arithmetic critical-property averaging.
They do not establish geometric temperature or volume mixing as Liang's
Takahashi reduction. Changing between the supported averaging interpretations
does not explain Figure 6's cold diffusion ratio. At the saved 300 K state,
whole-mixture averaging gives 1.0155 and a hydrogen tracer-in-bath interpretation
gives 0.9791, versus the paper reading 0.9122. The exact quantity plotted as
`D` remains unspecified.

Takahashi mentions modified hydrogen critical constants while evaluating the
older Slattery–Bird chart. The final chart's construction does not explicitly
restate that substitution, so its use there is not established. A contemporary
primary calculation corroborates Newton's `+8 K`, `+8 atm` rule. Testing this
historical rule only as a transport sensitivity gives H₂ = 1.0251, still above
the paper. Chart interpolation and separate ideal/real flame compositions
also fail to close the gap.

A recovered Liang dissertation changes the interpretation of the target:
its Figure 8-5 labels **density-weighted** diffusion and `lambda_real/lambda_ideal`.
The journal Figure 6 instead labels **pressure-weighted** diffusion and the
inverse conductivity ratio. Both figures' text confirms their own labels.
These are distinct source definitions, not a corrected glyph reading.

## What the original Takahashi paper prescribes

[Takahashi, pp. 418–419](https://www.jstage.jst.go.jp/article/jcej1968/7/6/7_6_417/_pdf)
defines the correction of the pressure-diffusivity product:

```text
F(Tr, Pr) = D*p / (D*p)^0
Tr = T / Tc
Pr = p / Pc
```

The data reduction uses the **base gas's** critical temperature and pressure.
For a mixed base gas, Eqs. (8)–(9) use Kay's rule:

```text
Tc_bath = sum(x_bath,k * Tc,k)
Pc_bath = sum(x_bath,k * Pc,k)
sum(x_bath,k) = 1
```

Table 1 distinguishes the tracer from the base gas and identifies the
composition of mixed baths. The calibration chiefly concerns self-diffusion
and tracer diffusion, rather than arbitrary finite multicomponent reacting
mixtures. Its trace-gas derivation and empirical extension do not prescribe
one unique symmetric binary matrix for a flame.

**21 October qualification:** page 419's sentence replacing experimental
hydrogen critical constants with Newton's modified values belongs to
"Application of the SB Chart", before "Preparation of a New Generalized Chart".
The latter section says to use base-gas critical properties and Eqs. (8)–(9)
for mixed baths, without explicitly repeating Newton's substitution.
Table 1's hydrogen range `Tr = 1.67–2.72` is consistent with 55–90 K divided
by the physical hydrogen critical temperature near 33 K; it is not consistent
with dividing those temperatures by approximately 41 K. This is supporting
evidence, not a recovered implementation. Newton's rule therefore remains
a historical sensitivity, not a demonstrated omission in the current
Takahashi implementation. Takahashi does not print Newton's numerical values.
[Newton's publisher record](https://doi.org/10.1021/ie50303a014)
identifies *Activity Coefficients of Gases*, 1935, volume 27, pp. 302–306;
the original full text was not obtained.
[Maron and Turnbull's 1942 primary calculation](https://doi.org/10.1021/ja01261a047)
explicitly uses `Tc + 8` and `Pc + 8` for hydrogen and helium following Newton,
with temperature in kelvin and pressure in atmospheres. The indexed text
of the original pp. 2195–2198 was available through a public PDF mirror;
local PDF download failed. This corroborates the historical rule without
claiming direct inspection of Newton's numerical tables. Later
temperature-dependent quantum-fluid constants are a different prescription.

The correction multiplies a dilute coefficient already evaluated at the same
pressure. An extra inverse-pressure factor would be an error.

## What the cited combustion papers add

| Source | Inspected statement | Reduced-property conclusion |
|---|---|---|
| [Liang ref. 5: Pons 2009](https://doi.org/10.1080/13647830802368821), p. 63 | CHEMKIN/TRANSPORT dilute binary coefficients multiplied by `f(Tr,Pr)` | Does not print a pair-composition normalization or alternative critical mixing equation |
| [Ref. 6: Huo 2014](https://doi.org/10.1016/j.combustflame.2014.06.005), Section 2.2 | Takahashi for binary diffusivity; implementation details referred to Yang 2000 and Meng 2005 | Does not establish geometric/volume reduction |
| [Ref. 7: Wang 2015](https://doi.org/10.1080/00102202.2014.973955), pp. 62–63 | Refers to Huo's formulation and Yang's property treatment | Supplies no distinct Takahashi mixing rule |
| [Ref. 8: Jorda Juanos 2017](https://doi.org/10.1016/j.combustflame.2017.01.030), Eq. (7) | CHEMKIN multicomponent diffusion; documented real transport corrections concern viscosity/conductivity | Cannot establish a Takahashi binary reduction |
| [Ref. 10: Giovangigli 2011](https://doi.org/10.1080/13647830.2010.527016), Sections 3.3/4.2 | Dense kinetic theory with collision/free-volume factors and thermodynamic driving forces | An alternative transport formulation, not a different Takahashi averaging prescription |
| [Yang 2000](https://www.yang.gatech.edu/publications/Journal/P%26C%282000%2C%20ref19%2C%20Yang%29.pdf), p. 929 | Dilute Chapman–Enskog binary diffusion followed by a reduced-temperature/pressure chart | Does not specify an alternative critical mixing equation |
| [Meng 2005](https://doi.org/10.1017/S0022112004003106), Eqs. (3.16)–(3.17) | Fuller dilute correlation followed by Takahashi | Provides a numerical binary-mixture check below, but not a distinct printed mixing rule |

Geometric pair temperatures and cube-root volume combining rules do appear
in corresponding-states conductivity/viscosity models. Their occurrence in
the same property library does not justify inserting them into Takahashi.
No such prescription was established in the inspected diffusion sections.
The earlier [diffusion literature audit](liang-diffusion-literature-20261020.md)
records the broader validation limits of these sources.

## Current implementation and possible interpretations

[Cantera 3.2.0, `updateCorrectionFactors()`](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/HighPressureGasTransport.cpp#L173)
normalizes the two local mole fractions before arithmetic averaging.
`cantera-liang/StagedTransport.h` retains this rule:

```text
z_i = x_i / (x_i + x_j)
z_j = x_j / (x_i + x_j)
Tc_ij = z_i*Tc_i + z_j*Tc_j
Pc_ij = z_i*Pc_i + z_j*Pc_j
F_ij = F(T/Tc_ij, p/Pc_ij)
```

Its nonnegative floors avoid an undefined empty pair. The tested baseline also
uses the corrected original Table 2 coefficient and the declared
`1 <= Tr <= 5` bounds.

| Interpretation | Source support and limit |
|---|---|
| Pair-normalized arithmetic rule | Implemented in pinned Cantera; reduces to the bath's constants for a binary tracer limit. Its extension to every finite reacting-mixture pair is not explicitly prescribed by Takahashi. |
| Whole-mixture Kay rule | Matches the original concept for a trace gas in a mixed bath. Applying one bulk factor to every finite-concentration pair is an additional approximation. Already tested in methane flames without closing the gap. |
| Species-specific remaining bath | Define bath fractions as `x_j/(1-x_i)` for `j != i`. Useful for a named tracer's mixture diffusivity. Applying it at large `x_i` is a diagnostic; it is not a symmetric binary matrix. |
| Geometric temperature / volume combining | Not established as a Takahashi rule in these primary sources. No fitted or speculative flame variant is justified. |
| Modified hydrogen critical constants | Takahashi names Newton in the Slattery–Bird comparison; its use in the final chart is not established. Maron/Turnbull corroborate `+8 K`, `+8 atm`. Liang's use remains unknown. Test only as a transport sensitivity, not an EoS change. |

## Quantitative cold-state comparison

The independent local probe uses saved LJ-control job **125069072**, row 77,
at **299.99827 K and 100 atm**. It changes only the reduction interpretation
in a prescribed-state calculation. It does not solve a flame. Local mole
fractions are H₂ = 0.287574, O₂ = 0.149639 and N₂ = 0.562766, with small
minor-species contributions.

| Named ratio `Dreal/Dideal` | Pair-normalized baseline | One bulk factor | Remaining-bath tracer diagnostic |
|---|---:|---:|---:|
| H₂ mixture coefficient | 1.036511 | 1.015466 | 0.979106 |
| O₂ mixture coefficient | 0.986750 | 1.015466 | 1.033411 |
| N₂ mixture coefficient | 0.996923 | 1.015466 | 1.048636 |
| H mixture coefficient | 0.990676 | 1.015466 | 1.015466 |
| OH mixture coefficient | 0.983884 | 1.015466 | 1.015466 |
| H₂O mixture coefficient | 0.983007 | 1.015466 | 1.015487 |

The entire set of 13 baseline mixture ratios spans 0.982188–1.036511.
The paper's red curve reads **0.912239**, with graphical bounds
**0.910448–0.918209**, at 300 K. Neither the bulk rule nor the tracer
interpretation reaches it.

The important binary corrections show why:

| Pair | Tc,pair, K | Pc,pair, MPa | Tr | Pr | F |
|---|---:|---:|---:|---:|---:|
| H₂–O₂ | 74.730 | 2.58107 | 4.01443 | 3.92570 | 1.048675 |
| H₂–N₂ | 94.735 | 2.68848 | 3.16670 | 3.76885 | 1.033436 |
| O₂–N₂ | 132.153 | 3.74353 | 2.27008 | 2.70667 | 0.979118 |

For a fixed composition, the mixture-ratio numerator cancels:

```text
R_i = sum_j(x_j / D0_ij) / sum_j(x_j / (D0_ij * F_ij)), j != i
```

This is a positive weighted harmonic combination of the pair factors; it
cannot lie outside their range. Altering between `1-X_i` and `1-Y_i`
in otherwise matched numerator definitions therefore does not change this
real/ideal coefficient ratio.

A fixed 0.01 mole-fraction grid samples **5,151 H₂/O₂/N₂ compositions**
at each temperature using their existing physical critical data. Its
arithmetic-Kay factor range is 0.953103–1.063817 at 300 K and
1.001110–1.063817 at 400 K. The minimum is pure O₂ in each sampled set.
This is a sampled envelope, not a proof over every possible mixture or a
validation of the correlation. Together with the actual 13-species checks,
it makes ordinary major-species averaging an unlikely explanation for the
paper's cold ratio.

## Newton correction and chart interpolation

Applying `Tc,H2 += 8 K` and `Pc,H2 += 8*101325 Pa` to the existing
hydrogen input gives effective values **41.18 K and 2.1106 MPa**.
These are derived from our pinned physical input, not transcribed values
from Newton. This diagnostic is not evidence that Takahashi's final chart
requires the substitution. At the same saved 299.998 K state:

| Named mixture ratio | Physical H₂ critical data | Newton transport reduction |
|---|---:|---:|
| H₂ | 1.036511 | 1.025150 |
| O₂ | 0.986750 | 0.985065 |
| N₂ | 0.996923 | 0.993684 |

All 13 Newton ratios span **0.982059–1.025150**. The bulk factor becomes
1.007460. The H₂ remaining-bath result stays 0.979106 because hydrogen
has been excluded from its bath. Using `+8 bar` instead of `+8 atm`,
as a unit-transcription sensitivity only, changes any cold mixture ratio
by at most **0.000106**. No version reaches the paper reading.

Takahashi's original Figure 2 has linear pressure and correction-factor
axes, with labelled reduced-temperature isotherms. The inspected paper
does not prescribe a numerical interpolation algorithm.
[Cantera's source](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/HighPressureGasTransport.cpp#L25)
evaluates Eq. (10) at the adjacent pressure rows, then linearly interpolates
the factor in reduced pressure.

The following checks keep every original Table 2 coefficient:

| Pair, physical critical data | Current factor | Linear interpolation between chart isotherms | Minimum/maximum of containing chart cell's four corners |
|---|---:|---:|---:|
| H₂–O₂ | 1.048675 | 1.043543 | 1.011170–1.055136 |
| H₂–N₂ | 1.033436 | 1.031036 | 1.011170–1.055136 |
| O₂–N₂ | 0.979118 | 0.974151 | 0.941602–0.999271 |

The hydrogen pairs occupy `3 <= Tr <= 5`, `3 <= Pr <= 4`; O₂–N₂
occupies `2 <= Tr <= 2.5`, `2.5 <= Pr <= 3`. Newton's correction
leaves those same cells. Any convex interpolation among the four corners
therefore remains above 0.912. Log-pressure interpolation at the actual
temperature, an unsupported sensitivity rather than an original-paper rule,
changes these factors by at most 0.000551. The chart provides no
source-supported interpolation route to the pressure-weighted target.

## Dissertation definition and density-weighted diagnostic

[Liang's 2018 dissertation](https://www.riss.kr/pdu/ddodLink.do?id=T14998128),
printed pp. 171–172 / PDF pages 181–182, explicitly uses:

```text
black: lambda_real / lambda_ideal
red:   (rho*D)_real / (rho*D)_ideal
```

The journal Figure 6 and its adjacent paragraph explicitly use
`lambda_ideal/lambda_real` and pressure-weighted `P*D`. Both source images
were visually inspected. At equal pressure, the journal's red definition
reduces to `Dreal/Dideal`; the dissertation's density factor does not cancel.
Neither source identifies a diffusion species.

For this diagnostic, the named `D` is Cantera's mixture coefficient for
mass-average flux with a mole-fraction gradient:
`D_k = (1-Y_k)/sum_j(X_j/D_kj)`, `j != k`. This is an explicit diagnostic
choice, not an attribution to Liang's unspecified plotted quantity.

At 300 K in the author-pair Case 5 profile, the density ratio is **0.971838**.
The resulting ratios are:

| Species | Same `T,p,Y`: `rhoD` ratio | Separate Case 1/5 profiles at equal T |
|---|---:|---:|
| H₂ | 1.007275 | 1.007278 |
| O₂ | 0.958953 | 0.958719 |
| N₂ | 0.968939 | 0.968234 |

All 13 species span **0.954523–1.007275** for same-state properties and
**0.954351–1.007278** for separate profiles. LJ control gives essentially
the same bounds. These values still exceed the journal's roughly 0.912
reading at 300 K, but they test the dissertation's different definition.
The dissertation red curve first becomes visible at about **319.509 K,
ratio 0.9000**; it supplies no 300 K reading. Do not extrapolate it.

Separate profiles were compared at their first upward crossing of each
common temperature, without spatial alignment or extrapolation. At 300 K,
the Case 5 and Case 1 H₂ mole fractions are 0.287413 and 0.286775.
That small composition difference changes the density-weighted H₂ ratio
by only 0.000004; the O₂/N₂ changes are below 0.00071. Thus using separate
flame profiles does not explain this cold discrepancy.

The separate-profile conductivity ratio `lambda_real/lambda_ideal` is
1.16720 at 300 K, 1.07579 at 500 K, 1.02408 at 1000 K and 1.01260 at
1500 K. Its sign agrees with the dissertation definition. At visible
1200 K, however, it is 1.01782 versus the dissertation's 1.05720; at
1500 K it is 1.01260 versus 1.02474. The dissertation and journal curve
geometries also differ, so relabelling or inversion is not enough.

Using the dissertation's vector-extracted red curve at visible temperatures:

| T, K | Dissertation `rhoD` | Calculated H₂ | Calculated O₂ | Calculated N₂ |
|---|---:|---:|---:|---:|
| 320 | 0.90059 | 1.00383 | 0.96377 | 0.97105 |
| 400 | 0.96267 | 1.00166 | 0.97782 | 0.98294 |
| 500 | 0.99364 | 1.00353 | 0.98768 | 0.99220 |
| 1000 | 1.02091 | 1.00946 | 1.00454 | 1.00356 |
| 1500 | 1.02931 | 1.01518 | 1.01302 | 1.00777 |

Calculated columns use the separate profiles. Vector readings interpolate
between visible dashed-curve vertices; their displayed decimals identify
the extraction, not experimental accuracy. None of these three named
coefficients follows the entire dissertation curve.

The saved comparisons use Case 1/5 jobs **125068730/125068936** for
author pairs and **125068739/125069072** for LJ. There are 312
species-state rows and 30 independent C++ ratio checks, with maximum
relative difference `6.66e-16`. The dissertation PDF SHA-256 is
`806906f751d2b257dae7a9e66111158c5aaa8ec227fdd8f5ea909a57a52c3a85`.

## Independent binary check in the citation chain

Meng's Table 2 gives a **50/50 molar H₂/O₂ mixture at 200 K**. Its listed
diffusivities are `4.04e-5`, `3.88e-7` and `9.92e-8 m²/s` at 1, 100
and 400 atm. These are calculated property examples, not new experiments.
The primary PDF's extracted text was read through the web tool; download and
page-image retrieval failed. Keep this transcription provisional until its
table is visually checked.

At 100 atm, normalizing its value by the 1-atm value gives **0.960396**.
The current physical-critical arithmetic pair rule gives **0.963020**,
or **0.273% higher**, at `Tr = 2.13038`, `Pr = 3.19486`.
This supports the broad reduction scale in that cited implementation.
It does not determine Liang's inputs or validate a flame.

At 400 atm the corresponding values are 0.982178 and 0.980692. The current
calculation uses its `Pr >= 5` endpoint policy at actual `Pr = 12.7794`;
this out-of-table agreement is not validation of that policy.

The previous methane φ = 1.40 result remains relevant: whole-mixture
averaging gave Case 5 = **5.781626 cm/s**, further from Liang's
5.642738 cm/s than the pair-normalized baseline. See the
[recorded experiment](liang-diffusion-and-inversion-20261020.md).
No new flame repetition is justified by the averaging evidence alone.

## Evidence and next decision

Keep the current reduction as an identified baseline. Newton's corroborated
rule is a source-backed sensitivity, but these property checks do not justify
claiming it fixes Liang's result. Qualify the provisional Meng table before
using it as a numerical acceptance test. Preserve the two source definitions
and the unknown `D` identity; do not choose a species, ratio inversion or
critical-property rule by fitting the curve. A future change must also
preserve binary symmetry and demonstrate both property behavior and the
methane Case 4-to-5 decrement.

Artifacts are in ignored
`state/liang-hydrogen-20261020/takahashi-reduction/`:
`probe.py`, `summary.json`, `ratios.csv`, `pairs-300K.csv` and `sources.json`;
`newton_and_interpolation.py`, `newton-summary.json`, `newton-ratios.csv`,
`newton-pairs-300K.csv`, `interpolation-300K.csv`;
`density_weighting.py`, `density-weighting-summary.json` and
`density-weighted-ratios.csv`, plus `thesis-density-comparison.csv`.
The original chart's page-4 render is
also preserved.
The source manifest includes primary URLs, pre-existing PDF hashes, inspected
source hashes, and explicit access limits. No failed download is presented as
an obtained paper.

```powershell
& state/equilibrium-venv/Scripts/python.exe state/liang-hydrogen-20261020/takahashi-reduction/probe.py
& state/equilibrium-venv/Scripts/python.exe state/liang-hydrogen-20261020/takahashi-reduction/probe.py --apply
& state/equilibrium-venv/Scripts/python.exe state/liang-hydrogen-20261020/takahashi-reduction/newton_and_interpolation.py
& state/equilibrium-venv/Scripts/python.exe state/liang-hydrogen-20261020/takahashi-reduction/newton_and_interpolation.py --apply
& state/equilibrium-venv/Scripts/python.exe state/liang-hydrogen-20261020/takahashi-reduction/density_weighting.py
& state/equilibrium-venv/Scripts/python.exe state/liang-hydrogen-20261020/takahashi-reduction/density_weighting.py --apply
```

All plan/apply paths passed. The initial 117 saved-state species checks include 27 independent
replays of the C++ H₂/O₂/N₂ ratios; their maximum relative difference is
`6.66e-16`. Input hashes are preserved in `summary.json`.
The original Takahashi PDF SHA-256 is
`88e9eaa011e6b17b4ea2dd1253c36e363865776f4c8a8fa4db8fb507ada3945e`;
the hydrogen critical/species input hash is
`b093c29ac896bef71f36f5fbfc1f799bdc200f259efcf9b383138076253c3346`.
No solver edits, remote jobs, source commits or fitted parameters were made.
