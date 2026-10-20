# Methane energy-equation controls

At 06:20 CST on 21 October, the completed phi=1.10 methane profiles show
nonzero feed-to-outlet enthalpy changes. Dividing each change by its outlet
heat capacity gives about 2.0–2.1 K for Cases 4/5, versus −0.10 to −0.26 K
for ideal Case 1. These are endpoint diagnostics, not corrected flame
temperatures or flame-speed error bounds.

The [original six controls](liang-methane-phi110-controls-20261021.json)
retain their native Soret and elemental checks. The largest relative
feed-to-outlet elemental change is 0.0434%. Neither check establishes
the omitted terms, if any, in the temperature equation.

## Declared test

Three new controls at phi=1.40 use the existing `total-enthalpy` option.
Cases 1, 4 and 5 retain their original mechanism, transport, physical
conditions, initial steady guess, grid-refinement rules and convergence
tolerances. The only equation change replaces the temperature residual
with the divergence of total enthalpy flux. This uses mixture enthalpy,
partial-species diffusion enthalpies and the native conductive flux.
Soret remains disabled in these controls.

The first hypothesis is that the nonideal temperature equation's
composition terms affect the Case 4–5 separation. A matched total-enthalpy
control tests that hypothesis without changing transport coefficients.
The second hypothesis is that this equation change shifts both cases
similarly and leaves the diffusion discrepancy unresolved.

Inspect the saved enthalpy endpoints and reconstructed energy flux first.
Then apply the existing numerical and paper-point screens, with no new
acceptance allowance. The ideal Case 1 control checks the numerical
effect of changing the energy discretization. A common speed shift does
not explain the missing Case 4–5 separation.

The qualified executable comes from source
`56e6bcba5cec8eeaf47a3ba366dec3b9ec26eb90`, build `125100350`.
Its SHA-256 is
`876243a6f686e1e475de3f3a01233da6302ddc7bd87b6a9a65c34abc2079ea0d`.
Each control has one CPU, 3072 MiB and a 75-minute cap.
Case 1, 4 and 5 jobs are `125101520`, `125101527` and `125101531`.
This is a steady Cantera diagnostic; it creates no CFD restart.
No new transport or thermodynamic coefficient is fitted.
