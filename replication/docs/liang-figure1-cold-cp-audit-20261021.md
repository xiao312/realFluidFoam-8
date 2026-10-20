# Figure 1: oxygen heat capacity below 200 K

21 October 2026, Asia/Shanghai. Local diagnostic tested; no production model
or job changed.

**Replacing extrapolated oxygen NASA Cp with a published 100–700 K Shomate
fit changes the Figure 1 conductivity by at most 0.131% over 100–200 K.**
It removes the Cp range extrapolation in this separate diagnostic, but does
not resolve the density-mapping or paper-comparison discrepancies.

## Reference input

The official NIST WebBook oxygen page supplies the gas-phase Shomate fit

```text
Cp° = A + B t + C t² + D t³ + E/t²     [J/(mol K)]
t = T/1000
A = 31.32234    B = -20.23531    C = 57.86644
D = -36.50624   E = -0.007374
valid range: 100–700 K.
```

The page attributes this fit to Chase's 1998 NIST-JANAF compilation, with
data reviewed in March 1977 and a new parameter fit in January 2009. Its
listed range includes the entire cold diagnostic. The page does not assign
an uncertainty to this Cp fit.
[Official NIST oxygen gas-phase heat capacity](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7782447&Mask=1#Thermo-Gas).

The existing author dictionary specifies NASA Cp validity from 200 K. Its
low-temperature polynomial is

```text
Cp°/R = 3.78246 - 0.00299673 T + 9.8473e-6 T²
        - 9.6813e-9 T³ + 3.24373e-12 T⁴.
```

This is the exact rounded polynomial used by property job `124887485`,
not a replacement taken from a newer GRI file. Its dictionary hash matches
the job receipt. The native CSV explicitly marks `T<200 K` as extrapolated.

Shomate supplies ideal-gas Cp for the internal-mode term. The dense-fluid
Cp in the 100-atm WebBook fluid table is a different quantity and is not
substituted. The physical oxygen state can be dense while this transport
model still uses an ideal-gas internal-mode heat capacity.

## Frozen-state calculation

All 101 native states from 100 through 200 K are reused. Temperature,
100-atm pressure, SRK density, molar volume, critical inputs, molecular
weight, conformal factors, mapped reference viscosity and reference
conductivity remain fixed.

For pure oxygen, the harmonic internal-mode mixture expression in
`ElyHanley.H` reduces exactly to

\[
\lambda_{\rm int}
 =\frac{1.32\mu^\star R}{W}
   \left(\frac{C_p^\circ}{R}-2.5\right).
\]

Here \(\mu^\star\) is the model's mapped dilute reference viscosity,
not the dense oxygen viscosity. Both Cp inputs stay above \(2.5R\), so
the implementation's nonnegative internal-mode clamp is inactive.
The translational contribution has no Cp dependence at frozen state.
Consequently,

\[
\Delta\lambda
 =\frac{1.32\mu^\star}{W}\Delta C_p^\circ,
\]

using J/(kmol K) for Cp and kg/kmol for W. This is the exact finite
change for this pure-fluid diagnostic, not a first-order approximation.
The absolute change is identical for the molar-consistent and mass-density
shortcut variants because they differ only in the other contribution.

The independent Python evaluation reproduces the native molar-consistent
conductivity within `4.28e-13` relative across these states. Re-evaluating
the full conductivity after the Cp substitution agrees with the analytical
change to better than `2e-16 W/(m K)`.

## Measured change

Cp is in J/(mol K); conductivity is in W/(m K). Percentages are
`100*(Shomate-based / original - 1)`.

| T, K | Original Cp | Shomate Cp | Original conductivity | Cp-substituted conductivity | Conductivity change, % |
|---:|---:|---:|---:|---:|---:|
| 100 | 29.69845 | 29.10357 | 0.14278716 | 0.14260083 | -0.13050 |
| 125 | 29.46326 | 29.15385 | 0.10072262 | 0.10060255 | -0.11922 |
| 150 | 29.29586 | 29.13810 | 0.06733479 | 0.06726213 | -0.10790 |
| 175 | 29.19010 | 29.11689 | 0.04055137 | 0.04051242 | -0.09605 |
| 200 | 29.14008 | 29.11354 | 0.03204618 | 0.03203019 | -0.04989 |

The largest Cp change is -2.0031%, at 100 K. Its conductivity effect is
small because the original internal-mode contribution there is only
`0.00279155 W/(m K)` of the total `0.14278716 W/(m K)`.
The largest absolute conductivity change is `1.86333e-4 W/(m K)`.
For the mass-density shortcut, the largest relative change anywhere on
this grid is 0.04584%.

At the four retained cold triangle centers, linear interpolation on the
same 1 K grid gives:

| Paper marker T, K | Original prediction | Cp-substituted prediction | Paper reading interval |
|---:|---:|---:|---:|
| 156.43 | 0.05968206 | 0.05961924 | 0.072857–0.074913 |
| 171.85 | 0.04318116 | 0.04313860 | 0.050927–0.053064 |
| 184.14 | 0.03541313 | 0.03538370 | 0.039575–0.041734 |
| 198.21 | 0.03224538 | 0.03222806 | 0.030232–0.032370 |

These intervals are the existing image-reading bounds, not experimental
uncertainties. The Cp change is much smaller than their widths. The table
evaluates nominal marker temperatures; it does not replace the earlier
two-dimensional temperature/value interval comparison.

## Consequence for Figure 1

A separately labelled Shomate-Cp cold curve can be plotted without
extrapolating the Cp correlation. The other model limitations remain,
including the SRK/reference-fluid hybrid and density-mapping ambiguity.
The original native curve must retain its extrapolation label.

This result rules out the tested Cp substitution as an explanation for the
large cold conductivity discrepancy. It does not validate the complete
Ely–Hanley model at these states or identify Liang's heat-capacity input.
No automatic splice at 200 K is proposed: the two fits differ slightly
there even though both include that boundary.

## Reproduction

Ignored evidence directory:

```text
state/liang-hydrogen-20261020/figure1-cp-diagnostic/
```

The versioned entry point is
[`cold_cp_probe.py`](../development/liang-properties/cold_cp_probe.py).
It takes `plan|apply`, `--native OXYGEN.csv`, `--species DICTIONARY`,
`--readings PAPER_READINGS.csv` and `--output NEW_DIRECTORY`.
Both paths passed. `versioned-001/` holds the 101-row CSV, cold-marker
CSV and summary. The summary pins all input hashes, script hash, source
coefficients and validity range.

Its numeric CSV matches the original scratch calculation in `results-001/`
byte for byte, SHA-256
`6b8417589d3b0fe1a6a85ab700b3000a051dc878130bf9462c6703daa0accc4f`.

Use the project's existing analysis virtual environment. The diagnostic
imports the existing property mathematics read-only and never changes the
EOS, library, case inputs or historical native CSV.
