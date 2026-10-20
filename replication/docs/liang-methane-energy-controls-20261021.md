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

## Completed original-alpha controls

All three jobs completed and pass the existing numerical flame screen.
The [result and flux record](liang-methane-energy-results-20261021.json)
retains observed source, executable, input and profile hashes.

| Case | Stock temperature equation, cm/s | Total enthalpy, cm/s | Paper, cm/s |
| --- | ---: | ---: | ---: |
| 1 | 6.116619 | 6.121254 | 6.116682 |
| 4 | 5.807094 | 5.771139 | 5.795719 |
| 5 | 5.762399 | 5.727276 | 5.642738 |

Cases 1/4 pass the unchanged paper-point screen. Case 5 remains 1.498% high,
outside its 0.071427 cm/s allowance by a 0.084538 cm/s error.
The Case 4–5 separation changes from 0.044695 to 0.043863 cm/s.
Liang's separation is 0.152981 cm/s. Thus this energy change does not
explain the missing diffusion effect.

The endpoint enthalpy change divided by outlet Cp decreases from
2.152/2.122 K to −0.060/−0.058 K for Cases 4/5.
Frozen-profile audit job `125102007` reduces their reconstructed upwind
partial-enthalpy flux spans from 22486/22367 to 610/584 W/m².
This independently supports improved energy balance; it does not bound
the remaining speed error or replace an exact native residual.
Legacy pure-species controls must use their own pure-species flux column:
their larger partial-enthalpy reconstruction is a different equation.

The next declared numerical control applies the already-tested conservative
species divergence together with total enthalpy. It changes no mechanism,
thermodynamic parameter or transport coefficient. Native mass, element and
energy exports will test its conservation before interpreting the speed.

## Completed historical smooth-alpha controls

The earlier smooth-alpha controls were recovered before creating another
smooth-alpha campaign. Their [completed record](liang-methane-legacy-energy-20261021.json)
supersedes the stale running status in the 20 October report.
Case 5 at phi=1.40 gives 5.727907 cm/s with partial diffusion enthalpy and
5.725730 cm/s with pure-species diffusion enthalpy. Both remain outside
the existing paper allowance, by errors of +1.509% and +1.471%.
These completed tests remove the need to repeat that pair.

The three current controls retain the original alpha expression. Its known
enthalpy jumps remain explicit in the [alpha audit](cantera-alpha-discontinuity-20261020.md).
Therefore their energy-equation effect must not be confused with the separate
effect of smoothing the thermodynamic model.
