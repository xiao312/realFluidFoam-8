# Liang Case 5: diffusion reference audit

Reviewed 20 October 2026. This record supports the existing
[Case 5 comparison](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnAQDmyzTPvtCilc9u3tV8jd).
No solver, transport coefficient, case input, or running job changed.

## Finding

The next useful test is diffusion at prescribed temperature, pressure and
composition, followed by the Case 4-to-5 flame-speed change. A satisfactory
Case 4 flame speed does not independently validate every underlying property.
The response to diffusion also depends on the flame structure produced by those
properties.

At phi = 1.40 and 100 atm, the existing finer-grid results are:

| Source | Case 4, cm/s | Case 5, cm/s | Reduction, cm/s |
|---|---:|---:|---:|
| Digitized Liang Figure 8(a) | 5.795719 | 5.642738 | 0.152981 |
| Current Cantera, extra refinement | 5.799594 | 5.754848 | 0.044747 |

The calculated reduction is about 29% of the paper reduction. These values come
from the [existing result record](liang-diffusion-and-inversion-20261020.md).
They identify a diffusion-response mismatch, not a measured error in a particular
binary coefficient. The nonideal-driving experiment did not close this gap.

Liang Figure 1 compares oxygen density and thermal conductivity at 100 atm.
It contains no diffusion panel. The broader validation statement therefore needs
to be followed through the cited sources.
[Liang et al., DOI 10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070).

## What Liang's references establish

| Liang reference | Source and inspected location | Relevance and limit |
|---|---|---|
| 19 | [Takahashi, generalized high-pressure diffusion chart](https://doi.org/10.1252/jcej.7.417), Tables 1-2, Figures 1-2, pp. 417-420 | Direct source for the pressure correction. Table 1 identifies its experimental systems. |
| 5 | [Pons et al. (2009), Mass transfer and combustion in transcritical non-premixed counterflows](https://doi.org/10.1080/13647830802368821), p. 63 and Appendix B, p. 80 | Uses CHEMKIN/TRANSPORT dilute binary coefficients multiplied by Takahashi. Appendix B explicitly omits binary-diffusion comparisons because experimental/reference data were lacking. Figures 17-19 validate other properties. |
| 6 | [Huo, Wang and Yang (2014), oxygen/hydrogen counterflow flames](https://doi.org/10.1016/j.combustflame.2014.06.005), Section 2.2 and Figure 5 | Uses Takahashi. Figure 5 checks oxygen density/compressibility, Cp, conductivity and viscosity at 100 atm, not diffusion. Refers onward to Yang (2000) and Meng et al. (2005) for property methods. |
| 7 | [Wang, Huo and Yang (2015), oxygen/n-alkane counterflow flames](https://doi.org/10.1080/00102202.2014.973955), Figures 2-3 | Oxygen and methane property comparisons at 20, 50, 100, 150 and 200 atm; no binary-diffusion panel. Useful later flame benchmark, but its methane mechanism differs from our GRI30. |
| 8 | [Jorda Juanos and Sirignano (2017), Pressure effects on real-gas laminar counterflow](https://doi.org/10.1016/j.combustflame.2017.01.030), Eq. (7), p. 56, and case table | Uses CHEMKIN multicomponent diffusion. Its listed transport correction changes viscosity and conductivity; it does not document a Takahashi binary-diffusion correction. |
| 10 | [Giovangigli, Matuszewski and Dupoirieux (2011), Detailed modeling of planar transcritical H2-O2-N2 flames](https://doi.org/10.1080/13647830.2010.527016), Sections 3.3 and 4.2 | Uses dense-gas kinetic theory, Stefan-Maxwell transport and thermodynamic driving forces. Eq. (48) uses a concentration ratio and collision free-volume factor, not Takahashi. Useful as an independent model; not the same implementation. |

The citation chain supports high-pressure modeling generally. It does not supply
six independent validations of one shared mass-diffusion implementation.
Reference 8's comment about neglected pressure effects accompanies the diffusion
velocity equation. Do not use that wording alone to distinguish pressure-gradient
diffusion from pressure-dependent coefficients.

Takahashi's journal volume is **7**, not the **31** printed in Liang's reference 19.
The scanned issue says 1974; J-STAGE gives publication on 31 January 1975.
Use its DOI to avoid ambiguity.

## Property checks to extract first

Takahashi correlates `F = D*p/(D*p)^0`, not dimensional diffusivity alone.
Thus `D(T,p) = D(T,p0)*(p0/p)*F`. Avoid applying inverse-pressure scaling twice.
Table 1 is chiefly self/tracer diffusion; its bath-gas critical properties matter.
Table 2 gives `B = 2.39031` at `Pr = 3`, already corrected in our adapter.
Its reported mean deviation is 4.1%; that is a diffusion-data statistic, not a
flame-speed tolerance.
[Original paper](https://www.jstage.jst.go.jp/article/jcej1968/7/6/7_6_417/_pdf).

Recommended order:

1. Reproduce Takahashi Figure 2 and Table 2 values without a flame solver.
   Preserve the declared interpolation, valid range and extrapolation policy.
2. Compare the dilute binary baseline with modern measured/evaluated gas data.
   Separate this from pressure correction, critical-data selection and mixing.
3. Reproduce selected high-pressure experimental isotherms listed below.
   Identify whether each value is self, tracer, Fick or Maxwell-Stefan diffusion.
4. At frozen Case 4 states, export `Dij_dilute`, `Fij`, corrected `Dij`, pair
   `Tr/Pr`, and contributions `Xj/Dij` to each mixture coefficient.
   Rank H, H2, O, OH, CH4, O2, N2, H2O, CO and CO2 by actual flux contributions.
5. Change one justified component and repeat Cases 4 and 5 at phi = 1.40.
   Judge both absolute speeds and their difference. Do not fit coefficients to
   the digitized flame curve.

The existing 848 checks establish binary-to-mixture reconstruction and mass
conservation. They do not establish agreement with measured binary diffusivity.
Whole-mixture critical averaging and the added fugacity driving force already
failed to explain the flame gap. Repeat them only if new evidence changes their
inputs or physical interpretation.

## Additional references with usable tests

| Reference | Test opportunity | Qualification needed |
|---|---|---|
| [Dawson, Khoury and Kobayashi (1970)](https://doi.org/10.1002/aic.690160507), cited by Takahashi | Methane self-diffusion measured by pulsed NMR, 150-350 K and 200-5000 psia (about 1.38-34.47 MPa). | Obtain original numerical tables. Distinguish self-diffusion from a finite-composition mixture coefficient. |
| [Takahashi (1972), CTH3 in CH4-CO2](https://doi.org/10.1246/bcsj.45.2074), cited by Takahashi | Methane tracer in methane, CO2, and a bath with methane mole fraction 0.522; 298.15, 323.15 and 348.15 K; 15-250 atm. | Check isotopic tracer treatment and bath composition. Particularly useful for testing the reduced-property mapping. |
| [Harstad and Bellan (2004)](https://doi.org/10.1021/ie0304558), Pons reference 18 | High-pressure binary-diffusion data, reduced-density fits and discussion of data interpretation. | Publisher abstract and Caltech metadata verified; full tables were not obtained. Alternative correlation, not evidence of Liang's exact code. |
| [McGivern et al. (2021), NIST manuscript](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=931779) | Measured dilute CH4-N2, 250-550 K, and CH4-air, 250-350 K. Tables 2 and 4 provide direct regression targets. | Reported D values are normalized to 101.3 kPa; actual measurement pressure was 403.5-679.3 kPa. Tests dilute transport, not 100-atm suppression. |
| [Bogatyrev and Nezovitina (2013), NIST ThermoML](https://trc.nist.gov/ThermoML/10.1007/s10765-013-1539-3.html) | H2-N2, H2-CO and H2-CH4 data, 250-900 K and pressure levels 0.1, 4, 7, 10 and 15 MPa. | Archive uncertainty/scaling fields need original-table verification. Do not use as an accepted fixture yet. |
| [Guevara-Carrion et al. (2019)](https://www.nature.com/articles/s41598-019-44687-1) | Dilute methane in dense CO2, 292.55-332.85 K, 9, 12.5 and 14.7 MPa; Taylor-dispersion measurements. | Distinguishes measured Fick diffusion from simulated Maxwell-Stefan/intradiffusion. Near-critical composition dependence must be retained. |

## What NIST supplies

**Yes, NIST supplies mass-diffusion data**, through publications and the TRC
ThermoML literature archive. The familiar
[WebBook pure-fluid page](https://webbook.nist.gov/chemistry/fluid/) does not
list binary mass diffusivity. REFPROP's
[thermal diffusivity](https://github.com/usnistgov/REFPROP-docs/blob/master/doc/GUI/Menu%20Commands/Options%20Menu/properties.rst)
is `lambda/(rho*Cp)`; it is a different property despite having the same units.

[NIST TN 2279, Burgess (2024)](https://doi.org/10.6028/NIST.TN.2279)
compiles approximately 300 self/binary gas coefficients. It provides reference
values at 298.15 K and 101.325 kPa, plus temperature correlations where available.
Individual entries include experiments and first-principles calculations.
For example, its CH4-N2 experimental-source fit lists 0.234 cm2/s near 298 K.
This is a dilute-gas reference, not high-pressure validation.

An immediate measured target is McGivern Table 2:
CH4-N2 at 300 K, normalized 101.3 kPa,
`D = (2.37 +/- 0.03)*10^-5 m2/s` at 95% confidence.
Table 4 gives CH4-air `D = (2.37 +/- 0.05)*10^-5 m2/s`.
Do not confuse these with finite-composition methane/air flame coefficients.

ThermoML's high-pressure hydrogen record contains suspect fields. One
300 K, 0.1 MPa H2-N2 point has `D = 8e-5 m2/s` but an uncertainty entry of
`1600`. High-pressure coefficient scaling and the stated hydrogen mass fraction
of 0.5 also need source-table checks. No guessed correction was applied.

No verified dataset for the entire reacting methane/air mixture at 100 atm
and 300-2200 K was established. Independent binary checks can constrain the
model without uniquely reconstructing Liang's unpublished transport inputs.

## Evidence and next decision

Relevant methods, validation sections and references were checked in all six
primary papers. Downloaded papers, extracted text, page renders and the NIST research note are under
the operator workspace `state/diffusion-literature-20261020/`.
The existing Giovangigli PDF remains in `state/cantera-liang-20261019/`.
Downloaded publications are excluded from Git.
The [source manifest](liang-diffusion-sources-20261020.json) preserves the six
downloaded PDF hashes and their public locations.

This audit recommends property benchmarks before another Case 5 model variant.
It does not declare a faulty diffusivity value or accept the current model.
