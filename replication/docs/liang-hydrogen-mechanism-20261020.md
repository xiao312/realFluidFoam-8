# Liang hydrogen mechanism and transport provenance, 2026-10-20

Liang's section 2 names Burke et al. for hydrogen. The matching public author
release is **Burke, Chaos, Ju, Dryer and Klippenstein (2012), version 6-10-2011**,
with the nitrogen bath-gas falloff block enabled. Its kinetics and thermochemistry
can be used now. Its supplied transport contains an additional pair-diffusion
extension, so an ordinary Cantera conversion is not the complete transport model.
No flame result was generated in this source audit.

Sources: [Liang, section 2 and reference 12](https://doi.org/10.1016/j.proci.2018.06.070),
[Burke publication](https://doi.org/10.1002/kin.20603), and
[Burke's download page](https://burke.me.columbia.edu/content/mechanisms-and-downloads).
The local Liang PDF is `C:/Users/xiaox/Desktop/1-s2.0-S1540748918302530-main.pdf`.
The Liang source revision and exact transport input are not specified in the paper.
The current public Burke release is therefore a traceable reconstruction input,
not proof of bitwise identity to Liang's calculation.

## Files obtained and conversion

Raw evidence is under the project-local
`state/liang-hydrogen-20261020/mechanism-source/`. `sources.json` records URLs,
hashes and sizes; `conversion-audit.json` records the Cantera conversion checks.
Downloaded papers and mechanism files remain outside the public Git checkout.

| Local file | Primary source | SHA-256 |
|---|---|---|
| `burke-2012-chem.inp` | [Author kinetics with embedded NASA thermochemistry](https://burke.me.columbia.edu/sites/default/files/content/chem.txt) | `a68b12b089bb908242bf7673d6dfe34e4a08953dfcf3ba99da37b6db70d709d7` |
| `burke-2012-tran.dat` | [Author transport](https://burke.me.columbia.edu/sites/default/files/content/tran.txt) | `35c110cd2275845c4f4e4d57325cb59e4065ac7403b641cbd1cb7a3e1f6ca783` |
| `burke-2012-author.cti` | [Author Cantera file](https://burke.me.columbia.edu/sites/default/files/content/chem_cti.txt) | `3648ea70bcf658ca6ba4b9e449e5a9f49ddf51999bad7bc60c1ad591442a5fbc` |
| `Burke-2012-author-manuscript.pdf` | [Author manuscript](https://burke.me.columbia.edu/sites/default/files/content/Burke_et_al-H2_Model_Revised_Manuscript_Submitted_7-25-11.pdf) | `caf9045357849d18ec5815c38c2b95c4f0c9a82f2526182f37d743a3b89949d6` |

The species order is `H H2 O OH H2O O2 HO2 H2O2 N2 AR HE CO CO2`:
13 species and 27 reversible reaction entries, including duplicate Arrhenius
terms. Cantera 3.2.0 classifies these as 16 Arrhenius, 9 three-body Arrhenius and
2 Troe falloff reactions. The separate Ar/He collider channels account for part of
the count. CO and CO2 are available bath species; this is not a carbon oxidation
mechanism.

The author file specifies a choice of bath-gas approximation for
`H + O2 (+M) <=> HO2 (+M)`. The active N2 block has
`LOW / 6.366e20 -1.72 524.8 /`; the commented Ar/He alternative uses
`9.042e19 -1.50 492.2` and different efficiencies. Keep the N2 block for H2/air.
Both use the supplied high-pressure limit and Troe broadening. Do not add newer
2013 or 2017 Burke reaction updates to this replication baseline.
[Author kinetics](https://burke.me.columbia.edu/sites/default/files/content/chem.txt)

The strict command using the complete transport file failed: `ck2yaml` reads the
post-`END` pair records as malformed species transport. The failure was not bypassed
with `--permissive`. A separate `burke-2012-lj-only.tran` contains exactly the 13
matching species rows, preserving their numbers. The command was:

```text
python -B -m cantera.ck2yaml --input=burke-2012-chem.inp --transport=burke-2012-lj-only.tran --output=burke-2012-lj.yaml
```

It passed strict conversion and Cantera loading. The generated baseline hash is
`f5e015f4c7908eff0202f2cfe0df966ce777a1ad86be0a930efb5764a557c2f0`.
A separate `cti2yaml` conversion of the author CTI loaded the same 13 species and
27 reactions. Across 54 states (300, 600, 1000, 1500, 2500, 3500 K; 1, 10, 100 atm;
phi 0.5, 1, 2), both conversions gave exactly equal forward and reverse rate
constants, standard cp and enthalpy, and binary diffusion coefficients. This
qualifies conversion consistency, not agreement with Liang. Most NASA fits start
at 300 K; a 298 K inlet would slightly extrapolate those fits.

The first generated YAML contained malformed UTF-8 in the Hong et al.
bibliographic page range in a reaction `note`. Cantera loaded it, but Python's
strict UTF-8 reader rejected it. The original is preserved. Its LF/UTF-8 copy,
`mechanism-source/burke-2012-lj-utf8.yaml`, has SHA-256
`3a227ac76148d4fce35b2dda1d57989bee885eb1cce37b14295e47de88729cc6`.
All five numeric comparisons above remain exactly equal over the 54 states.
`utf8-canonicalization-audit.json` records the note-only repair.

### Reproducing acquisition and conversion

`replication/development/liang-hydrogen/acquire.py` pins the three author input
hashes, downloads them from their primary URLs, extracts transport records, and
runs strict `ck2yaml` and independent `cti2yaml` conversions with Cantera 3.2.0.
It also accepts an offline directory containing the same byte-exact author files.
Choose a new output directory outside Git:

```sh
python -B acquire.py plan /project/state/burke-inputs --source-dir /project/state/author-downloads
python -B acquire.py apply /project/state/burke-inputs --source-dir /project/state/author-downloads
```

Omit `--source-dir` for HTTPS acquisition. `plan` performs no download or writes;
with an offline source it verifies hashes. `apply` refuses existing output
directories, changed source hashes and Cantera versions other than 3.2.0. It
preserves the raw files, fixes only the known nonnumeric page-range defect,
normalizes generated YAML to LF/UTF-8, and removes the generated date so conversion
output does not depend on execution time. `pair-coefficients.json` remains
separate from the LJ baseline and feeds the optional transport override.

An offline run in `state/liang-hydrogen-20261020/acquisition-verification/`
passed all 54-state independent comparisons with zero numeric differences.
Its reproducible `burke-2012-lj-utf8.yaml` hash is
`d2dce0d282ffe5f58e52277f75ee74c580361ccd76bc51c7f0c284b28f45ea19`.
This differs from the first canonical copy because the reproducible conversion
uses an ASCII page-range hyphen and omits the generated date. The acquisition
manifest records all source/output hashes and comparison errors.

## The appended diffusion model

The first `END` terminates conventional species transport data. The subsequent
12 four-row pair records terminate at `ENDDIFF`. Burke's manuscript transport
section explicitly describes using improved pair diffusion derived from quantum
calculations. The author CTI does not contain these corrections. Its numerical
agreement with the LJ-only conversion confirms that omission.
[Burke manuscript, page 29](https://burke.me.columbia.edu/sites/default/files/content/Burke_et_al-H2_Model_Revised_Manuscript_Submitted_7-25-11.pdf)

The same polynomial coefficients and their interpretation are published by their
compiler, Hai Wang, in the [FFCM transport documentation](https://web.stanford.edu/group/haiwanglab/FFCM1/pages/transport.html).
For the first row,

`D_ij(T,p) [m2/s] = 1e-4 * (101325 / p[Pa]) * exp(d0 + d1*ln(T[K]) + d2*ln(T[K])^2 + d3*ln(T[K])^3)`.

Wang specifies the 1 atm reference and natural-log polynomial. The cm2/s
interpretation follows the CGS Sandia/Chemkin transport convention; see the
[transport manual](https://www3.nd.edu/~powers/ame.60636/transport.pdf). The next
three rows are A-star, B-star and C-star collision-integral ratios. Their fits use
**actual T**, not reduced temperature. They are required for multicomponent and
thermal diffusion; only D is required for mixture-averaged diffusion without
Soret. The source does not state a single fit-validity interval. Do not present
an arbitrary evaluation grid as a published validity range.

`pair-coefficients.json` preserves all 12 records, their source line numbers,
comments, formula and source hash. Ten pairs exist in the Burke species set:
H-He, H-H2, H2-He, H-Ar, H-O2, O-O2, H-N2, H2-N2, N2-N2 and H2-H2.
N-H2 and N-N2 are excluded because atomic N is absent. This includes self-diffusion
pairs, although those do not enter an ordinary non-pure mixture sum.
Liang does not explicitly say whether he enabled this extension. It should be
an identified transport variant, not silently substituted for the LJ baseline.

## Cantera application path

Cantera 3.2 implements both binary and mixture-averaged coefficients using
`GasTransport::m_bdiff`, populated by virtual `updateDiff_T()`. The high-pressure
base multiplies those entries by Takahashi before forming the same mixture sums.
An exact implementation in `StagedTransport` can call the base update and replace
selected symmetric entries with `101325 * 1e-4 * exp(polynomial)`. This avoids
changing other transport fits. Override only after loading indices and validating
positive coefficients. [GasTransport source](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/GasTransport.cpp#L123),
[virtual declaration](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/transport/GasTransport.h#L154),
[high-pressure application](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/HighPressureGasTransport.cpp#L219).

The public Python setter `set_binary_diff_coeffs_polynomial(i,j,coeffs)` also works.
CK mode uses four log coefficients: add `ln(101325*1e-4)` to d0. Default mode instead
fits `p*D/T^1.5` with a fourth-degree polynomial; the original four coefficients
cannot be passed directly. [Cantera API](https://www.cantera.org/3.2/python/transport.html)

`pair-api-audit.json` tests the CK setter at 300, 600, 1000, 2000 and 3000 K,
1 and 100 atm. All 100 pair values and ten independent mixture reconstructions
pass with maximum relative error `4.440892098500626e-15`. This test does not modify
the production adapter or solve a flame. At 2000 K the supplied pair fits change
H-H2, H-N2 and H2-N2 diffusion by +42.52%, +13.55% and +7.71% relative to the
same author LJ data in CK mode. These differences justify an isolated comparison;
they do not prove improved agreement with Liang.

## Rights and next qualification

The kinetics and CTI retain the authors' copyright notice. No explicit open-source
redistribution license was found in the retrieved files or author listing. Keep
raw downloads and generated mechanism inputs in controlled project state; public
Git can retain source URLs, hashes, preparation logic and derived verification
summaries. This is a provenance observation, not a restriction on the authorized
local calculations.

For Figures 3-7, first compare the Burke N2 kinetics with the explicit LJ baseline,
then the supplied pair-diffusion variant with every other setting fixed. Figure 2
is a mixture critical-point calculation and does not require reaction kinetics.
The transport extension does not resolve Liang's unspecified rich-H2 conductivity
mapping or the known critical-pressure ambiguity.
