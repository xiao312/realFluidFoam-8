# Liang Figures 2 and 4: fresh-mixture density consistency

21 October 2026, Asia/Shanghai. Status: investigated; no model change.
Figure 4's hydrogen/air density is consistent with the current extended-Cantera
SRK implementation within the published image's reading bounds. It does not
support changing the EOS to reproduce Figure 2's critical pressures.
This supplements the [critical-definition audit](liang-critical-definition-audit-20261020.md)
and [source follow-up](liang-figure12-followup-20261021.md).

The original page was checked visually. Figure 4's black line is **Case 1
ideal-gas density**, and its black triangles are **Case 2 calculated density**,
not experimental measurements. The red quantities use the separate burning-flux
axis. Section 3.1 identifies these as densities of the initial, unburned mixture
at 100 atm.
[Liang, Li and Law, Figure 4 and Section 3.1](https://doi.org/10.1016/j.proci.2018.06.070).

## Comparison with the existing Case 2 runs

The initial LJ-transport runs use source
`ff39189850d8ec83277e3abe093cfc037f8da900`, build **125068607**, the author Burke
mechanism, 298 K, 100 atm, and 21/79 molar O2/N2 air. The actual pinned
`SrkKernel.h` uses the original Soave coefficient
`m=0.480+1.574 omega-0.176 omega²`.
The earlier compiled OpenFOAM property audit instead used the fork's
`m=0.48508+1.5517 omega-0.15613 omega²`. Both use the same pure-species
Tc/Pc covolumes; these source identities must remain distinct.

The existing vector extraction stores both each triangle's bounding-box
midpoint and its geometric centroid. The original plotting package's anchor
convention is unknown. Changing the reading from midpoint to centroid lowers
the reported density by approximately 0.228–0.229 kg/m3, within the retained
full-symbol reading half-bound of approximately 0.693–0.696 kg/m3.
The reference JSON was not changed.

| phi | Job | Native inlet density, kg/m3 | Paper midpoint, kg/m3 | Paper centroid, kg/m3 | Native/centroid difference, % |
| --- | --- | ---: | ---: | ---: | ---: |
| 0.6 | 125071231 | 93.76777 | 94.02873 | 93.80078 | -0.0352 |
| 0.8 | 125071234 | 88.09169 | 88.34685 | 88.11897 | -0.0310 |
| 0.9 | 125071241 | 85.52987 | 85.77739 | 85.54944 | -0.0229 |
| 1.0 | 125069036 | 83.12873 | 83.37761 | 83.14866 | -0.0240 |
| 1.1 | 125071247 | 80.87344 | 81.11855 | 80.89066 | -0.0213 |
| 1.2 | 125071250 | 78.75093 | 78.99677 | 78.76888 | -0.0228 |
| 1.3 | 125071254 | 76.74969 | 76.99965 | 76.77063 | -0.0273 |
| 1.4 | 125069084 | 74.85950 | 75.10783 | 74.87888 | -0.0259 |
| 1.5 | 125071271 | 73.07127 | 73.31845 | 73.08943 | -0.0248 |
| 1.6 | 125071279 | 71.37689 | 71.61816 | 71.38915 | -0.0172 |
| 1.7 | 125071284 | 69.76910 | 70.01694 | 69.78905 | -0.0286 |
| 1.8 | 125071308 | 68.24137 | 68.48954 | 68.26166 | -0.0297 |
| 1.9 | 125071315 | 66.78780 | 67.02938 | 66.80042 | -0.0189 |
| 2.0 | 125071350 | 65.40309 | 65.64868 | 65.41967 | -0.0253 |
| 3.0 | 125071380 | 54.46803 | 54.71037 | 54.48242 | -0.0264 |

The 15 common conditions have **0.335% RMS difference against midpoint
readings**, or **0.0258% against centroid readings**. Every native value lies
within the existing vertical reading bound even before adding horizontal
marker uncertainty. This does not establish which anchor the author used.
It shows that the small apparent density offset can be explained by reading
convention without changing physics.

The paper markers near phi=0.7, 2.25, and 2.5 have no exactly corresponding
initial LJ run. They were not filled by interpolating CFD or flame results.
The local property-only diagnostic evaluates its equations at all 18 original
marker positions; those results are separately labelled.

An independent NumPy cubic-root evaluation reproduces the 15 recorded inlet
densities within **9.1e-13 kg/m3**. This checks the species weights, composition,
units, original-alpha coefficients, and gas-root selection used in this audit.
It does not establish the correctness of the reacting energy or transport
equations elsewhere in the flame.

## The ideal density line constrains the upstream state

At the stated pressure and assumed composition,
`T = p Wmix/(R rho_ideal)`. Applied to the Case 1 vector line at the 18 Case 2
marker positions, this gives nominal temperatures **298.002–298.079 K**.
The line's existing vertical stroke bounds alone expand the combined range
to approximately **297.31–298.77 K**. Composition and horizontal reading
uncertainty would broaden it further.

Thus Figure 4 independently supports the current 298 K assumption already
noted in the [hydrogen progress record](liang-hydrogen-progress-20261020.md).
It does not prove an inlet temperature to hundredths of a kelvin. The inference
also conditions on the printed pressure: ideal density constrains `p/T`, not
pressure and temperature independently.

## What density can and cannot infer about a and b

For molar volume `v=Wmix/rho`, the stated SRK equation gives the conditional
relation

```text
a(b) = [R T/(v-b) - p] v (v+b).
```

If `a(T)` is instead held at its baseline value, the physical root of

```text
p v b² + (R T v + a)b + (R T v² - a v - p v³) = 0
```

gives a conditional covolume. These are algebraic inversions, not a fit of
species coefficients. At one temperature and pressure, density supplies one
constraint for two quantities. It cannot independently identify both parameters,
their temperature derivatives, or the species mixing rule.

The table uses the paper midpoint as the nominal reading. The inverse-b range
propagates the full Figure 4 density and horizontal marker extents, including
the extractor's 0.025 PDF-point allowance, while holding T=298 K and the
baseline attraction function. It is a reading interval, not a statistical
confidence interval or a bound on unknown model-form error.

| Nominal phi | Baseline b, cm3/mol | b from Figure 4 at fixed baseline a, cm3/mol | Figure 4 inverse-b reading range, cm3/mol | Figure 2 implied b, cm3/mol |
| --- | ---: | ---: | ---: | ---: |
| 0.6 | 24.284 | 23.704 | 19.894–27.662 | 29.864 |
| 1.0 | 23.587 | 22.952 | 19.171–26.874 | 33.039 |
| 1.9 | 22.493 | 21.701 | 17.843–25.700 | 40.988 |

The small baseline-b differences from the previous audit arise because the
Figure 4 markers are at their measured phi values, within 0.00022 of the nominal
values. Figure 2 values are reused from the preceding audit at nominal phi.
The previous estimated Figure 2 calibration bounds remain 0.1 K and 0.05 atm;
their propagated b uncertainty is much smaller than these discrepancies.

Inserting the Figure 2 covolume while leaving the baseline attraction unchanged
lowers density away from Figure 4:

| Nominal phi | Paper midpoint density, kg/m3 | Density with Figure 2 b and baseline a, kg/m3 | Change in a needed to recover that density at Figure 2 b |
| --- | ---: | ---: | ---: |
| 0.6 | 94.029 | 91.291 | +39.5% |
| 1.0 | 83.378 | 79.599 | +74.2% |
| 1.9 | 67.029 | 61.693 | +183.6% |

At phi near 1, the baseline `a(298 K)` is 0.0508735 Pa m6/mol2.
Holding its b fixed, the midpoint reading implies 0.0530807, with a broad
reading interval 0.0400208–0.0653914. Holding Figure 2's b instead requires
0.0886025. The ability to compensate one parameter with the other is why the
density match alone cannot prove a unique EOS.

The stronger restriction remains Liang's printed linear covolume mixing:
with the inspected H2/O2/N2 constants, any mixture b must lie between the
constituent values. The earlier Figure 2 inconsistency cannot be repaired by
adjusting only attraction, including its alpha function or binary attraction
corrections. A different model would require independent evidence.

## Documented input alternatives

The following property-only alternatives were checked without altering baseline
inputs. The critical values use the analytical inflection relation; the
previous finite-difference critical solves were not repeated.

| Input convention | Density near phi=1 at 298 K, kg/m3 | Inflection Tc at phi=1, K | Inflection Pc at phi=1, atm | b at phi=1, cm3/mol |
| --- | ---: | ---: | ---: | ---: |
| Current extended Cantera, original Soave alpha | 83.1258 | 105.232 | 31.719 | 23.587 |
| OpenFOAM fork's alpha coefficients | 83.0454 | 105.105 | 31.681 | 23.587 |
| Rounded Tc/Pc printed in Liang's discussion | 82.9867 | 104.544 | 30.811 | 24.123 |
| Current NIST critical constants and acentric factors | 83.1656 | 105.251 | 31.699 | 23.606 |
| N2/O2=3.76 instead of 79/21 | 83.1177 | 105.226 | 31.718 | 23.586 |
| Paper reading | 83.3776 midpoint; 83.1487 centroid | 98.117 | 21.114 | 33.039 implied |

The table's density is evaluated at the measured Figure 4 phi=1.0001255;
the critical columns use exactly phi=1. These input choices remain difficult
to distinguish from the density image, but none approaches the Figure 2 pair.
The NIST variant's slightly smaller image residual is not evidence that Liang
used that variant, nor a reason to replace baseline inputs.

The rounded alternative takes H2 `(33 K, 12 atm)`, N2 `(126 K, 33 atm)`, and
O2 `(154 K, 50 atm)` directly from Liang's discussion. The modern variant uses
the official WebBook auxiliary metadata:

| Species | Tc, K | Pc, MPa | Acentric factor |
| --- | ---: | ---: | ---: |
| H2 | 33.145 | 1.2964 | -0.219 |
| O2 | 154.581 | 5.0430 | 0.0222 |
| N2 | 126.192 | 3.3958 | 0.0372 |

Official result pages and their retrieval hashes are preserved locally:
[hydrogen](https://webbook.nist.gov/cgi/fluid.cgi?Action=Load&ID=C1333740&Type=IsoBar&P=1&PUnit=MPa&TLow=298&THigh=298&TInc=1&TUnit=K&DUnit=kg%2Fm3&RefState=DEF#AdditionalFluidProperties),
[oxygen](https://webbook.nist.gov/cgi/fluid.cgi?Action=Load&ID=C7782447&Type=IsoBar&P=1&PUnit=MPa&TLow=298&THigh=298&TInc=1&TUnit=K&DUnit=kg%2Fm3&RefState=DEF#AdditionalFluidProperties),
[nitrogen](https://webbook.nist.gov/cgi/fluid.cgi?Action=Load&ID=C7727379&Type=IsoBar&P=1&PUnit=MPa&TLow=298&THigh=298&TInc=1&TUnit=K&DUnit=kg%2Fm3&RefState=DEF#AdditionalFluidProperties).
The mechanism molecular weights were held fixed in this sensitivity.

Soave's original article notes limitations for hydrogen-containing mixtures
and reports that effective critical constants did not improve the systems
examined. It does not supply a unique hydrogen correction applicable to
Liang's calculation. Selecting an effective constant or attraction correction
solely to match these figures would exceed the available evidence.
[Soave (1972), mixture discussion, page 1200](https://doi.org/10.1016/0009-2509(72)80096-4);
[primary text inspected](https://www.researchgate.net/publication/239154680_Equilibrium_Constants_From_a_Modified_Redlich-Kwong_Equation_of_State).

## Decision and evidence

Retain the current fresh-mixture EOS. Figure 4 density provides no useful lead
for correcting the nonideal flame-speed discrepancies by changing bulk density
or upstream temperature. This does not clear the energy, transport, kinetics,
or flame-convergence checks. Figure 2 remains an unresolved publication/input
consistency problem; it is not an input table consumed by the current flame EOS.

The ignored operator directory is
`state/liang-hydrogen-20261020/density-consistency/`, relative to the outer
realfluidfoam project. `check_density.py plan|apply` produces:
`case2-comparison.csv`, `conditional-inverses.csv`, `input-sensitivity.csv`,
`ideal-density-temperature.csv`, and `manifest.json`.
The manifest hashes every inlet profile, configuration, source-revision and
input receipt used. No flame was run and no coefficient was fitted or written
into production inputs.

Verification: 15 native-density parity checks passed, and four forward/inverse
checks recovered supplied a and b to relative error below 1e-11. Paper markers
were never interpolated. All 18 Case 1 samples fall within its extracted line
domain. The comparison does not introduce an acceptance tolerance.

| Evidence | SHA256 |
| --- | --- |
| `digitized/reference.json` | `a62b7930fd8c1e0cef978842ab5b49a21a832034eaab6328f92c10fd545cdf99` |
| `density-consistency/check_density.py` | `b24dc354c9adcc58686d0c2f139e7beabb4c9fd040d2a1f598036c308afac43b` |
| `density-consistency/case2-comparison.csv` | `1947e9ea6f289da58e2593de4554a3baca10c66a1c52f1909247950edcfd8d6f` |
| `density-consistency/conditional-inverses.csv` | `a64a48845219ca0c30866487b04f0e799db0d51aece3613af5b31bfd13371d7b` |
| `density-consistency/manifest.json` | `ae2efd9419c5f5c0b8b61a29e45f389dc8c3964c1723f90fb99bc47d46ba5eeb` |
