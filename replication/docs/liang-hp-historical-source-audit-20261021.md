# HP publication-era source audit, 21 October 2026

**The exact publisher supplement was recovered. Its active kinetics,
thermochemistry and transport records match our current HP inputs exactly.**
A change in the current author-page release therefore does not explain the
observed full-mechanism flame-speed discrepancy. The source does expose a
separate, testable distinction: our input is the **prompt HP** mechanism,
whereas the cited paper also calculates an HP mechanism without the three
CH2O prompt-dissociation additions.

Status: input identity tested; no new flame or mechanism accepted. This audit
made no solver changes and submitted no jobs. It follows the
[implementation audit](liang-figure8b-implementation-audit-20261021.md).

## Publication and acquired files

Liang reference 15 is Zhao, Fu, Haas and Ju, *Combustion and Flame* **183**
(2017), 253–260,
[DOI 10.1016/j.combustflame.2017.05.005](https://doi.org/10.1016/j.combustflame.2017.05.005).
It is not the 2015 acetylene paper, although both publications are cited in
the mechanism header. The original 2017 article was recovered through
[Hao Zhao's laboratory publication page](https://neec-pku.github.io/ZHAOHAO/publication.html)
and its [linked PDF](https://neec-pku.github.io/ZHAOHAO/pubs/J7.pdf).
Its supplementary-material statement explicitly identifies a prompt HP
mechanism. Section 2.2 distinguishes the base models from versions with
CH2O prompt reactions at 1 and 10 atm.

The PDF's embedded reference links identify PII `S0010218017301724`.
The publisher article landing page returned HTTP 403. Its publicly served
supplementary files were retrieved directly, without credentials or an
access-control workaround:

| Original | Bytes | SHA-256 |
| --- | ---: | --- |
| [Article, author copy](https://neec-pku.github.io/ZHAOHAO/pubs/J7.pdf) | 2,207,268 | `3d10f61b9a824c386efb38ac8e994692dcb450156807a531c7215baa77fcd0a0` |
| [Publisher mechanism ZIP, mmc2](https://ars.els-cdn.com/content/image/1-s2.0-S0010218017301724-mmc2.zip) | 59,387 | `6d44ddf4c95597464c20f363f47edf89941496d0add00585de1d4a55168b8dd1` |
| [Publisher supporting document, mmc1](https://ars.els-cdn.com/content/image/1-s2.0-S0010218017301724-mmc1.docx) | 52,589 | `e81a655b333b68d7e638e07db06c238ea22e5619d0bbbc1967dec0501d5df50f` |

The ZIP has three members, each with archive timestamp 14 June 2017,
10:47:10. These are archive metadata, not an independently authenticated
release time. Association with the publisher's article-specific supplement
provides the substantive provenance.

| ZIP member | SHA-256 |
| --- | --- |
| `HPMech_201706001300745086.inp` | `2d02d2d92a968fa5d694d03f95150929e3351786247a066ce4cddfeda9a62262` |
| `therm_201706001300745087.dat` | `22fbad516b2a36029a4bf14e56116cd6bb4d76b3435876047bca3c6b674fe5ec` |
| `tran_201706001300745088.dat` | `1824968858798066ce11f9e8342cbe60342c831643db7523ca6ef6b69b5e85d9` |

All originals remain in ignored project state; public availability is not
treated as a redistribution license.

## Exact comparison with the current input

The publisher files were compared with the original author-page downloads,
not with our transformed YAML. After removing blank lines and CHEMKIN comments,
every retained line is identical, including internal spacing and all numeric
tokens:

| Input | Active lines, each source | Parsed result |
| --- | ---: | --- |
| Kinetics | 1,302 | All 92 species and 615 reaction records identical |
| Thermochemistry | 643 | All 160 database records identical; all 92 used species covered |
| Transport | 161 | All active records identical |

The mechanism contains 88 PLOG reaction records. The independent parser
compared equations, reversibility notation, Arrhenius coefficients, duplicate
flags, LOW/Troe terms, efficiencies and every PLOG node. Thermochemical
temperature ranges and all NASA coefficients also match.

The different byte hashes have a mundane explanation. Thermo and transport
text become exactly equal after decoding and newline normalization. The
kinetics text additionally differs by one initial blank line. There is no
changed prompt coefficient or other active reaction in the present author
files relative to the publisher files.

This extends the earlier frozen-rate/conversion verification to a
publication-specific original. A repeat flame using these same coefficients
would not be an independent mechanism control. The existing fixed-100-atm
representation keeps its original pressure/temperature qualifications.

This finding supersedes the narrower historical uncertainty in the earlier
audit: current full-HP inputs now have a publisher-era identity check.
It still does **not** identify Liang's unpublished methane subset or determine
whether Liang enabled the prompt additions.

## Source-supported CH2O prompt-off control

The supporting document lists three groups. Each retains an ordinary
H-abstraction rate \(k_0\), subtracts a prompt fraction \(k_p\) from its
HCO-producing channel, and adds a direct H + CO channel with \(k_p\).
Thus the forward coefficients are \(k_0-k_p\) and \(k_p\).
The full forward CH2O consumption coefficient for that group is still \(k_0\),
but the immediate products and reverse reactions differ.

Reaction IDs below are **one-based original CHEMKIN records**, before the
HCCO endpoint representation adds an extra YAML record. Zero-based indices
are one less. Source lines refer to the unchanged publisher `.inp`.

| Retain baseline | Remove negative correction | Remove direct prompt | Baseline equation | Direct equation |
| --- | --- | --- | --- | --- |
| 45, line 308 | 46, line 312 | 47, line 316 | CH2O + OH ⇌ HCO + H2O | CH2O + OH ⇌ H + CO + H2O |
| 48, line 322 | 49, line 326 | 50, line 330 | CH2O + H ⇌ HCO + H2 | CH2O + H ⇌ H + CO + H2 |
| 51, line 337 | 52, line 341 | 53, line 345 | CH2O + O ⇌ HCO + OH | CH2O + O ⇌ H + CO + OH |

For \(k=A T^b\exp[-E_a/(RT)]\), the baseline terms are:

| Retained ID | A | b | Ea, cal/mol |
| --- | ---: | ---: | ---: |
| 45 | 7.820e7 | 1.630 | -1055 |
| 48 | 5.860e3 | 3.130 | 1514 |
| 51 | 1.560e8 | 1.670 | 1770 |

The source's default CHEMKIN units are mol, cm, s and cal/mol. The forward
channels are bimolecular, so \(k\) has units cm3/(mol s); A also carries the
corresponding K\(^{-b}\) factor. Every group has PLOG nodes at 1 and 10 atm.
The retained baseline coefficients are identical at both nodes. The prompt
magnitudes are:

| Correction/direct IDs | P, atm | \|A\| in machine file | b | Ea, cal/mol |
| --- | ---: | ---: | ---: | ---: |
| 46 / 47 | 1 | 2.587e11 | 0.692 | 9370.9 |
| 46 / 47 | 10 | 2.737e11 | 0.679 | 9904 |
| 49 / 50 | 1 | 5.109e7 | 2.182 | 11528 |
| 49 / 50 | 10 | 1.160e9 | 1.812 | 13167 |
| 52 / 53 | 1 | 9.338e17 | -0.803 | 21684 |
| 52 / 53 | 10 | 1.973e18 | -0.882 | 22607 |

The correction uses negative A; the direct channel uses positive A.
An XML-text extraction of the publisher DOCX was checked against all 18
tabulated HP reaction rows. Equations match throughout. Sixteen coefficient
triples match exactly. The two O-channel 1-atm entries print **9.348e17**,
where the machine supplement and current source both contain **9.338e17**.
That is approximately 0.107% in those coefficients, and must be preserved
as a source disagreement. All 10-atm terms match exactly.

At 100 atm, Cantera selects the highest authored PLOG endpoint, 10 atm,
as documented in its
[versioned PLOG documentation](https://github.com/Cantera/cantera/blob/v3.2.0/doc/sphinx/reference/kinetics/rate-constants.md#pressure-dependent-arrhenius-rate-expressions-p-log).
Therefore the 1-atm document discrepancy does not affect this 100-atm
comparison. This endpoint behavior is an extrapolation convention; it does
not establish experimental validation of these prompt rates at 100 atm.

A controlled ablation can consequently:

1. Remove exactly records 46, 47, 49, 50, 52 and 53.
2. Keep 45, 48 and 51 with their original coefficients and clear their now
   unpaired duplicate flags.
3. Preserve every species, thermochemical record, transport record and
   remaining reaction.

The result would have 609 raw reactions, or 610 if based on our existing
fixed-100-atm YAML that already splits the separate HCCO reaction. The latter's
pressure guard remains necessary. Check records by equation and coefficients
as well as ordinal: a different prior transformation can change indices.

Other reactions in the C2 network also produce H + CO directly. They are
outside the three documented CH2O additions and must remain in this control.
This is specifically a **CH2O prompt-off diagnostic on the full publisher
mechanism**. It is not the recovered 2015 HP release, not a methane-subset
extraction, and not demonstrated to be Liang's input. The source supports
testing the distinction; agreement with a figure would not establish identity.

## Review of the prepared control

The separately prepared `liang-kinetics/prompt_off.py` control was checked
against this contract. Its output retains the same 92 species and has
610 reactions. A parsed-YAML comparison confirms that only the specified
six reactions, the three unpaired duplicate flags and the description
change. All species, phase settings, thermo, transport and other reaction
records remain exactly equal to the fixed-100-atm parent.

The preparation's qualification records 24 forward/reverse rate checks
at 298, 500, 1000, 1800, 2500 and 3500 K, with two positive all-species
compositions. Every retained rate agrees exactly at these frozen states.
The output SHA-256 is
`aec705319b232278613acbc3f5784a61f9c5ace9e9a21578a0343d309f9d8caf`.
This verifies the control's content, not its agreement with Liang or
experimental validity above the author's pressure range. The flame runner
must retain the fixed-100-atm restriction.

## Reproduction and evidence

The evidence directory is:

```text
state/liang-hydrogen-20261020/hp-historical-source-audit/
```

It contains original downloads, all retrieval receipts, safely extracted
ZIP members, the DOCX text, complete source diffs and `compare_publisher.py`.
The latter imports the existing independent `raw_chemkin.py` reader and
records its hash. It performs no mechanism conversion or model change.

Using the project's analysis virtual environment:

```text
python -B compare_publisher.py plan
python -B compare_publisher.py apply --output verification-002
```

`apply` requires a new output directory, so use a fresh name when repeating
the check. `verification-002/comparison.json` contains complete reaction
records, all 18 SI coefficient comparisons and the machine-readable
`prompt_off_control_contract`. The plan and apply checks passed.

Author-site repository metadata was also retained. Its current tree contains
the article PDF but no matching mechanism or supplement file; its repository
was created in 2022. The publisher supplements provide stronger evidence for
this question than that later Git history. No inaccessible archive or
publisher-page restriction was bypassed.
