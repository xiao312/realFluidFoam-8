# Liang Figures 1–8: overnight qualification checkpoint

21 October 2026, Asia/Shanghai. The campaign continues until 08:00. Extended
Cantera remains the current calculation stage; the conditional OpenFOAM stage
has not been released. Completion of a numerical solve is recorded separately
from agreement with the paper.

## Completed coverage

All 244 hydrogen baseline calculations completed: 122 with ordinary
Lennard–Jones transport and 122 with the ten applicable author binary-diffusion
polynomials. The baseline covers Figures 3–5 and the stoichiometric profiles
for Figures 6–7. The complete point identities, final values and result hashes
are in [the baseline ledger](liang-hydrogen-baseline-ledger-20261021.json).
Historical build associations are labelled as registry associations, because
the earliest job directories did not record their build paths directly.

All author-polynomial runs have less than 0.5% speed change between the final
two refinement levels. Eight ordinary-transport Case 1 runs exceed that
refinement screen. Neither statement proves domain independence or paper
agreement.

| Figure | Observed result | Remaining qualification |
| --- | --- | --- |
| 1 | SRK density follows the visible model line, 0.272% RMS over 68 readings | Paper triangles and model lines are distinct targets; conductivity mapping remains unresolved |
| 2 | Independent pressure-derivative calculations agree with the native implementation | Paper critical pressures are inconsistent with the stated linear covolume rule and retained species inputs |
| 3 | Author-polynomial Cases 1 and 2 pass all 14 readable speed comparisons; maximum error is 0.53% | Cases 3–5 still fail after native conservation, tighter convergence, domain and grid controls |
| 4 | All twelve selected conservative density/burning-flux points lie within existing image-reading bounds | Keep density and burning-flux comparisons distinct from speed acceptance |
| 5 | Thirty conservative controls pass balances; paired endpoint temperatures differ by less than 0.001 K | Several few-kelvin paper differences remain; Case 3 is still faster and colder than the reported result |
| 6 | Named conductivity and diffusivity ratios are evaluated at saved flame states | Journal and dissertation use different definitions and different curve values; neither current interpretation closes the gap |
| 7 | Conservative Case 5 width agrees; native-Soret Case 5 passes all seven width/peak/location bounds | Conservative HO2/H2O2 peaks are 5.97%/7.36% high; Soret tails still differ and the paper does not identify its case |
| 8(a) | Baseline GRI Cases 1–4 pass; native Soret gives passing discrete rich points | Baseline Case 5 fails three rich conditions; Soret and total enthalpy do not reproduce the Case 4–5 separation |
| 8(b) | Generic ideal GRI driver reproduces the earlier result within 0.003%; full USC/HP sweeps completed at phi 0.90–1.40 | Full author releases do not reproduce the unprovided methane subsets; Hashemi input has a negative rate |

Figure 3 author-polynomial speed errors are +2.20–8.47% for Case 3,
+6.65–10.87% for Case 4 and +7.65–12.13% for Case 5. The partial-temperature
control follows the paper's Case 3* curve, but is not accepted as the author's
implementation. The speed screen is the existing absolute allowance
`max(0.05 cm/s, 1% of reference) + image-reading allowance`.

## Corrections and new primary evidence

The earlier Figure 7 overlay used half the printed horizontal tick interval.
It therefore doubled the apparent calculated width. That display error and the
broader-flame claim are withdrawn. The latest conservative Case 5 has a
corrected 500–2000 K width of 4.819 micrometres versus 4.726 [4.422, 5.025]
in the image. At the same finite paper right edge, it differs by 4.024 K.
The full-domain burned endpoint is a different comparison.

The tight native-Soret Case 5 completed as job `125100455`. Its unchanged
native flux checks pass. Its width is 4.828 micrometres and its HO2/H2O2
peak errors are +1.629%/+2.507%. All seven finite-image width, peak and
location bounds pass. At 2300 K, H2 and HO2 still differ by +8.31%/+9.62%.
Neither this result nor the two Case 3 Soret controls identifies the paper's
unreported case and thermal-diffusion setting. The two complementary tight
Case 5 attempts timed out at one hour; no complete paired-triple claim is made.
The [structure record](liang-hydrogen-structure-controls-20261021.json)
retains 21 selected profiles, and the
[Case 5 qualification](liang-hydrogen-case5-native-20261021.json) retains
native checks and scheduler outcomes.

The current Figures 2–7 gallery uses independently measured axes. Figure 4
retains boundary points within the measured vector precision. Figure 1 now
uses its measured raster ticks too. These corrections change display geometry,
not simulation data. Original paper graphics and explicit computed-data legends
remain in the comparisons.

Liang's recovered dissertation provides an additional primary source.
Its Figure 8-5 labels conductivity as real/ideal and diffusion as density
weighted. The journal labels them ideal/real and pressure weighted, respectively.
The black curve values also change; an unchanged curve with a simple label
typo is not established. Figures 2, 3 and 5 retain effectively identical data.
See the [source comparison](liang-conductivity-source-audit-20261021.md).
The unpublished rich-hydrogen mixing/conformal rule is still absent.

## Diagnostic results

Eight prescribed H2 chemistry-law controls used the same C4-alpha model and
author pair table. Replacing pressure-based chemistry by actual SRK
concentrations changes third-body and falloff concentrations as well.
It lowers speed by only 0.5–0.6% at the tested conditions:

| phi | Case | Pressure-based, cm/s | Actual-concentration, cm/s | Jobs |
| --- | --- | ---: | ---: | --- |
| 1.10 | 2 | 59.421016 | 59.084957 | 125077287 / 125077304 |
| 1.10 | 3, matched energy | 56.580722 | 56.261328 | 125077312 / 125077326 |
| 1.40 | 2 | 79.121107 | 78.732869 | 125077345 / 125077357 |
| 1.40 | 3, matched energy | 75.567697 | 75.196517 | 125077365 / 125077380 |

These results do not justify replacing the pressure-based baseline. Build
125076921, source `6dc503ab778665a0e4e6b6268463efe56a47ffe2`, passed the
six-state independent chemistry-law check to `4.3e-16` relative error.

The [energy-flux audit](liang-energy-conservation-audit-20261021.md) finds
baseline Case 3 flux errors below 0.019 K equivalent. Nonuniform-grid species
advection explains the observed small elemental drift, but refinement does not
close the speed discrepancy. Correcting that drift lowers the rich burned
temperature further from the paper. Boundary energy leakage is negligible.

The completed [30-run conservative campaign](liang-conservation-expanded-20261021.json)
covers Cases 1–5 at phi=1.0/1.3/1.4, with two initial-grid factors and
steady tolerances `1e-7/1e-13`. All predeclared native balance checks pass.
The maximum two-grid speed change is 0.0541%. Rich Cases 1/2 remain within
0.31% of the paper; Cases 3/4/5 remain 5.02–5.97%/8.37–8.55%/9.86–10.22% high.
This separates the remaining model discrepancy from the tested conservation,
mesh and convergence errors.

The dissertation's narrower description of Case 3* as a heat-capacity update
supports a separately named `cp-only-temperature` diagnostic. It retains actual
SRK mixture Cp and ideal-reference species enthalpies only in the temperature
residual. It does not redefine the phase or exported thermodynamic values.
Source `1dfca4b248f5eb4e7cb58beb4488f76ae79e81b7` compiled as build 125079942,
binary SHA256
`2a97d3904cc5641dc358a2a9bfe82520d9afd5034508cd23066bf1093cc08fe3`.
All eight pilots completed. At phi 1.10 the ideal baseline and diagnostic both
give 57.212396 cm/s, differing by less than `3e-14` relative; at phi 1.40 both
give 76.132282 cm/s. Nonideal Case 3* changes from 56.937076 to 55.983576 cm/s
and from 2449.975 to 2444.747 K at phi 1.10. At phi 1.40 it changes from
76.014137 to 74.944278 cm/s and from 2302.931 to 2298.509 K.
Jobs 125080413–125080444 and the eight-entry `cp-only-jobs.json` registry
identify these runs; `snapshot-cp-only-0131` contains their collected outputs.
The narrower heat-capacity-only interpretation worsens agreement with the
paper's Case 3* curve and does not resolve the slower-but-hotter Case 3 result.

The subsequent [chemistry and alpha controls](liang-chemistry-alpha-controls-20261021.md)
also completed. Activity-based chemistry raises hydrogen Case 3 speed by
approximately 2.2%, worsening agreement. A signed Soave factor lowers the
consistent Case 3 speed by approximately 0.5%, which is insufficient.
Both controls preserve exact ideal-case parity. Their observed build identities
and result hashes are retained separately from the baseline.

The [Takahashi reduction audit](liang-takahashi-reduction-audit-20261021.md)
retains source-supported averaging, historical hydrogen critical-constant
diagnostics, chart interpolation bounds and density weighting. None closes
the cold diffusion discrepancy. Newton's modified constants are not established
as a required input to the final Takahashi chart; they remain a diagnostic.

## Figure 8(a) methane controls

The [native and manual Soret controls](liang-soret-results-20261021.md)
are labelled sensitivities. Native Soret yields passing discrete Case 1/4/5
paper-point screens at phi=1.10, 1.30, 1.35 and 1.40. It lowers Cases 4/5
almost equally, so their separation remains much smaller than the paper's.
The manual formula moves rich Cases 1/4 outside their screen while improving
Case 5. Neither result identifies Liang's thermal-diffusion setting.

The [matched energy controls](liang-methane-energy-results-20261021.json)
at phi=1.40 improve the energy balance. Case 4/5 speeds decrease from
5.807094/5.762399 to 5.771139/5.727276 cm/s.
Their separation is 0.043863 cm/s versus 0.152981 cm/s in the paper.
Case 5 remains 1.498% high and outside the unchanged allowance.
The reconstructed upwind energy-flux spans fall from about 22.4 kW/m²
to 0.6 kW/m²; these are frozen-profile diagnostics, not native residuals.

Previously completed smooth-alpha partial/pure-species energy controls were
also recovered and checked. Their Case 5 speeds, 5.727907/5.725730 cm/s,
still fail the existing screen. The
[legacy record](liang-methane-legacy-energy-20261021.json) explicitly retains
its historical build-association limitation. No duplicate rerun was needed.

The [tolerance controls](liang-methane-tolerance-controls-20261021.md)
separate output precision from nonlinear convergence. The
[conservative species controls](liang-methane-conservation-controls-20261021.md)
add native balance exports; they change no model parameter.
These diagnostics do not replace the 65-point baseline or the frozen CFD
capture. New OpenFOAM runs remain conditional on the unresolved scientific
comparisons.

## Figure 8(b) mechanism controls

At phi 1.10, 100 atm, 298 K:

| Input | Job | Speed, cm/s | Paper reading, cm/s |
| --- | --- | ---: | ---: |
| GRI, generic-driver parity | 125075288 | 7.461914 | 7.4587 +/- 0.0378 |
| Full USC II, first duplicate records | 125077761 | 4.275202 | 3.7160 +/- 0.0378 |
| Full USC II, last duplicate records | 125077764 | 4.275301 | Same reference |
| Full HP 2017, qualified 100-atm representation | 125077801 | 3.971707 | 2.9220 +/- 0.0473 |

USC duplicate-record selection changes this pilot by about 0.0001 cm/s.
The completed USC and HP coarse-guess pilots used 1789 and 2158 final points,
respectively. Their last speed changes are approximately 0.124% and 0.151%.
They are not the unknown Liang methane subsets.

Build 125079371, source `2ff36b1949c498ee3d9ca190933d1c7f458b357e`, passed
1200 author-pair transport checks with maximum relative error `4.8e-15`.
Its binary SHA256 is
`b00cefc331484ce26932d2f7d676cb87c2434d30b64c424e53a87228abea58aa`.
The sweep at phi 0.9, 1.0, 1.2, 1.3 and 1.4 uses jobs 125079670–125079758;
job 125079771 isolates the USC author pair table at phi 1.1. The durable
individual job registry is `state/liang-hydrogen-20261020/kinetics-wave-jobs.json`.
One compute thread is used per flame; five allocated CPUs secure 16 GiB under
the site's memory-per-CPU rule. Failed earlier memory/guess pilots remain
separate records.
The author-pair pilot completed at 4.286499 cm/s, an increase of 0.011297 cm/s
over the ordinary-transport full USC result. This cannot explain the paper's
lower speed. The dissertation independently confirms the USC and HP readings;
see [the mechanism implementation audit](liang-figure8b-implementation-audit-20261021.md).

All six USC and six HP sweep conditions completed. The current Figure 8(b)
comparison contains 28 computed points, including the earlier GRI sweep.
Separate C0–C2 structural controls give 4.322247 cm/s for USC and 3.953245
cm/s for HP at phi 1.10. Neither closes the discrepancy. These are explicitly
constructed subsets, not identified author inputs.

The exact publisher HP supplement matches the retained kinetics,
thermochemistry and transport inputs. The source-supported prompt-off control
changes speed from 3.971810 to 3.964975 cm/s with a matched steady guess.
That 0.172% change cannot explain the paper's 2.9220 cm/s value.
The versioned fixed-pressure converter reproduces the historical input
byte for byte and independently verifies its rates over 298–3500 K.
See the [control record](liang-chemistry-alpha-controls-20261021.md).

The [Hashemi audit](liang-hashemi-rate-audit-20261021.md) confirms that reaction
567 has no missing positive duplicate. Its published aggregate rate is negative
at 100 atm between 488.25 and 580.13 K. The current publisher archive is
unchanged. No rate clipping, reaction deletion or parameter fit was accepted.

All raw PDFs, profiles, downloads and rendered images remain in project state
or output directories. The source checkout retains scripts, identities and
reviewable scientific findings. No new CFD calculation has consumed these
unqualified diagnostics.
