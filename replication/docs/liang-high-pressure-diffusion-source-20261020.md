# High-pressure diffusion reference qualification

Reviewed 20 October 2026 for the [diffusion investigation](https://github.com/xiao312/realFluidFoam-8/issues/4).

The next executable benchmark is methane **self-diffusion** from Dawson's
original dissertation. It permits a conditional pressure-correction comparison
without a mixture composition or thermodynamic-factor conversion. It does not
validate the binary diffusion of radicals in methane/air or establish Liang's
implementation.

## Dawson: usable data with explicit limits

[Self-diffusion in methane](https://hdl.handle.net/1911/14341), Charles Rapier
Dawson Jr., has a September 1966 title page; Rice catalogs it as 1967.
Table I, printed p. 104 (PDF page 113), supplies 35 warm-gas measurements.
The [fixture](../validation/diffusion/dawson-reference.json) preserves temperature,
pressure, density, diffusion coefficient and the printed density-diffusivity
product. These are direct visual transcriptions, not plot digitization.
[Original PDF](https://repository.rice.edu/server/api/core/bitstreams/136a4ce1-fe6e-42d6-b141-b8a7a05c6640/content).

| Selected original row | T, K | p, psi | Density, g/cm3 | Self-D, cm2/s |
|---|---:|---:|---:|---:|
| Near room temperature, lower pressure | 296.96 | 771 | 0.03793 | 0.003838 |
| Near the flame study pressure | 296.86 | 1386 | 0.07281 | 0.002053 |
| Same approximate isotherm | 296.84 | 1846 | 0.1003 | 0.0014747 |
| Higher pressure | 296.81 | 3020 | 0.16405 | 0.0008806 |
| Warmer isotherm | 322.52 | 1489 | 0.06876 | 0.002282 |
| Warmest isotherm | 353.85 | 1680 | 0.06803 | 0.002386 |

The measurement is pulsed-NMR molecular self-diffusion in nominally pure
methane. The uncertainty discussion gives a shared 3% gradient systematic
component and about 1.5% point scatter, without coverage factors. Low-pressure
noise adds unquantified error. Do not present their sum as a 95% interval.
The fixture excludes the near-critical-temperature rows whose density
uncertainty is separately estimated as 10%.
[Dawson, printed pp. 61 and 98-100](https://repository.rice.edu/server/api/core/bitstreams/136a4ce1-fe6e-42d6-b141-b8a7a05c6640/content).

Table I labels pressure only as PSI. The
[1970 companion article](https://doi.org/10.1002/aic.690160507) explicitly describes
absolute pressure, supporting but not proving that basis for every thesis row.
Use nominal absolute pressure and also calculate a +101325 Pa sensitivity.
Report the assumption and whether it changes conclusions. The journal's full
numerical table was not obtained; the thesis must remain a distinct source.
Its dilute-fit Lennard-Jones values also differ from those in the journal
abstract, so they must not be silently interchanged.

Comparison requirements:

- Convert psi by 6894.757293168 Pa/psi and cm2/s by 1e-4 m2/s.
- Calculate the dilute same-species binary coefficient, then its Takahashi
  correction using the tested implementation's CH4 critical properties.
  A mixture-averaged pure-fluid coefficient is not the requested observable.
- Report the 28 warm rows within approximately `Pr <= 5` separately from the
  seven higher-pressure rows; classify with the actual critical table.
  All 35 selected temperatures exceed methane's critical temperature.
- No thermodynamic factor is required for this self-diffusion comparison.
  This is a mapping to the self-diffusion data underlying corresponding-states
  correlations, not an assertion that self and mutual diffusion are equal in
  arbitrary mixtures.
- Report residuals and pressure-basis sensitivity. A successful comparison
  cannot by itself close the binary-mixture validation gate or the flame gap.

As a transcription check, recomputed `rho*D` agrees with the printed product
to within 0.0592%, consistent with the table's rounding.

## Why the 2019 methane/CO2 measurements are not the primary gate

[Guevara-Carrion et al.](https://doi.org/10.1038/s41598-019-44687-1), Table 1,
provides 22 measured **Fick** coefficients and standard deviations at
9.0, 12.5 and 14.7 MPa. The injection stock has methane mole fraction 0.2052;
it is not the composition at measurement. The text estimates 0.0156 at about
313 K and 9 MPa, requiring a fresh estimate for each state. That estimate must
not be assigned as an exact composition to the 313.45 K table row.

At finite composition, `D_Fick = Gamma * D_Maxwell-Stefan`; near the critical
region, `Gamma` need not be one even at small solute fractions. The article
does not provide a complete experimental composition table. Its simulation
curves at `xCH4=0.01` are separate computed results. Thus these measurements
remain a bounded qualitative stress test until composition and the corresponding
thermodynamic factor are established. The highest-pressure isobar is less
anomalous, but that does not eliminate the definition mismatch.
[Primary full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6560060/).

The supplement could not be retrieved in this audit. Neither the original
Takahashi 1972 numerical tables nor Dawson's final 1970 journal tables were
obtained. No values were reconstructed from third-party transcriptions or
repaired by guessed powers of ten.

## Preserved evidence

Downloaded publications, XML, repository metadata and page renders remain in
the ignored operator directory `state/diffusion-high-pressure-20261020/`.

| File | SHA-256 |
|---|---|
| Dawson dissertation PDF | `71227eec51a166ecec3dc95bbb185ac784da6f1df6235fae0623c36228745723` |
| Guevara-Carrion 2019 PDF | `2eb1d98363db8604dea4beb8ea5f65fd1b5e897b4e20392abe5fa97c1c008686` |
| Guevara-Carrion 2019 full-text XML | `2276be933ec3348f900680cfbb3a0f7349617f362a1b1ed824e3093e2b9805af` |

The XML was obtained from the
[Europe PMC primary-article endpoint](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6560060/fullTextXML).
No remote computation, transport-model change or flame launch was performed
for this source audit.
