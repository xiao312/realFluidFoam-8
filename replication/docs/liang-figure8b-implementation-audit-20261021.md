# Liang Figure 8(b): mechanism implementation audit

Status: tested, not accepted. Recorded 21 October 2026, Asia/Shanghai.

The downloaded USC-II and HP-May2017 inputs survive conversion without an
identified coefficient, unit, falloff, third-body, duplicate, or reverse-rate
error. Their completed ideal flames remain faster than Liang's curves. The
author's dissertation independently confirms the USC and HP figure readings.
The exact methane sub-model files used by Liang remain unavailable; current
author-page release labels do not prove that their present bytes equal the
2017–2018 inputs.

This audit uses the completed full-mechanism profiles at equivalence ratio 1.1,
100 atm and inlet temperature 298 K. It does not alter a mechanism, solve a new
flame, or select an input by agreement with the paper.

## Independent conversion check

An independent reader parses the original CHEMKIN reaction blocks and NASA7
records, compares every literal coefficient with YAML, then evaluates forward
and reverse rates of progress at fourteen prescribed states. Temperatures are
298, 600, 1000.1, 1500, 2200, 3000 and 3500 K; each uses both a uniform species
mixture and a product mixture containing trace species. All states use 100 atm.
The calculation uses the authored mol/cm3 units internally, then converts
rates of progress to kmol/m3/s. Its reverse equilibrium constants use the
authored NASA7 coefficients and their 1-atm standard state.

| Input | Species | Raw reactions | LOW / Troe | PLOG reactions | Duplicate records | Literal mismatches |
|---|---:|---:|---:|---:|---:|---:|
| USC first thermo records | 111 | 784 | 62 / 60 | 0 | 18 | 0 |
| USC last thermo records | 111 | 784 | 62 / 60 | 0 | 18 | 0 |
| HP May2017 author records | 92 | 615 | 35 / 31 | 88 | 44 | 0 |

Checked fields are stoichiometry, reversibility, Arrhenius A/b/Ea, LOW,
Troe parameters, third-body efficiencies, duplicate flags, PLOG pressure and
rate entries, NASA7 limits and coefficients. Neither mechanism supplies explicit
REV records. The independent rate evaluation includes third-body concentrations,
Troe falloff and PLOG summation/interpolation using the standard definitions in
[Cantera's rate documentation](https://cantera.org/3.2/reference/kinetics/rate-constants.html).

| Rate comparison with Cantera 3.2 | Maximum forward relative difference | Maximum reverse relative difference |
|---|---:|---:|
| USC first/last | 6.875e-14 | 8.336e-14 |
| HP raw input versus fixed-100-atm representation | 4.675e-9 | 4.675e-9 |

The largest HP relative difference is numerical cancellation in reaction 104,
`CH2(S)+M <=> CH2+M`, for which the author assigns zero efficiencies to the
dominant bulk gases. At 298 K in the product/trace mixture, the forward values
are 0.001625540687767257 and 0.0016255406801683001 kmol/m3/s: an absolute difference
of 7.6e-12. This does not account for the flame-speed discrepancy.

HP's previously documented fixed-100-atm input preserves signed Arrhenius
components and their aggregate at the authored pressure endpoint; it contains
616 YAML reactions. This audit compares that representation with the raw
100-atm rate expressions, including reverse rates. It does not qualify the
representation at other pressures or prove that the underlying rate model
matches experiment. See the [earlier source record](liang-figure8b-reading-20261021.md).

The USC first/last duplicate thermo choices remain separate. No ambiguity was
resolved by selecting whichever output best agrees with Liang.

## Thermochemistry is intentionally mechanism-specific

The author files do not all use GRI thermochemistry. Selected formation-enthalpy
differences at 298.15 K, author minus the Cantera GRI input, are:

| Species | USC minus GRI, kJ/mol | HP minus GRI, kJ/mol |
|---|---:|---:|
| OH | -1.80440 | -2.04692 |
| CH3 | 0 | -0.19933 |
| HCO | 0 | +0.30000 |
| CH2O | 0 | -0.58400 |
| HO2 | 0 | -0.25600 |

These values follow directly from the downloaded author NASA7 coefficients,
which are preserved in YAML. They affect reverse rates as well as heat release.
They are an input difference, not a conversion defect. Substituting GRI thermo
would create a new model and would not reconstruct an unspecified author input.
The frozen-state audit records Cp, h and s for thirteen named species at several
temperatures, rather than inferring an effect on flame speed from this table.

## Dissertation figure check

The [June 2018 dissertation](http://imgsvr.riss4u.net/ddod8/201812/14998/128/14998128.pdf),
Figure 8-7(b), printed page 173 / PDF page 183, contains separate vector strokes
for all eight curves. They were extracted from the original PDF, calibrated
using its four x ticks and seven y ticks, and overlaid on the original panel for
visual verification. Native line segments are retained. Sample bounds include
line thickness, tick-calibration residuals, and additional uncertainty where a
sample lies inside a dash gap. These are graphical reading bounds, not
experimental error bars.

| Curve at phi 1.1 | Dissertation, cm/s | Journal raster reading, cm/s |
|---|---:|---:|
| GRI Case 1 | 7.4630 ± 0.0265 | 7.4587 ± 0.0378 |
| GRI Case 3 | 7.1306 ± 0.0269 | 7.0712 ± 0.0425 |
| USC Case 1 | 3.7158 ± 0.0305 | 3.7160 ± 0.0378 |
| USC Case 3 | 3.5426 ± 0.0330 | Occluded; not read |
| HP Case 1 | 2.9237 ± 0.0269 | 2.9220 ± 0.0473 |
| HP Case 3 | 2.7506 ± 0.0336 | 2.7519 ± 0.0473 |
| Hashemi Case 1 | 3.5529 ± 0.0277 | 3.5505 ± 0.0331 |
| Hashemi Case 3 | 3.3391 ± 0.0396 | 3.3379 ± 0.0378 |

USC, HP and Hashemi readings differ by no more than 0.0147 cm/s across the
available comparison samples. GRI Case 1 differs by at most 0.0195 cm/s.
GRI Case 3 differs by up to 0.0694 cm/s; at phi 1.15 its reading bounds narrowly
fail to overlap, by 0.00103 cm/s. Overall 91 of 92 paired bounds overlap.
Do not silently replace the journal data with the thesis data. The ideal USC
and HP discrepancies remain much larger than either set of reading bounds:
4.27520 and 3.97171 cm/s from the full mechanisms, respectively.

The journal source is
[Liang et al., DOI 10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070).
Its numerical image-reading method and omitted points are recorded in the
[Figure 8(b) source note](liang-figure8b-reading-20261021.md).

## Activity of species containing more than two carbon atoms

The complete saved profiles from jobs 125077761 (USC) and 125077801 (HP) were
evaluated with their exact input mechanisms. The source revision is
`a21f8b1532e5bc4b3248fcec96dd876ccd234e0b`. No new flame was solved.

For a channel r, define

`D_CH4 = -integral(omega_CH4 dx)`,
`R_net,r = integral(q_net,r dx)/D_CH4`, and
`R_abs,r = integral(abs(q_net,r) dx)/D_CH4`.

Rates use kmol/m3/s and integrals kmol/m2/s. Identical-stoichiometry duplicate
entries are summed before taking the absolute value, so signed fitted components
are not counted as separate physical cycles. A channel is selected when a
reactant or product contains more than two carbon atoms. Efficiencies alone do
not make a channel selected.

| Full flame | USC | HP |
|---|---:|---:|
| Saved points | 1789 | 2158 |
| Maximum sum of C>2 mass fractions | 2.58739e-4 | 5.24510e-5 |
| Temperature at that maximum, K | 1843.12 | 1732.42 |
| C>2 species count | 72 | 38 |
| Reactions involving C>2 species | 534 | 244 |
| Net CH4 consumption, kmol/m2/s | 0.0180829 | 0.0167976 |
| Sum of selected R_abs | 0.087593 | 0.027041 |

The dominant selected channel in both mechanisms is
`C2H2 + CH3 <=> H + pC3H4`.
Its signed/absolute ratios are 0.006430/0.008276 for USC and
0.004632/0.004632 for HP. Other active selected channels consume OH and the
C3 intermediates. Full channel tables are retained.

These are cycle-inclusive reaction-progress ratios. They are not carbon
fractions, carbon balances, flame-speed sensitivities, or an upper bound on the
effect of truncation. A small species mass fraction does not imply negligible
reaction flux. Repeating quadrature with every second saved point changes
integrated CH4 consumption by +0.00252% for USC and -0.000650% for HP;
that is an integration check, not a flame-grid convergence check.

A C0–C2 graph truncation can test the effect of removing these pathways if it
preserves all retained coefficients and is labelled as a new diagnostic input.
It cannot establish Liang's unpublished methane sub-model. A C1-only ablation
would additionally remove methyl recombination to ethane, a qualitatively
different test. Neither should be selected by closeness to a paper curve.

The audit also exposed a CSV formatting defect: two USC species names contain
commas, which the saved header did not quote. Numeric rows are intact. This
analysis validates the complete literal header against the mechanism's species
order and reads numeric columns positionally. Reconstructed density agrees with
the saved density within 6.8e-11 relative. The defect affects generic CSV
interpretation, not the stored flame solution.

## Historical provenance limits

The [USC author input](http://ignis.usc.edu/Mechanisms/USC-Mech%20II/USC_Mech_ver_II.txt)
declares a May 2007 release and names several rate updates from that month.
The cached [Princeton HP page](https://engine.princeton.edu/mechanisms/hp-mech/)
labels its release May 18, 2017. Its mechanism header cites both the 2015 HP
paper and Zhao et al. (2017). The
[Princeton publication record](https://collaborate.princeton.edu/en/publications/effect-of-prompt-dissociation-of-formyl-radical-on-135-trioxane-a/)
identifies the latter's formaldehyde/formyl prompt-dissociation study.

The current author mechanism directory separately lists a DME release from
June 22, 2018 and 2022 releases. Those are distinct links, not evidence that the
2017 row's present contents are unchanged. Neither cached page provides a
verified content-modification timestamp tied to the downloaded mechanism bytes.
Local download timestamps are not release dates.

A 2016–2019 Wayback CDX request for the author HP URLs was inaccessible; the
current author page also returned 403 on recheck. No archive-access workaround
was attempted. No dated 2017–2018 mechanism snapshot was recovered. Thus the
present input hashes are reproducible, but their historical identity with
Liang's inputs is unproven. An author-supplied input bundle or accessible dated
author archive remains stronger evidence than choosing another public mechanism
because its speed happens to agree.

## Reproducible evidence

All large or downloaded files remain outside Git under
`state/liang-hydrogen-20261020/figure8b-implementation-audit/`:

- `raw_chemkin.py`, `verify.py`, and `results-5/audit.json`: literal and independent
  frozen-rate comparisons, source hashes, and thermo differences.
- `channel_flux.py` and `channel-results-2/`: profile identities, all selected
  channel integrals, normalization definitions and quadrature check.
- `thesis_figure8b.py` and `thesis-results/`: vector path IDs, calibration,
  original PDF hash, journal comparison CSV and verified sample overlay.

Each script has a no-write plan and requires a new output directory for apply.
Python environments are the local Cantera 3.2 equilibrium environment and the
PyMuPDF analysis environment. Initial parser attempts and the CSV-header failure
remain recorded; successful result directories are named explicitly above.
No remote work, mechanism changes, source commits or acceptance decision were
performed by this audit.
