# Independent hydrogen-mixture conductivity measurements

21 October 2026, Asia/Shanghai. Research only; no solver, running inputs, jobs,
or model coefficients changed. Context: source
`fcd11507e74587a4e3aced0f383d630018121a01` and the
[conductivity source review](liang-hydrogen-conductivity-source-review-20261021.md).

**No new dilute hydrogen-mixture validation has passed.** A primary H2/N2 paper
provides a concrete 42-point candidate, but its original table image and pressure
have not been qualified. A NIST measurement report was recovered and inspected;
its room-temperature N2/O2 data now have a provisional finite-density comparison.
Neither finding justifies changing the flame conductivity baseline.

## Hydrogen data: a usable next source, with remaining gates

[Gray, Holland and Maczek (1969)](https://doi.org/10.1039/TF9696501032)
measured six binary systems formed from H2, D2, O2 and N2O at 50 and 100 degrees C.
The publisher abstract establishes those conditions, not individual data points
or their uncertainties. The PDF request returned HTTP 403. OpenAlex reports no
open repository location. No numerical H2/O2 data were accepted. The temperatures
convert to 323.15 and 373.15 K; rounded labels in later figures should not replace
the original experimental conditions.

[Mukhopadhyay, Das Gupta and Barua (1967)](https://doi.org/10.1088/0508-3443/18/9/312)
is the strongest recovered alternative. Its
[public coauthor-uploaded full text](https://www.researchgate.net/publication/258287189_Thermal_conductivity_of_hydrogen-nitrogen_and_hydrogen-carbon-dioxide_gas_mixtures)
exposes Table 2, printed page 1303: 42 H2/N2 points at seven temperatures,
including two pure endpoints per temperature. The authors state 1% accuracy,
without a coverage factor. Mixtures were prepared by partial pressures and
checked by mass spectrometry; this supports a molar interpretation. Measurement
pressure remains unestablished from the accessible text.

The original uses **4.1855 J/cal**. If its conductivity column is confirmed as
`K_expt * 10^5` in `cal/(cm s degree C)`, the SI multiplier is `0.0041855`.
At 293.25 K the provisional pure N2/H2 values become
`0.025657115 / 0.176042130 W/(m K)`. Use the measured column: the other two columns
are predictions, one using measured pure-gas inputs. This distinction directly
supports separating endpoint-property error from mixing-rule error.

The publisher route returned a CAPTCHA rather than a PDF; the public author-PDF
route returned HTTP 429. No challenge or rate limit was bypassed. The saved
42-point CSV is **text-only and provisional**: the table layout, exponent and
readings still require visual verification. The seven temperatures are
258.25, 273.25, 293.25, 353.25, 393.25, 433.25 and 473.25 K. No model-error score
was calculated from this CSV.

An additional concrete source is
[Kestin, Nagasaka and Wakeham (1982)](https://doi.org/10.1002/bbpc.19820860302).
The [author institution's record](https://keio.elsevierpure.com/ja/publications/thermal-conductivity-of-mixtures-of-hydrogen-with-nitrogen/)
specifies H2/N2 measurements at nominal 300.65 K and 0.7-10 MPa, with estimated
uncertainty of 0.3%. Its zero-density limit is a reduction of finite-pressure
measurements, not a separate zero-pressure measurement. No numerical table was
recovered here.

## Verified NIST table, with a different validation scope

The original [NISTIR 3961 government copy](https://www.govinfo.gov/content/pkg/GOVPUB-C13-374e8d83887744b1c1a2c07a26ccccd2/pdf/GOVPUB-C13-374e8d83887744b1c1a2c07a26ccccd2.pdf)
was downloaded successfully. DOI: [10.6028/NIST.IR.3961](https://doi.org/10.6028/NIST.IR.3961).
It archives transient-hot-wire mixture measurements. Table 2 reports an actual
composition of 49.998% N2 and 50.002% O2; the inspected text does not explicitly
label the percentage basis, so the benchmark must resolve it before use.

These rows and headings were visually checked on printed page 40, PDF page 46:

| Run-point | Pressure, MPa | Conductivity temperature, K | Conductivity, W/(m K) | STAT |
|---|---:|---:|---:|---:|
| 1213 | 1.935 | 304.078 | 0.02757 | 0.001 |
| 1214 | 1.935 | 303.523 | 0.02747 | 0.001 |
| 1215 | 1.935 | 303.006 | 0.02735 | 0.001 |
| 1216 | 1.935 | 302.542 | 0.02742 | 0.001 |

Printed page 2 defines STAT as relative two-sigma slope-fit precision. It is
**not a complete accuracy budget**. The tabular conductivity rounding half-width
is `0.000005 W/(m K)`. Evaluate conductivity at the table's conductivity
temperature, not the roughly 300.10 K cell temperature assigned to thermal
diffusivity and derived Cp. These finite-pressure, non-hydrogen rows do not
isolate the dilute large-molecular-mass-ratio mixing problem.

## Bounded evaluation of the four NIST states

An exploratory calculation retained **both** interpretations of the reported
composition. Each uses the reported pressure and conductivity temperature,
the existing Burke input and species table, Cantera 3.2.0, and the independent
SRK/Ely-Hanley kernel. No flame was solved and no coefficient changed.
The reference density printed in the report remains labelled as DDMIX output;
the models calculate their own SRK volume.

| Model | RMS error, mole-percent interpretation | RMS error, mass-percent interpretation |
| --- | ---: | ---: |
| Cantera dilute mixture | 2.672% | 2.684% |
| Current full EH, partial-volume mapping | 7.991% | 7.948% |
| Current EH dense increment + Cantera dilute term | 2.945% | 2.923% |
| Coupled mapping, TN 1039 constants and noncorrespondence correction | 6.175% | 6.116% |

The dilute result is low; the three finite-density variants are high at all
four points. Changing the composition interpretation changes the RMS errors
by less than 0.06 percentage point. Thus this particular ambiguity does not
explain the observed differences. These are four repeated measurements at one
pressure near one temperature, not four independent composition/pressure tests.
No pass/fail criterion or fitted correction is inferred from them.

Replay from the Git root, with Python Cantera 3.2.0 and the existing input
directory supplied as `INPUTS`:

```text
python -B replication/development/liang-properties/conductivity_measurements.py plan INPUTS replication/development/liang-properties/nistir3961-reference.json NEW_OUTPUT.json
python -B replication/development/liang-properties/conductivity_measurements.py apply INPUTS replication/development/liang-properties/nistir3961-reference.json NEW_OUTPUT.json
```

The [public result record](liang-nist-conductivity-provisional-20261021.json)
contains all eight state/basis combinations, input/code hashes, mapped states,
individual signed errors and qualification limits. The portable module reproduces
the initial local probe's model values exactly. This diagnostic does not establish
which variant reproduces Liang's unprovided hydrogen modification.

## Reproducible benchmark design

1. Qualify the original H2/N2 Table 2 image, measured column, unit exponent,
   composition basis and pressure. Retain the original PDF hash and page crops.
   Keep reading/rounding error separate from the authors' 1% accuracy statement;
   do not invent a statistical confidence level.
2. Evaluate all 42 published states without composition interpolation. Pin the
   current mechanism, pure transport inputs and conductivity implementations.
   Compare the existing Mathur, fixed Mason-Saxena 1.065, full Ely-Hanley and
   Ely-Hanley dense-increment variants. Keep coefficients fixed independently
   of the measurements and Liang flame curves.
3. Report 14 endpoint checks separately from 28 interior mixture checks. Then
   repeat the mixture-rule calculation with measured pure conductivities where
   the rule accepts them. Retain and identify any modelled pure viscosities or
   other inputs; measured conductivity endpoints do not eliminate those errors.
   For an indivisible conformal-mapping model, report its endpoint error rather
   than silently rescaling the whole model.
4. Retain residuals versus composition and temperature, signed bias, RMS and
   maximum absolute relative error. Test whether residuals exceed the stated
   accuracy plus source-reading limits. Do not select a universal correction
   from a single binary system. A dilute-property pass does not qualify dense
   flame transport or demonstrate Liang's undocumented hydrogen modification.
5. Treat NISTIR 3961 as a separate finite-pressure benchmark after resolving its
   composition basis and full uncertainty budget. Preserve the reported pressure
   and conductivity temperature; do not label the report's empirical
   zero-density correlation as an independent measured datum.

## Evidence and replay

All raw evidence is under the project-relative directory
`state/liang-hydrogen-20261020/conductivity-measurement-audit/`:

- `qualification.json`: source URLs, access failures, interpretation limits and
  SHA-256 hashes of local artifacts.
- `mukhopadhyay1967-table2-provisional.csv`: 42 provisional H2/N2 readings,
  original reported values, inferred SI conversion and an empty pressure field.
- `nistir3961-table2-four-rows.csv`: visually checked NIST rows, including density,
  wire power, cell temperature and printed/PDF page identifiers.
- `nistir3961-table2-four-rows.json`: standalone inputs with SI conversions,
  unresolved composition basis, precision/rounding/full-accuracy distinctions,
  source PDF and page/crop hashes. This source fixture contains no model results.
- `nistir3961-provisional-evaluation.json`: the separate eight-state diagnostic
  above, including all inputs, model outputs and script hashes.
- `nistir3961-page-08.png`, `nistir3961-page-29.png` and
  `nistir3961-page-46.png`: verified original pages. Two matching crops retain
  the composition statement and the four rows with their complete column units.
  Other saved renders are navigation evidence, not additional qualified readings.
- `nistir3961-govinfo.pdf`: original scan, 4,884,669 bytes, SHA-256
  `f30d6632e95f88bd13182f7b25f4e810d949ef28fac29738af23f0760e85b800`.

The failed IOP download is preserved as `mukhopadhyay1967-iop-challenge.html`,
not as a falsely labelled PDF. No downloaded paper is added to Git. The next
source action is legitimate access to the original Gray or Mukhopadhyay table,
or the Kestin H2/N2 numerical table; more flame jobs cannot resolve this source
qualification gap.
