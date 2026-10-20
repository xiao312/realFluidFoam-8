# Liang Figure 8(b): author mechanisms and conversion checks

20 October 2026, Asia/Shanghai. Status: inputs acquired and checked; no flame
calculation or paper comparison accepted in this task. Original downloads,
conversion logs, hashes and diagnostic scripts are under
`state/liang-hydrogen-20261020/figure8b-sources/`, relative to the project root.
No production model, running job or upstream mechanism was changed.

**HP-Mech now has a usable, explicitly fixed-100-atm input. USC II has two
loadable variants because its author files contain conflicting duplicate
records. Hashemi's original mechanism remains blocked by a genuinely negative
summed rate in the flame preheat temperature range.**

## Source identity

Liang Section 3.2 and references 14–16 identify the mechanisms below. The paper
calls them methane sub-models or a methane sub-mechanism but supplies no species
selection, reaction selection, source-file hashes or extraction procedure.
This wording alone does not establish whether the full published mechanism or
a separately extracted subset was used. No exact Liang subset was found in
the project inventory or these author downloads. A C1-only extraction would
be an additional modeling choice, not a demonstrated reproduction.
[Liang, Li and Law](https://doi.org/10.1016/j.proci.2018.06.070).

| Liang reference | Acquired source | Species / reactions | Cantera 3.2 result |
|---|---|---:|---|
| 14: USC Mech II, 2007 | Hai Wang's author archive, May 2007 release | 111 / 784 | Two explicit duplicate-selection variants load; warnings and transport limitation remain |
| 15: Zhao et al., 2017 | Princeton HP-Mech page dated 18 May 2017 | 92 / 615 | Original conversion writes YAML but fails rate validation |
| 15: same rates at 100 atm | Separately named endpoint representation | 92 / 616 | Loads; altered channels positive over 298–3500 K and rate parity verified |
| 16: Hashemi et al., 2016 | Exact publisher supplementary ZIP | 68 / 631 | YAML writes but fails rate validation; do not launch |

The 2017 HP source is the historical author release, not the newer HP-Mech
3.3 or a subsequent methane/methanol model. Its page cites the exact paper in
Liang reference 15: *Effect of prompt dissociation of formyl radical on
1,3,5-trioxane and CH2O laminar flame speeds with CO2 dilution at elevated
pressure*, DOI `10.1016/j.combustflame.2017.05.005`.
[Author release page](https://engine.princeton.edu/mechanisms/hp-mech/).

Author/publisher download links:

- USC: [release page](https://web.stanford.edu/group/haiwanglab/USC%20Mech%20II/USC%20Mech%20II.html),
  [kinetics](https://web.stanford.edu/group/haiwanglab/USC%20Mech%20II/Mechanisms/USC%20Mech%20II/USC_Mech_ver_II.txt),
  [thermodynamics](https://web.stanford.edu/group/haiwanglab/USC%20Mech%20II/Mechanisms/USC%20Mech%20II/thermdat.txt),
  [transport](https://web.stanford.edu/group/haiwanglab/USC%20Mech%20II/Mechanisms/USC%20Mech%20II/trandat.txt).
- HP: [kinetics](https://engine.princeton.edu/mechanisms/hpmech-inp/),
  [thermodynamics](https://engine.princeton.edu/mechanisms/therm-dat/),
  [transport](https://engine.princeton.edu/mechanisms/tran-dat/).
  These pages contain raw data in HTML `pre` elements. The saved originals
  retain the HTML; `hp-*.dat`/`hp-chem.inp` contain the decoded data.
- Hashemi: [paper](https://doi.org/10.1016/j.combustflame.2016.07.016),
  [mechanism ZIP](https://ars.els-cdn.com/content/image/1-s2.0-S0010218016301766-mmc2.zip),
  [supplementary figures and tables](https://ars.els-cdn.com/content/image/1-s2.0-S0010218016301766-mmc1.pdf).
  The ZIP contains `mech.inp`, `therm.DAT` and `trans.dat`, preserved in
  `hashemi-author/`.

No explicit permissive software/data license was found in these acquired
mechanism files or release pages. Public download availability is not treated
as permission to redistribute the complete files in Git. The downloads remain
in ignored project state; this note records their identity and provenance.

## HP: a restricted representation that preserves the author rates

`hp-2017-author.yaml` fails Cantera validation for three negative PLOG
correction reactions and one HCCO channel. The three correction reactions
subtract prompt-dissociation contributions from the corresponding stable-HCO
channels. They have separate positive duplicate baseline reactions.
Individually taking a logarithm of their negative rate is undefined. The HCCO
PLOG channel has a negative *sum* at 10,000 K, although its sum is positive
through the qualified flame interval.

Cantera sums the Arrhenius terms at each PLOG pressure node, then interpolates
their logarithm. Beyond the tabulated pressures it uses the nearest endpoint.
These behaviors were checked against local Cantera 3.2 source
`src/kinetics/PlogRate.cpp` and its
[rate documentation](https://cantera.org/stable/reference/kinetics/reaction-rates.html#pressure-dependent-arrhenius-rate-expressions-p-log).

At precisely 100 atm, the following seven original reactions can be expressed
as their unchanged endpoint Arrhenius terms:

| Original one-based reaction IDs | Equation | Selected PLOG node |
|---|---|---:|
| 45, 46 | CH2O + OH ⇌ HCO + H2O | 10 atm, highest node |
| 48, 49 | CH2O + H ⇌ HCO + H2 | 10 atm, highest node |
| 51, 52 | CH2O + O ⇌ HCO + OH | 10 atm, highest node |
| 234 | HCCO + OH ⇌ HCOH + CO | 100 atm |

`fixed_pressure_hp.py` retains every selected `A`, `b` and `Ea` unchanged.
Negative terms use Cantera's explicit `negative-A` declaration and duplicate
Arrhenius reactions. Reaction 234 has two terms, increasing the representation
from 615 to 616 reactions. Every other original rate, species, thermodynamic
record and transport record remains unchanged. There is no reaction removal,
clipping, coefficient fitting or surrogate mechanism.

This is **not** a general PLOG regrouping. Between pressure nodes,
log-interpolation of a sum differs from a sum of separately interpolated
rates. The output therefore has a fixed-pressure contract:

```text
input: hp-2017-fixed-100atm.yaml
pressure: exactly 10,132,500 Pa = 100 atm
temperature qualification: 298–3500 K
species: 92
represented reactions: 616
```

For each changed channel, positivity was verified analytically over the entire
temperature interval. With one positive and one negative Arrhenius term, the
logarithm of their magnitude ratio is
`ln(A+/|A-|) + (b+−b−) ln(T) − (E+−E−)/(R T)`.
Its extrema occur at the interval endpoints or
`T = −(E+−E−)/[R(b+−b−)]`. The minimum positive/negative ratios are 3.24069,
1.26518, 1.75208 and 1.59854 for the four rows above; all exceed one.

Independent analytical evaluation of the unchanged author terms versus
Cantera's converted forward rate constants passed at 3,204 temperatures.
The maximum relative error was `8.99e-15`. Summed forward rates of progress
at five frozen states with every species present differed by at most
`1.12e-14`. The check threshold was `1e-10`. These tests qualify this
representation, not the scientific accuracy of the mechanism or a flame.
All reaction mappings, complete selected terms and coefficient hashes are in
`hp-fixed-100atm-validation.json`.

The required loader is:

```python
from fixed_pressure_hp import load_fixed_100atm
import cantera as ct

gas = load_fixed_100atm(100 * ct.one_atm, temperature_k=298.15)
gas.set_equivalence_ratio(phi, "CH4", {"O2": 0.21, "N2": 0.79})
```

The loader rejects 1 atm, 100 bar and initial temperatures outside the
qualification interval. A flame runner must also reject any solution whose
temperature leaves 298–3500 K. The standalone YAML cannot enforce that
runtime contract by itself. The helper resides beside the YAML, so import it
from that directory or load it by an explicit module path. Do not use this
input for pressure sweeps.

## USC II: usable variants with unresolved author-file ambiguities

The strict converter found two conflicting NASA7 duplicates: `CH2CHCO`
and `sC4H9`. Both species participate in the supplied 111-species mechanism.
The transport file also has conflicting records for `CH3CHOCH2` (geometry
1 versus 2), `iC4H5` and `C4H6` (collision diameter 5.176 versus 5.180 Å).
Other duplicate transport records are identical. Their source lines and
complete values are recorded in `normalization.json`.

Two variants preserve the first or last occurrence consistently:

```text
usc-author-first.yaml
usc-author-last.yaml
```

Both load in Cantera 3.2, with 111 species and 784 reactions. Several original
NASA polynomial discontinuity warnings remain in `input-validation.json`;
the coefficients were not repaired. Neither variant is selected by how well
it matches Liang.

The source transport file additionally contains a custom `DIFF` appendix
after its first `END`, including H/O2, H/N2 and H2/N2 binary fits. Generic
`ck2yaml` does not import this appendix. The variants contain the standard
species transport parameters only, while the complete appendix is preserved
in `trandat.txt`. Its coefficient conventions and whether Liang used these
overrides remain unverified. The two YAML files therefore support explicit
diagnostic runs, not a claim of exact author transport reproduction.

Mechanical parser edits are separate from these scientific ambiguities:
remove UTF-8 BOM and empty/comment-only thermo lines, replace TROE commas
with whitespace, insert the omitted species-section `END`, and discard
non-mechanism bibliography text after the reaction `END`. All originals
remain unchanged. `normalize_sources.py` records these transformations.

## Hashemi: confirmed negative endpoint, not a pressure-unit error

In the exact publisher mechanism, reaction 567 is
`CH2CHOO ⇌ CO2 + CH3`. Both terms below belong to its 100-atm PLOG block:

```text
A = −2.51e3,  b = 1.41, Ea = 14420 cal/mol
A =  4.05e−9, b = 5.14, Ea = 10480 cal/mol
```

The source uses cm, mol, s and cal/mol; PLOG pressure is atm. This channel is
unimolecular, so its summed rate constant has units s⁻¹. The audited values
are:

| Quantity | Result |
|---|---:|
| Negative interval at 100 atm | 488.24785–580.12981 K |
| Rate at 500 K | −0.0535613 s⁻¹ |
| Minimum rate | −0.404614 s⁻¹ at 554.47066 K |
| Rate at 600 K | 1.45164 s⁻¹ |

The problem remains after checking pressure-block membership, activation
energy units and both terms together. It is the same exact reaction and
coefficients reported in the Cantera project's
[2019 issue 77](https://github.com/Cantera/cantera-website/issues/77).
The maintainer confirms that the negative sum makes logarithmic pressure
interpolation undefined. The issue was closed by documenting the behavior;
it does not provide a corrected author rate.

Hashemi's paper tests flow-reactor data at 700–900 K and 100 bar, RCM data
at 800–1250 K and 15–80 bar, shock-tube data at 1100–1700 K and 7–456 bar,
and flame speeds at 1–10 bar. These experimental ranges do not validate
this 488–580 K rate at 100 atm. The affected source block cites Goldsmith
et al., [DOI 10.1021/acs.jpca.5b01088](https://doi.org/10.1021/acs.jpca.5b01088).
The exact original Goldsmith supporting-file temperature validity statement
was not recovered: ACS supporting-file access returned HTTP 403. Hashemi's
specific block does not state a fit interval. A secondary copied mechanism's
comments are not used to invent an author validity limit.

No authored positive alternative was found in this investigation. The
Hashemi flame remains blocked. Replacing this rate, clipping it, bypassing
validation or dropping its C2 network would change the model. The additional
original NASA enthalpy discontinuity for `HOCHO` at 1000 K is also preserved
and recorded.

## Reproduction and hashes

Use the project's existing `state/equilibrium-venv` with Cantera 3.2.0.
From the source directory, the short verification sequence is:

```text
python -B fixed_pressure_hp.py
python -B audit_inputs.py
```

`audit_inputs.py` checks all five YAML files, verifies the pressure/temperature
loader guards, independently locates the Hashemi negative interval and writes
`input-validation.json` plus `file-manifest.json`. The latter includes the
size and SHA-256 of every acquired and derived file. Original strict converter
failures remain in `hp-convert.log` and `hashemi-convert.log`.

| File | SHA-256 |
|---|---|
| `USC_Mech_ver_II.txt` | `1f999b6523cb4a7f5790582ce6d85901a70f6b7e2bfa68a32b7becf1340d6f1c` |
| `thermdat.txt` | `2fbed6c4c5362dc8e9f46a04c9325a3db0c992de9754e777c32626a5df45afed` |
| `trandat.txt` | `35c110cd2275845c4f4e4d57325cb59e4065ac7403b641cbd1cb7a3e1f6ca783` |
| `hp-chem.inp` | `e9a92c36cbc2c76a1367e69fea07dab0790830b92ebf53676b47f6da1f0d8bf8` |
| `hp-therm.dat` | `7152feac851a00c5b2e58fa18dc3adbef6e32f37eb10a84320344a69255b4076` |
| `hp-tran.dat` | `099695093244fadfd66a82c5027e9a0465809c9625da6b0402515a5864235995` |
| `hashemi-mmc2.zip` | `27ff94441f53f9742e056930e1d57bf3e4c231656de127b1aeaa52084d1986ac` |
| `hp-2017-fixed-100atm.yaml` | `cc34fbe54bfe71c79edabc6763934bdfbe4d1046ae5e33f67ca1efae02aa9afb` |
| `usc-author-first.yaml` | `378180928e9470ac6374b15a6b0ac7f2726f63f6dce65a87d2df0de97dad2cec` |
| `usc-author-last.yaml` | `847f6567a211d992c6f6efa57e06e230eeb25278321d9550006af4b1af0638b9` |

The next eligible calculation is a clearly labeled full-author HP mechanism
at exactly 100 atm, starting with Case 1 and then the established Case 3
extension. USC can be evaluated as two source-ambiguity variants. Figure 8(b)
must continue to mark exact methane-submodel identity and Hashemi as
unresolved until corresponding evidence is available.
