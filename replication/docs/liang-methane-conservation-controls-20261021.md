# Methane conservative-species controls

These controls test the remaining discretization difference after the
total-enthalpy update. They retain methane/air at phi=1.40, 100 atm and
298 K, original physical inputs, transport, chemistry and steady guesses.
They apply the same conservative species divergence already qualified
in the hydrogen campaign. No model coefficient is changed.

## Source and verification

Source `6c9cc9b7d5090a947c0f73ad8e2789c9c55110f1`, build `125102147`,
executable SHA-256
`7cb1bd1cf59a7d116225e1c6fc41dcfa056ba3a339284eceac361cf1d1675cff`.
The shared class retains every numerical expression from its hydrogen
implementation. A compatibility alias preserves the hydrogen interface.

The [qualification record](liang-methane-conservation-qualification-20261021.json)
contains the kernel, alpha, Takahashi, Soret and 16 manufactured residual checks.
The conservative fixture's global species identity error is `1.11e-16`.
Three invalid option combinations fail before an output directory is created.
Independent copies with altered species or energy fluxes both fail the
corresponding native audit. The original captured fields remain unchanged.

## Matched campaigns

| Case | Default job | Tight job |
| --- | ---: | ---: |
| 1 | 125102175 | 125102244 |
| 4 | 125102176 | 125102245 |
| 5 | 125102177 | 125102246 |

Defaults use steady `rtol=1e-5`, `atol=1e-11`; tight controls use
`1e-7`, `1e-13`. Every job has one CPU and 3072 MiB.
Default/tight wall limits are 45/55 minutes. These are steady Cantera
calculations, with no transient CFD restart.

The first default Case 1 run completed at 6.108901 cm/s.
Every native residual/flux identity passes, but convergence checks retain
two failures: maximum active-element span `3.00e-6` versus `1e-6`, and
energy-flux span 0.0544 K equivalent versus 0.05 K.
The tighter pair tests the same issue seen in the earlier hydrogen pilots.
No failed default point is promoted to a qualified conservative overlay.

The existing numerical limits remain unchanged. Native conservation, grid
stability and paper-point agreement are separate requirements.
