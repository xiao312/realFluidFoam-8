# Liang Figures 1 and 2: source and qualification follow-up

21 October 2026, Asia/Shanghai. Status: investigated; neither figure is accepted.
This is a dated supplement to the [property comparison](liang-properties-20261019.md),
[critical-point audit](liang-critical-definition-audit-20261020.md), and
[conductivity audit](liang-hydrogen-conductivity-audit-20261020.md).
No production model, coefficient, case, or remote job changed. No critical-point
solve was repeated.

Figure 2 remains incompatible with the printed SRK inflection definition,
linear covolume mixing, and the standard major-species constants inspected.
Neither a coherent change of units nor a simple curve-label swap resolves it.
Figure 1's reference-density conversion is physically specified: methane mass
per corresponding molar volume requires the molecular-weight ratio. What
remains unknown is which complete conductivity implementation Liang used.
The existing Figure 1 overlay is not yet a quantitative paper comparison.

## Figure 2: definitions and labels

The owner-provided PDF was checked visually on pages 2 and 3. Equation (1)
uses molar volume; equation (2) uses mole fractions. Figure 2 labels black
curves against the left temperature axis and red curves against the right
pressure axis. Solid curves denote hydrogen/air and dashed curves methane/air.
The text specifies an inflection of the pressure-volume diagram. The labels
agree with the earlier vector extraction.
[Liang, Li and Law, DOI 10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070).

For that fixed-composition SRK definition, the earlier analytical derivation gives

```text
vc/b = 1 + cube_root(2) + cube_root(4)
Pc = 0.08664034996495773 R Tc / b
b = sum(Xi bi).
```

Changing the attraction parameter or its temperature function cannot remove
this identity while retaining the pressure equation and temperature-independent
linear `b`. At phi=1, the published hydrogen pair implies
`b=33.039 cm3/mol`, above every H2/O2/N2 constituent value. Their inspected
range is `18.386–26.752 cm3/mol`. Propagating the previous estimated reading
bounds, 0.1 K and 0.05 atm, gives about `0.112 cm3/mol`, far below the
`6.287 cm3/mol` excess. These are reading estimates, not author uncertainties.

Simple fuel-label permutations were checked algebraically using the existing
digitized pairs; no critical solver was run:

| Assignment of the published pairs | H2/air inferred b, cm3/mol | CH4/air inferred b, cm3/mol |
| --- | ---: | ---: |
| Printed labels | 33.039 | 24.193 |
| Exchange only the pressure curves | 17.177 | 46.533 |
| Exchange only the temperature curves | 46.533 | 17.177 |
| Exchange both fuel assignments | 24.193 | 33.039 |

The methane constituent bounds are `22.081–29.783 cm3/mol`. Every permutation
violates at least one mixture's bounds. Thus a simple fuel-legend swap is not
a joint explanation. A more general plotting or input error remains possible,
but the paper does not identify one.

A common pressure-unit error also fails: matching the native phi=1 pressures
would require multiplying the paper's H2 pressure by 1.5005 and its CH4 pressure
by 0.9147. One scale conversion cannot make these opposite corrections.

### Original Soave constants and mass conventions

Liang's reference 17 lists 1971, but the cited article is Soave's **1972**
paper, volume 27, pages 1197–1203. Its equations (5), (6), (13), and (15) give
`ac=0.42747 R²Tc²/Pc`, `b=0.08664 RTc/Pc`, and
`alpha=[1+m(1-sqrt(T/Tc))]²`, with
`m=0.480+1.574 omega-0.176 omega²`.
The original article discusses hydrogen using classical critical constants
and an acentric factor near -0.22; it supplies no unique effective-critical
replacement that resolves Liang's curves.
[Soave, DOI 10.1016/0009-2509(72)80096-4](https://doi.org/10.1016/0009-2509(72)80096-4);
[primary article text inspected](https://www.researchgate.net/publication/239154680_Equilibrium_Constants_From_a_Modified_Redlich-Kwong_Equation_of_State).

The fork's different `m` coefficients were already tested in the
[19 October audit](liang-critical-audit-20261019.md). Restoring Soave's original
coefficients changes the H2 phi=1 pressure from about 31.681 to 31.719 atm;
it does not approach 21.114 atm. Rounding `0.08664035` to `0.08664` changes
the covolume coefficient by only about four parts per million.

A consistent mass convention is mathematically equivalent. With mixture
molecular weight `W`, molar volume `v=W nu`, and mass-specific volume `nu`,

```text
Rmass = R/W; bmass = b/W; amass = a/W²
bmass = sum[Yi bi/Wi]
amass = (sum[Yi sqrt(ai)/Wi])².
```

These are derived transformations of the same pressure equation, so Tc and Pc
do not change. Mixing mass coefficients with mole fractions without conversion
would change the model; it is not an alternate valid convention.

True mixture phase criticality concerns composition stability as well as
mechanical stability. The previous audit already tested this distinction:
the alternative local candidate helps methane but strongly worsens hydrogen
and reverses its pressure trend. Kay-type averages also failed. These results
must not be repeated as proposed fixes, nor may the fixed-composition
`vc/b` identity be imposed on a composition-stability critical point.

**Interpretation:** the inspected information contains an internal incompatibility.
It does not prove a particular author coding error. The authors' original
species constants, composition arrays, critical routine, or raw curve data
would distinguish an undocumented model from a publication error. Keep the
verified SRK formulation unchanged; do not infer new coefficients from Figure 2.

## Figure 1: what the conductivity mapping establishes

The original NBS TRAPP code forms methane reference mass density with methane's
molecular weight. In `TCOND`, printed page 58, its expression is
`D0=.001*DX*HX*CMW0`, where `DX` is molar density. Consequently,

```text
rho0_mass = W0 h/v = rho_mix_mass h W0/Wmix.
```

The factor is about 0.50 for oxygen. Omitting it approximately doubles the
mapped mass density; that is a different model, not a harmless unit choice.
The effective molecular weight in the transport scaling is a separate quantity
and must not replace `Wmix` in this mass-to-mole conversion.
[Ely, NBS Technical Note 1039, original program](https://nvlpubs.nist.gov/nistpubs/Legacy/TN/nbstechnicalnote1039.pdf).

Cantera 3.2's `HighPressureGasTransport.cpp` uses mass density times `h_m`
directly in its reference-density expression. This explains the provenance
of the existing shortcut diagnostic; it does not establish Liang's choice or
make the two mappings equivalent.
[Cantera 3.2 source](https://cantera.org/3.2/cxx/d9/d63/classCantera_1_1HighPressureGasTransport.html);
local source pin `4a8358eb80cfeb50474386b5f9ec0b3a83519889`.

There is a useful simplification specific to Figure 1. In the coupled conformal
map described in the prior audit,
`ti=fi*T/(fm*Tci)` and `wi=hi*v/(hm*vci)`. For one pure species,
`fm=fi` and `hm=hi`; therefore `ti=T/Tci` and `wi=v/vci`.
Its partial molar volume is also `v`. This is an algebraic deduction:
coupled mixture mapping versus partial-volume mapping cannot explain a
pure-O2 discrepancy at the same prescribed volume. Existing pure-recovery
checks in `conductivity-probe/summary.json` support that reduction.
The unpublished rich-H2 mixture modification likewise does not specify a
different pure-O2 formula.

### New evidence from the cited 1983 article

The 1983 article itself was now read through a public reproduction. Printed
page 92, equations (19)–(21), applies the noncorrespondence correction to the
entire collisional/translational contribution and explicitly excludes critical
enhancement. Page 93 obtains reference density through the methane reference
EOS. Its reported validation covers hydrocarbon families, not pure O2 or H2.
The aggregate approximately 7% deviation is therefore not an oxygen acceptance
tolerance. This confirms that the correction is in the cited article, rather
than only in the earlier program.
[Ely and Hanley, 1983](https://doi.org/10.1021/i100009a016);
[primary article reproduction inspected](https://www.scribd.com/document/768293849/ely1983).

The reproduction's OCR does not reliably preserve every symbol in equation
(19). For the exact derivative, clamp, and multiplier, retain the visually
checked NBS Fortran and the formula already recorded in the prior audit.
No equation was implemented from damaged OCR.

Source-justified comparisons still available are the complete noncorrespondence
factor, a coherent set of original reference constants, and the original
reference-EOS density route versus the present SRK-density hybrid. They are
separate named variants, not a license to combine whichever parts fit Liang.
Low-temperature caloric input remains a separate limitation.

## Existing Figure 1 data and measurable comparison limits

The compiled property data are job **124887485**, source
`e208396bdba48592aacbf6bb9a1c41b8eca3d9bb`, library build **124657926**:
901 oxygen states, 100–1000 K at 100 atm. The frozen current NIST table has
181 states at 5 K spacing. A read-only aggregation of those existing files
gives the following relative errors, using `100*(model/reference-1)`.

| Temperature interval | Points | SRK density RMS, % | Correctly mapped conductivity RMS, % | Conductivity error range, % |
| --- | ---: | ---: | ---: | ---: |
| 100–195 K | 20 | 5.361 | 11.881 | -17.777 to -1.521 |
| 200–295 K | 20 | 1.882 | 6.645 | -0.150 to +8.013 |
| 300–1000 K | 141 | 0.622 | 9.264 | +6.227 to +14.895 |

The conductivity below 200 K uses extrapolated NASA Cp and remains unqualified.
That caloric limitation does not apply to the density equation. At 300 K,
the correctly mapped conductivity is 0.034070 W/(m K), versus current NIST
0.031543; at 1000 K the values are 0.083726 and 0.072872.
The mapping shortcut has a worse 300–1000 K RMS error, 15.315%, despite
looking closer to Liang's black model curve. Paper reproduction and agreement
with current reference data are different comparisons.

The current plotter overlays these predictions and selected NIST points onto
the original raster. It does **not** export Figure 1's original black curve
or triangle coordinates and therefore supplies no numerical residual against
either. Liang calls the markers experiments and attributes them to NIST,
but does not identify individual experiments, database version, or uncertainty
bars. Current WebBook outputs must remain separately labelled reference data.

The source raster is 775 by 1371 pixels. The existing axis calibration gives:

| Panel | One source pixel horizontally | One source pixel vertically |
| --- | ---: | ---: |
| Density | 1.1905 K | 0.3824 kg/m3 |
| Conductivity | 1.3400 K | 0.0002317 W/(m K) |

These are resolutions, not automatically uncertainty bounds. A quantitative
paper comparison should extract curve centers and triangle centers separately,
measure actual stroke/marker extent and repeatability, and propagate both
horizontal and vertical extraction intervals. On the steep low-temperature
curve, temperature uncertainty cannot be ignored. Record RMS and maximum
relative error alongside absolute error and overlap with the measured
digitization envelope. Do not assign an arbitrary percentage tolerance.
Density below the displayed curve's approximately 225 K lower edge is an
additional property check, not a visible Figure 1(a) comparison.

Useful independent reference uncertainty assessments exist:

- Lemmon and Jacobsen report oxygen conductivity uncertainty of **3% at
  270–300 K and 5% elsewhere**, with larger uncertainty near the critical
  region and unknown uncertainty above 100 MPa. The 2% dilute-gas estimate is
  not the appropriate default at 100 atm. Figure 1 uses 10.1325 MPa.
  [Original 2004 paper, conclusions, printed page 62](https://trc.nist.gov/refprop/FAQ/NAO.PDF).
- Lemmon et al., Section 7.2, report that the Schmidt–Wagner oxygen EOS,
  although originally qualified only to 300 K, extrapolates to 1000 K within
  **0.5% in density** against the cited high-temperature data.
  [Original 2000 paper, printed page 360](https://trc.nist.gov/refprop/Documents/Air.pdf).

These are reference-correlation assessments, not automatic allowable errors
for SRK or Ely–Hanley, and not paper-marker uncertainties. Identify the
current WebBook backend correlation before assigning them to the frozen
table. Subject to that identity, all 141 existing conductivity points from
300–1000 K exceed the 5% reference band; a visual match cannot qualify them.
No numerical acceptance tolerance has been approved.

## Next evidence and reproducibility

Keep three decisions separate:

1. **Implementation verification:** retain the existing SRK derivative,
   pure-fluid, reference-fluid, and species-splitting checks. Document which
   complete conductivity variant passes which check.
2. **Paper reproduction:** obtain Figure 1 numerical curve/marker extraction
   with measured image uncertainty; Figure 2 remains failed under its stated
   definition.
3. **Physical reference comparison:** report errors against the frozen NIST
   table and applicable reference uncertainty, with the sub-200 K conductivity
   exclusion. Owner review and declared criteria are still required for
   acceptance under the project rules.

This audit does not establish that Figures 1–8 pass and does not release the
conditional CFD replication gate. It identifies a finite property check to do
next without altering coefficients to fit the figures.

The note was prepared against checkout
`5da2bc6795917b445019c6ae9282614472b04e8d`; numerical results retain their
original build identity above. Paths here are relative to the outer project
`D:/xiaok/work/FlamePilot/projects/realfluidfoam`, not the Git root:

| Existing input | SHA256 |
| --- | --- |
| `state/liang-properties-20261019/job-124887485/properties/oxygen.csv` | `f944acd7f8089ab38ae756190ff28a09f57c704e71ad37c516d1b37709e64d65` |
| `state/liang-properties-20261019/nist/oxygen-100atm.tsv` | `369a894d2de0d0807f3f5fdd4f540a738302dab2cad7a77d90579926cb5e7499` |
| Owner-provided Liang PDF | `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe` |
| `state/liang-hydrogen-20261020/conductivity-sources/nist-tn1039.pdf` | `c3ea0e04a074c312f3c4852a02f5a691c3a92bde4e269691afef1fe47db6cbfa` |

The NIST manifest records retrieval at `2026-10-19T06:39:18.993150Z`,
pressure units of atm, density in kg/m3, and conductivity in W/(m K).
The table above is reproducible by joining the two CSV/TSV inputs on exact
temperature, selecting the displayed inclusive ranges, and computing
`sqrt(mean(relative_error_percent**2))`, minimum, and maximum.
No new simulation or fitted coefficient enters that aggregation.
