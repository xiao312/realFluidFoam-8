# Liang Figure 2: critical-point audit

Owner decision, 19 October 2026: defer this discrepancy and return to the
flame-speed campaign. Preserve the failed comparison and audit; do not fit
physical coefficients to force agreement. This is not scientific acceptance.

19 October 2026. This audit narrows the disagreement but does not reproduce
Liang's Figure 2. No reacting solver, library coefficient, or running job changed.

The independent SRK calculation agrees with all 282 native probe states to
within 2.0e-13 in temperature [K] and pressure [atm]. Numerical pressure
derivatives give the same critical points within 5.5e-7 K and atm. The published
temperature/pressure pairs imply a different mixture covolume, including the
opposite composition trend. Ordinary input rounding does not explain this.

## Calculation order

The pure-species critical constants and the mixture critical point are different
quantities. The former are database inputs. The latter are calculated outputs.

1. Read each species' critical temperature `Tci`, critical pressure `Pci`, and
   acentric factor `omega_i`. The author dictionary stores `Pci` in MPa; convert
   to Pa. This independent audit uses mol, whereas OpenFOAM uses kmol.
2. Calculate the temperature-independent species parameters:
   `bi = 0.08664 R Tci/Pci`, `aci = 0.42747 (R Tci)^2/Pci`,
   `si = 0.48508 + 1.5517 omega_i - 0.15613 omega_i^2`.
3. Specify the unburned mole fractions, then calculate `b = sum(Xi bi)`.
   For hydrogen use mole amounts `(phi, 0.5, 0.5*79/21)`.
   For methane use `(phi, 2, 2*79/21)`. Normalize each vector.
4. Form `ai(T) = aci [1 + si(1 - sqrt(T/Tci))]^2` and
   `a(T) = sum_i sum_j Xi Xj sqrt(ai(T) aj(T))`.
   Binary interaction coefficients are zero, as in Liang's printed equation.
5. Solve both pressure-inflection conditions at fixed composition:
   `dp/dv = 0` and `d2p/dv2 = 0`.
6. Evaluate pressure at the resulting temperature and volume.

The full pressure equation is `p = RT/(v-b) - a(T)/[v(v+b)]`, with molar volume
`v` in m3/mol and `R = 8.31446261815324 J/(mol K)` in this audit.

Eliminating the pressure derivatives gives
`vc = q b`, where `q = 1 + cbrt(2) + cbrt(4) = 3.8473221019`, and
`a(Tc)/(R Tc b) = K = 4.9339624518`.
Thus `vc` can be calculated immediately after `b`.

On the positive Soave square-root branch, define
`A = sum Xi sqrt(aci) (1 + si)` and
`C = sum Xi sqrt(aci) si/sqrt(Tci)`. Then `a(T) = (A-C sqrt(T))^2` and

```
Tc = [A / (C + sqrt(K R b))]^2
Pc = R Tc/(vc-b) - a(Tc)/[vc(vc+b)]
   = 0.08664034996495773 R Tc/b
```

The slightly different decimal constants in the input coefficients and exact
inflection identity explain small pure-fluid recovery errors, not Figure 2.
There is no circular use of an unknown mixture Tc/Pc to initialize its b.
The Chung transport pseudo-critical `TcM` in the library is a separate quantity;
it must not replace this EOS inflection calculation.

## Inputs and worked results

| Species | Tci (K) | Pci (MPa) | omega | bi (cm3/mol) |
|---|---:|---:|---:|---:|
| H2 | 33.18 | 1.300 | -0.216 | 18.38593 |
| O2 | 154.58 | 5.043 | 0.025 | 22.08091 |
| N2 | 126.19 | 3.398 | 0.039 | 26.75187 |
| CH4 | 190.60 | 4.610 | 0.011 | 29.78342 |

At phi=1, `(Xfuel, XO2, XN2)` is `(0.295775, 0.147887, 0.556338)` for
H2/air and `(0.095023, 0.190045, 0.714932)` for CH4/air.

| Mixture | b (cm3/mol) | vc (cm3/mol) | Tc (K) | Pc (atm) |
|---|---:|---:|---:|---:|
| H2/air | 23.58666 | 90.74549 | 105.10548 | 31.68083 |
| CH4/air | 26.15224 | 100.61611 | 136.64610 | 37.14720 |

## Tests and findings

The original pressure comparison fails with differences +10.5672 atm for H2/air
and -3.4631 atm for CH4/air at phi=1. The audit's `--require-paper-match` option
reproduces that failure and saves the evidence before returning a nonzero code.

1. **Figure extraction:** checked the rendered original, curve styles, axis
   endpoints, and all eleven red pressure ticks. Re-extracted vector curves
   over phi=0.6-1.9. The phi=1 values agree with the prior extraction.
   Assigned reading tolerances remain 0.1 K and 0.05 atm.
2. **Coefficient construction:** inspected the pure-SRK constructor and the
   registered `SRKchungKineticMixture` implementation. It converts Y to normalized
   X, sums b linearly, and constructs the same expanded geometric attraction.
   The independent mol-SI formula reproduces every native probe Tc/Pc value.
   This is a source audit, not a new compiled cell-mixture runtime test.
3. **Critical solver:** used direct pairwise ai(T) mixing and five-point numerical
   pressure derivatives, rather than the native expanded polynomial or closed
   critical formula. Six fuel/phi states, each at three derivative step sizes,
   pass. The maximum difference from the closed solution is 5.44e-7 K or atm.
4. **Input/model sensitivity:** the table below tests one choice at a time.
   No tested choice matches both published temperature and pressure pairs.

| Variant, phi=1 | H2 Tc (K) | H2 Pc (atm) | CH4 Tc (K) | CH4 Pc (atm) |
|---|---:|---:|---:|---:|
| Native coefficients | 105.105 | 31.681 | 136.646 | 37.147 |
| Paper's rounded major-species constants | 104.415 | 30.773 | 136.240 | 36.747 |
| N2/O2=3.76 instead of 79/21 | 105.099 | 31.680 | 136.650 | 37.149 |
| 0.48 + 1.574 omega - 0.176 omega2 alpha slope | 105.232 | 31.719 | 136.643 | 37.146 |
| Constant attraction, alpha=1 | 98.781 | 29.774 | 136.742 | 37.173 |
| Mass fractions incorrectly used as X | 129.460 | 36.156 | 134.957 | 37.058 |
| X incorrectly converted again as Y | 48.226 | 17.622 | 139.774 | 37.513 |
| Force b from measured Vc/q | 114.810 | 39.332 | 149.709 | 46.911 |
| Paper vector curves | 98.117 | 21.114 | 138.193 | 40.610 |

The alpha=1 hydrogen temperature is close to the paper. Its pressure remains
8.66 atm too high. That coincidence does not identify the authors' algorithm.
The rounded-constant test uses printed values as a sensitivity experiment;
they are not the authors' unavailable numerical input deck.

## Stronger consistency test

Every fixed-composition SRK inflection must satisfy
`b = 0.08664034996495773 R Tc/Pc`. Applying this identity to the paper curves:

| Mixture | phi | b from our inputs | b implied by paper Tc/Pc |
|---|---:|---:|---:|
| H2/air | 0.6 | 24.285 | 29.864 |
| H2/air | 1.0 | 23.587 | 33.039 |
| H2/air | 1.9 | 22.493 | 40.988 |
| CH4/air | 0.6 | 26.009 | 24.655 |
| CH4/air | 1.0 | 26.152 | 24.193 |
| CH4/air | 1.9 | 26.438 | 23.354 |

All b values are cm3/mol. For H2/O2/N2, any normalized linear mixture must lie
between 18.386 and 26.752. Every extracted H2/air pair exceeds that upper bound.
Changing the air ratio, equivalence ratio, or alpha function alone cannot remove
this contradiction for the pinned pure-species data.

Both fuels also show the opposite b trend. Adding H2 must lower b because its
bi is below air's. Adding CH4 must raise b because its bi is above air's.
The paper's paired Tc/Pc curves imply the reverse in both cases.

As a further diagnostic, fitting arbitrary *constant* fuel/air b values to the
inferred curves gives different air values: 19.880 for H2/air versus 25.353 for
CH4/air. The H2 fit still has a maximum residual of 0.812 cm3/mol. This inverse
fit checks compatibility only; no fitted value enters a model or case.

## Decision and remaining uncertainty

No numerical or coefficient-assembly correction was identified in the tested
SRK path. Keep its physical parameters unchanged. The Figure 2 match remains
failed, while the independent equation checks pass.

The evidence points to an unreported input/implementation difference, a different
critical-point definition, or a figure/label issue. It does not establish which
occurred in the authors' code. A full composition-stability critical calculation
would be a different definition; this audit does not claim to implement it.

Requesting the authors' Figure 2 input deck, a(T)/b mixing routine, critical-point
routine, and raw Tc/Pc arrays would resolve the remaining ambiguity most directly.
No message was sent. Until those are available, Figure 2 should remain a reported
disagreement, not a target for fitting our EOS. Independent property validation
can proceed with the documented SRK equations and fixed inputs.

## Reproduction and identity

The [machine-readable record](liang-critical-audit-20261019.json) contains input
hashes, the native source/library identity, summaries, and artifact hashes.
The source base is `a6b3f75c2ae17895b61b1aba530030fe332b1f3a`.
Native data are from job 124887485, source
`e208396bdba48592aacbf6bb9a1c41b8eca3d9bb`, library build 124657926.

From the checkout root, with NumPy and PyMuPDF installed:

```sh
python -B replication/development/liang-properties/test_critical.py
python -B replication/development/liang-properties/critical_audit.py plan \
  --species replication/validation/flames/author-counterflow/original/GRI30/constant/thermo.inputData_GRI \
  --native /PROJECT/state/liang-properties-20261019/job-124887485/properties/critical.csv \
  --paper /LOCAL/1-s2.0-S1540748918302530-main.pdf \
  --output /PROJECT/state/liang-critical-audit-new
```

Repeat with `apply`. Add `--require-paper-match` to reproduce the scientific
failure. The ordinary audit completes with `scientific_acceptance=false`.
Expected software check: four tests pass, 282 native states agree, and 18
numerical inflection solutions agree. `git diff --check` must pass.

Local evidence: `state/liang-critical-audit-20261019-v1/` under the project root.
Diagnostic image: `output/liang-critical-audit-20261019/critical-covolume-check.png`.
It supplements the existing Figure 2 overlay; it is not a style replica.

Primary source: [Liang, Li and Law, PCI 37 (2019), 1733-1739](https://doi.org/10.1016/j.proci.2018.06.070),
Eq.(1), Eq.(2), and Figure 2. The local PDF was inspected visually.
The [author's 2017 research abstract](https://mae.princeton.edu/document/1897)
does not supply the missing coefficients or critical-point routine.
