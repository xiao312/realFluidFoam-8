# Liang conductivity source audit, 21 October 2026

**The full dissertation was recovered. It does not give the missing rich-H2
mixing rule, but it materially changes how Figure 6 should be interpreted.**
Its corresponding plot labels conductivity as real/ideal and diffusion as
density-weighted. The journal plot reverses the conductivity label and instead
uses pressure weighting. The plotted conductivity values also differ.
Consequently, these are distinct source versions; an unchanged curve with a
simple typesetting error has not been established.

This audit extends the [earlier mapping search](liang-rich-hydrogen-mapping-20261021.md)
and [conductivity implementation audit](liang-hydrogen-conductivity-audit-20261020.md).
It used existing local flame profiles only. No model, mechanism, solver, job or
baseline was changed. Repository HEAD during the work was
`1dfca4b248f5eb4e7cb58beb4488f76ae79e81b7`.

## Recovered primary source

Wenkai Liang, *Theoretical Studies on Combustion Chemistry and Waves*,
Princeton University, June 2018, advisor Chung K. Law. The original front matter
identifies ProQuest number **10814581** and departmental thesis **T#3359**.
The [RISS catalog's normal full-text action](https://www.riss.kr/pdu/ddodLink.do?id=T14998128)
led to the publicly served
[dissertation PDF](http://imgsvr.riss4u.net/ddod8/201812/14998/128/14998128.pdf).
No credentials or institutional session were supplied.

The downloaded original has 212 PDF pages and 5,039,866 bytes:

```text
SHA-256 806906f751d2b257dae7a9e66111158c5aaa8ec227fdd8f5ea909a57a52c3a85
```

Chapter 8 occupies printed pages 163–178, PDF pages 173–188. Section 8.2 repeats
the modified mixing/conformal-mapping statement without adding equations,
coefficients or an implementation reference. The PDF has no embedded
attachments. Searches of the complete extracted text and inspection of the
chapter did not identify an additional conductivity appendix.

The methane submodels remain named without reaction/species counts or subset
files. This chapter adds no explicit inlet temperature, finite-domain boundary
conditions or grid settings. Its stated domain is doubly infinite. The 298 K
initial condition on printed page 181 belongs to the next chapter's separate
spherical ignition study and must not be transferred to Chapter 8 by citation.

## Figure 6 has an author-source disagreement

The glyphs and surrounding paragraphs were checked visually in both original
PDFs, rather than inferred from OCR:

| Quantity | Dissertation Figure 8-5, p. 171 | Journal Figure 6, p. 1737 |
| --- | --- | --- |
| Black label | \(\lambda_{\mathrm{real}}/\lambda_{\mathrm{ideal}}\) | \(\lambda_{\mathrm{ideal}}/\lambda_{\mathrm{real}}\) |
| Red label | \((\rho D)_{\mathrm{real}}/(\rho D)_{\mathrm{ideal}}\) | \((PD)_{\mathrm{real}}/(PD)_{\mathrm{ideal}}\) |
| Supporting prose | Page 172 names density weighting and increased conductivity at low temperature | Page 1737 names pressure weighting; the conductivity-increase statement is absent |

Sources: [dissertation, pp. 171–172](http://imgsvr.riss4u.net/ddod8/201812/14998/128/14998128.pdf)
and [published article](https://doi.org/10.1016/j.proci.2018.06.070).
The journal's capital \(P\) is not a mistaken reading of Greek \(\rho\).
Neither source identifies which mixture/species diffusivity the red curve uses.

The thesis plot remains vector graphics. Its visible black curve was extracted
from PDF drawing paths, calibrating the axes against all visible major ticks.
The journal values below come from the existing original-image extraction,
including its line-width/calibration allowance:

| T, K | Thesis black curve, real/ideal | Journal black curve, ideal/real | Journal reading interval |
| --- | ---: | ---: | --- |
| 1200 | 1.057196 | 1.070376 | 1.067612–1.073134 |
| 1500 | 1.024737 | 1.034209 | 1.032687–1.035522 |
| 1990 | 1.004761 | 1.008657 | 1.007612–1.009851 |

Across nine common readings, the RMS ordinate difference is 0.010295 and the
maximum difference is 0.013943. Thus the conductivity curves changed as well
as their definitions. These comparisons measure the plotted paths, not the
authors' underlying numerical tables. The thesis tick fit has maximum
temperature residual 0.073 K and ratio residual \(3.8\times10^{-6}\);
finite source stroke width is larger than those calibration residuals.

In particular, the available journal reading near 2000 K is still above one.
Its 1990 K interval does not support a crossing below one there. Clipped
low-temperature portions were not extrapolated.

The dissertation is direct author evidence that an earlier implementation
or presentation associated the upper black curve with enhanced conductivity.
It is not enough to decide whether the later journal changed physics, changed
normalization or introduced an error. Preserve the published label in the
published-figure comparison. A separate thesis interpretation may be shown
with its own source and numerical trace.

## Other figures mostly retain their original curves

To check whether a wholesale source revision explains our other discrepancies,
the thesis vectors were calibrated independently and compared with the existing
journal readings:

| Journal figure | Thesis counterpart | Comparison | Maximum absolute difference |
| --- | --- | --- | ---: |
| 1 | None in Chapter 8 | Oxygen/NIST validation panel was not found in this chapter | Not applicable |
| 2 | 8-1, p. 168 | Three common phi values, both fuels, both critical quantities | 0.0058 K; 0.0018 atm |
| 3 | 8-2, p. 169 | All six speed series, including both marker series | 0.0055 cm/s |
| 5 | 8-4, p. 170 | Four temperature series, including Case 1 markers | 0.039 K |
| 6 | 8-5, p. 171 | Nine black-curve readings | 0.01394 in ratio |

The first three comparisons are consistent with reuse of the same plotted
data to the precision of the PDF paths. This is not a claim of bitwise identity
of unpublished arrays. Curve samples are correlated and are not independent
experiments. Interpolation across short dash gaps is used only to test
source-to-source curve continuity, not to fill missing physical data.

The Figure 2 critical-pressure inconsistency therefore already occurs in the
dissertation. It is not resolved by adopting its figure. Likewise, Figure 5's
Case 3/Case 3* temperature ordering remains unchanged. The thesis does give
the narrower description that Case 3* updates heat capacity, which is useful
for designing a separate energy-form control; it does not authorize swapping
the displayed curves. See the separate energy audit for that implementation
question.

## Different flame composition does not close the journal gap

The article does not specify whether ideal/real conductivities are evaluated
at identical composition or on separate flame solutions. A diagnostic used
the saved stoichiometric, 100-atm, 298-K inlet profiles:

| Case | Job |
| --- | --- |
| 1 | 125068739 |
| 3 | 125069048 |
| 4 | 125069058 |
| 5 | 125069072 |

These are the existing Burke2012-N2-pressure, dense-increment diagnostic
results, with Soret off. Each conductivity was interpolated on its own strictly
increasing temperature branch, retaining its own composition. No property
model was reevaluated and no flame was solved.

| Ratio of separately solved profiles | 1200 K | 1500 K | 1990 K |
| --- | ---: | ---: | ---: |
| Case 1 / Case 4 | 0.978328 | 0.984694 | 0.989958 |
| Case 1 / Case 5 | 0.982553 | 0.987602 | 0.991206 |
| Case 3 / Case 4 | 0.976788 | 0.983150 | 0.988598 |
| Case 3 / Case 5 | 0.981007 | 0.986053 | 0.989844 |

All four stay below one over the nine journal comparison temperatures.
Their RMS errors against the literal journal curve are 0.0623–0.0670;
none falls within its vertical reading interval. The largest local
temperature spacing is below 2.7 K, and no endpoint extrapolation was used.
This rejects this particular composition-path explanation for our existing
profiles. It does not prove that every alternative conductivity implementation
would behave similarly.

Taking the inverse of our same-state conductivity ratio gives approximately
1.02215 at 1200 K and 1.01112 at 1990 K. That agrees with the thesis's direction
but still differs from its 1.05720 and 1.00476. A label reinterpretation does
not make the current model reproduce either source.

## Remaining cited-source route

The additional Pons reference
[Congiunti, Bruno and Giacomazzi, AIAA 2003-478](https://doi.org/10.2514/6.2003-478)
was inspected through the
[author-uploaded full text](https://www.researchgate.net/publication/236270198_Supercritical_Combustion_Properties).
Its equations 68–84 reproduce standard EH internal/translational terms,
methane mapping and mixture rules. Its validation section covers CH4, O2,
CO, CO2 and H2O, rather than a rich-H2 modification. No additional
hydrogen-specific replacement was identified there. The author-uploaded text
was readable through the search service; direct file retrieval returned 403,
so no verified local original PDF from that source was obtained.

References 5–8/10 and the original EH/NBS programs remain covered by the
previous conductivity audit. The full dissertation is a stronger new source,
but it does not supply the missing rule. No new source-supported alternate
rich-H2 implementation is ready to promote into the baseline.

The remaining specific retrieval is Weiyu Li's April 2019 MSE thesis,
*Flame Dynamics in Supercritical Conditions*. Its official Princeton
[degree record](https://mae.princeton.edu/sites/g/files/toruqf7696/files/2019%20-%20Class%20Day%20-%20Introduction%20of%20Graduates.pdf)
and earlier exam abstract are available, but a full thesis was not located.
This is a bounded search result, not proof that an implementation cannot be
obtained. No author contact was made.

## Evidence and reproduction

All generated evidence and copyrighted source downloads remain outside Git:

```text
state/liang-hydrogen-20261020/conductivity-source-audit/
  liang-dissertation-2018.pdf
  liang-dissertation-2018.txt
  riss-*-receipt.json
  compare-thesis-figures.py
  thesis-vector-readings.csv
  thesis-publication-comparison.csv
  thesis-figure-comparison.json
  thesis-publication-source-panels.pdf
  thesis-publication-figure6-panel.png
  compare-existing-profiles.py
  profile-composition-check.csv
  profile-composition-check.json
```

The four-page comparison PDF places original thesis and journal plots side by
side with labels retained. Its Figure 6 panel and the original full-page
renders were visually inspected. The two Python scripts run with the existing
analysis virtual environment, read only the recorded local inputs, and write
only into this evidence directory. JSON records retain source/profile hashes,
axis calibration and original PDF drawing identifiers.

The practical conclusion is to separate three questions: fidelity to the
published plot, fidelity to the dissertation plot, and independently validated
conductivity physics. The recovered primary source makes the uncertainty
more specific; it does not justify fitting conductivity to either curve.
