# Peng–Robinson equation of state

This template supplies density and departure properties to the real-fluid
thermodynamic packages. It does not implement the chemistry or transport models.
`rfSpecie` supplies critical properties, molecular weight and the gas constant.
The mixture package supplies the mixed `b_`, `coef1_`, `coef2_` and `coef3_` values.
Inputs are pressure in Pa and temperature in K. Specific outputs use kg units.
There are no host settings, credentials, network calls or file writes.

## Heat-capacity difference

For molar volume `v`, the PR pressure law is

```text
p = R T/(v-b) - a(T)/(v²+2bv-b²)
Cp-Cv = -T (∂p/∂T at v)² / (∂p/∂v at T) / W
```

Here `W` converts molar to specific heat capacity. With `Z=pv/(RT)` and
`B=bp/(RT)`, the reduced volume expression is

```text
M = (Z²+2BZ-B²)/(Z-B).
```

Both `Cp()` and `CpMCv()` must use this expression. The former was corrected
previously; the latter retained the SRK expression `(Z²+BZ)/(Z-B)`.
The inconsistent denominator produced negative `Cv` and also `Cv>Cp` at stable
single-phase states. `HtoEthermo.H` computes `Cv` as `Cp-CpMCv`.

The [focused regression](../../../../../replication/validation/pr-cpmcv/README.md)
compares this actual source body with independent numerical pressure derivatives.
Run from the repository root:

```sh
node replication/validation/pr-cpmcv/check.mjs
```

Expected result: all derivative identities pass and the historical expression
fails the negative control. This local check does not qualify a compiled library.
The regression guide contains the required isolated build and four-fluid checks.
