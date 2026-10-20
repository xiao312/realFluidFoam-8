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
| 3 | Author-polynomial Cases 1 and 2 pass all 14 readable speed comparisons; maximum error is 0.53% | Cases 3–5 fail all 13 readable points per case |
| 4 | Full Cases 1/2 coverage from phi 0.6 to 3.0; fresh density agrees with the paper | Keep density and burning-flux comparisons distinct from speed acceptance |
| 5 | Full overlapping phi range 0.85–1.35; consistent energy forms give close results | Paper Case 3 is slower but hotter than its Case 3*; implementation identity remains unresolved |
| 6 | Named conductivity and diffusivity ratios are evaluated at saved flame states | Journal and dissertation use different definitions and different curve values; neither current interpretation closes the gap |
| 7 | Corrected physical width and finite-window temperature agree within image-reading bounds | HO2/H2O2 peaks remain 5.23%/6.47% high; the paper does not identify the displayed case |
| 8(a) | Earlier GRI Cases 1–4 pass the declared digitized-paper screen | Case 5 remains outside it at three rich conditions |
| 8(b) | Generic ideal GRI driver reproduces the earlier result within 0.003%; first full USC/HP pilots completed | Full author releases do not reproduce the unprovided methane subsets; Hashemi input has a negative rate |

Figure 3 author-polynomial speed errors are +2.20–8.47% for Case 3,
+6.65–10.87% for Case 4 and +7.65–12.13% for Case 5. The partial-temperature
control follows the paper's Case 3* curve, but is not accepted as the author's
implementation. The speed screen is the existing absolute allowance
`max(0.05 cm/s, 1% of reference) + image-reading allowance`.

## Corrections and new primary evidence

The earlier Figure 7 overlay used half the printed horizontal tick interval.
It therefore doubled the apparent calculated width. That display error and the
broader-flame claim are withdrawn. The corrected 500–2000 K width is
4.864 micrometres for Case 5 versus 4.726 [4.422, 5.025] in the image.
At the same finite paper right edge, Case 5 differs by only 1.91 K; the
full-domain burned endpoint is a different comparison.

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

The [Takahashi reduction audit](liang-takahashi-reduction-audit-20261021.md)
retains source-supported averaging, historical hydrogen critical-constant
diagnostics, chart interpolation bounds and density weighting. None closes
the cold diffusion discrepancy. Newton's modified constants are not established
as a required input to the final Takahashi chart; they remain a diagnostic.

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

The [Hashemi audit](liang-hashemi-rate-audit-20261021.md) confirms that reaction
567 has no missing positive duplicate. Its published aggregate rate is negative
at 100 atm between 488.25 and 580.13 K. The current publisher archive is
unchanged. No rate clipping, reaction deletion or parameter fit was accepted.

All raw PDFs, profiles, downloads and rendered images remain in project state
or output directories. The source checkout retains scripts, identities and
reviewable scientific findings. No new CFD calculation has consumed these
unqualified diagnostics.
