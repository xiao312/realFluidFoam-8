# Liang Figure 2: critical-point definition check

20 October 2026, Asia/Shanghai. Status: investigated; paper comparison failed.
The request to cover Liang Figures 1–8 reopens the discrepancy deferred on
19 October. This note supplements the [coefficient and extraction audit](liang-critical-audit-20261019.md).
No production EOS, transport coefficient, mechanism, or running job changed.

Changing from a fixed-composition pressure inflection to a mixture stability
calculation does **not** explain Figure 2. It brings the methane critical
pressure closer, but moves the hydrogen pressure much farther from the paper
and reverses its equivalence-ratio trend. There is no justified coefficient
correction from this check.

## What the paper actually defines

Liang Section 3 defines the Figure 2 points “as the inflection point in the
P-v diagram.” Together with its equations (1) and (2), this specifies the
pressure derivatives at fixed composition. The paper supplies no composition
Hessian, phase-equilibrium calculation, or alternative critical criterion.
[Liang, Li and Law, 2019](https://doi.org/10.1016/j.proci.2018.06.070).

This distinction is explicit in Liang's reference 10. Giovangigli et al.,
Section 5.2, separately study composition stability and fixed-composition
mechanical stability. They report that the latter's limiting points for their
H2/O2/N2 mixtures lie below 51 atm, while composition instabilities can remain
at 100 atm. Therefore a mechanically supercritical mixture need not be stable
against composition changes. Their paper does not license replacing Liang's
stated Figure 2 definition with the other calculation.
[Giovangigli, Matuszewski and Dupoirieux, 2011](https://doi.org/10.1080/13647830.2010.527016),
author preprint, Section 5.2, pages 19–20.

For a mixture, the Heidemann–Khalil conditions instead concern the Helmholtz
energy's quadratic and cubic variations with species mole amounts at fixed
temperature and volume. A zero eigenvalue and vanishing cubic variation give
local critical candidates; additional stability conditions are required.
[Heidemann and Khalil, 1980](https://doi.org/10.1002/aic.690260510);
[Eaton, NBS Technical Note 1313, 1988](https://nvlpubs.nist.gov/nistpubs/Legacy/TN/nbstechnicalnote1313.pdf).

## Independent calculation

The following calculation was derived from the same SRK pressure equation.
It is a diagnostic outside the production models. It uses the four stable
species constants from the author dictionary already pinned by the preceding
audit, 21/79 molar O2/N2 air, zero binary interaction parameters, and the
existing Soave coefficient. Fresh mixtures contain only fuel, O2, and N2;
radical critical constants and the hydrogen reaction mechanism cannot affect
this particular comparison.

For mole amounts `n_i`, total amount `N`, volume `V`, and a fixed temperature,
define

```text
B = sum(n_i b_i)
C = sum(n_i sqrt(a_i(T)))
```

An SRK Helmholtz energy, omitting terms linear in `n_i` that do not affect
second or higher composition derivatives, is

```text
A/(R T) =
    sum[n_i (ln(n_i/V) - 1)]
  - N ln(1 - B/V)
  - C²/(R T B) ln(1 + B/V).
```

Taking `-dA/dV` recovers
`p = N R T/(V-B) - C²/[V(V+B)]`.
This is the same mole-based SRK mixture used in the earlier inflection audit.

The diagnostic evaluates the analytical composition Hessian `Q` of `A/(RT)`.
To improve conditioning, it diagonalizes
`diag(sqrt(n_i)) Q diag(sqrt(n_i))`. Its smallest eigenvalue and the analytical
third directional derivative along the corresponding composition direction
are solved simultaneously for temperature and volume. No paper values enter
those equations or their coefficients.

The table gives the resulting local candidates. Other Hessian eigenvalues
are positive at all six roots. A global tangent-plane stability test and
fourth-order stability test were not implemented, so these results are not
claimed as qualified equilibrium critical loci. They are sufficient to test
whether this alternative definition plausibly removes both Figure 2 errors.

| Mixture | phi | Fixed-composition Tc (K) | Fixed-composition Pc (atm) | Composition candidate Tc (K) | Composition candidate Pc (atm) |
|---|---:|---:|---:|---:|---:|
| H2/air | 0.6 | 113.782 | 33.310 | 124.803 | 56.164 |
| H2/air | 1.0 | 105.105 | 31.681 | 120.287 | 68.823 |
| H2/air | 1.9 | 90.932 | 28.741 | 109.890 | 99.873 |
| CH4/air | 0.6 | 134.627 | 36.800 | 136.327 | 39.680 |
| CH4/air | 1.0 | 136.646 | 37.147 | 138.987 | 41.196 |
| CH4/air | 1.9 | 140.698 | 37.835 | 144.112 | 43.904 |

At phi=1 the digitized paper values are:

| Mixture | Paper Tc (K) | Paper Pc (atm) | Composition-candidate temperature error (K) | Composition-candidate pressure error (atm) |
|---|---:|---:|---:|---:|
| H2/air | 98.117 | 21.114 | +22.170 | +47.710 |
| CH4/air | 138.193 | 40.610 | +0.794 | +0.586 |

The methane improvement alone is misleading. Its remaining errors exceed the
prior reading tolerances, and hydrogen has both the wrong pressure magnitude
and the wrong trend. This is not evidence that the authors used this method.

Two simple alternative averaging diagnostics also fail at phi=1:

| Mixture | Mole-averaged Tci (K) | Mole-averaged Pci (atm) | Harmonic-averaged Pci (atm) |
|---|---:|---:|---:|
| H2/air | 102.879 | 29.812 | 23.466 |
| CH4/air | 137.706 | 37.758 | 36.730 |

These are only algebraic alternatives. They do not satisfy Liang's specified
pressure-inflection conditions, and none is adopted.

## Verification and limits

The analytical Hessian was compared with centered second differences of the
Helmholtz expression at six mixture states. Its maximum absolute component
error was `2.44e-6`. The analytical cubic derivative was checked against a
centered directional derivative of the Hessian; maximum absolute error was
`1.97e-8`. The scaled critical residuals were below `5e-15`.

The same composition solver was reduced to each pure fluid, H2, O2, N2, and
CH4. Its Tc and Pc agreed with the independent closed SRK inflection solution
within `5.90e-11` K or atm. These checks support the diagnostic implementation;
they do not establish global phase stability.

At 298 K and 100 atm, an additional 25 fresh-mixture states per fuel over
phi=0.6–3.0 have positive scaled composition Hessians. The minimum eigenvalues
were 0.97361 for H2/air and 0.93693 for CH4/air. This is a local stability
screen for those assumed upstream conditions, not a flash calculation or a
validation of every point in a flame.

The earlier consistency test still applies to the paper's stated inflection:

```text
Pc = 0.08664034996495773 R Tc / b
b  = sum(Xi bi)
```

At phi=1, the paper's H2/air pair implies `b=33.039 cm3/mol`, outside the
`18.386–26.752 cm3/mol` bounds of its three major species. Across composition,
the paper's implied covolume trend is opposite the linear mixing rule for
both fuels. This contradiction concerns the stated fixed-composition
definition; it must not be applied to the different composition-stability
candidate as if its critical volume identity were unchanged.

## Consequences for the campaign

1. Keep the verified SRK implementation and stable-species constants unchanged.
   Record Figure 2 as a failed paper comparison alongside the successful
   equation/derivative checks.
2. Keep the figure's critical-point calculation separate from the flame
   property evaluator. The current `SrkKernel.h` forms `a_i(T)` and `b_i` from
   pure-species inputs; it does not consume the Figure 2 mixture Tc/Pc curve.
   `StagedTransport.h` uses pure-species critical data and its explicitly
   selected pair or bulk Takahashi convention. Substituting Figure 2's
   inferred pressures would alter several models without justification.
3. Continue property and extended-Cantera flame comparisons, but do not call
   Figures 1–8 collectively passed while Figure 2 remains unresolved.
   The user made advancing to the extended OpenFOAM campaign conditional on
   the comparisons passing.
4. The next evidence that can resolve the discrepancy is the authors'
   Figure 2 input constants, composition arrays, SRK mixing routine,
   critical-point routine, or raw Tc/Pc output. A figure/label error or a
   different implementation remains possible; neither is established.
   No author contact was made.

## Evidence and reproduction

Source base inspected:
`1cd91674e7a99aae8e46b3ef0ca860905842d4cd`, `develop/reacting`.
All calculation files below are in the ignored operator state, not production
source. No HPC compute was needed.

Operator directory:
`state/liang-hydrogen-20261020/critical-sources/`.

| Artifact | SHA256 |
|---|---|
| `definition_probe.py` | `dcf4f8c63fadee8e0eaec46169c0409d2067324486075f2e0c0479142d608fa1` |
| `definition-probe.json` | `c7063b152bfc6ba833bc8b4a806a09e47bb411db733cbb561da233d167797232` |
| `nbs-tn-1313-1988.pdf` | `cf190592f3af5994054db4f48ec86fe8b90b96eb5dd8ee66bf881eff60e060ed` |
| Existing `giovangigli-2011-transcritical.pdf` | `0e93e18d404857f37b49044813dc5adf799781e87735e34f357a3b8171a256c5` |
| Liang owner-provided PDF | `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe` |

Local read-only diagnostic command:

```powershell
& 'D:/xiaok/work/FlamePilot/projects/realfluidfoam/state/analysis-venv/Scripts/python.exe' -B `
  'D:/xiaok/work/FlamePilot/projects/realfluidfoam/state/liang-hydrogen-20261020/critical-sources/definition_probe.py'
```

Expected result: six local critical candidates, six derivative checks, four
pure-species recovery checks, and 50 positive upstream Hessian checks, emitted
as JSON; no production files written.
