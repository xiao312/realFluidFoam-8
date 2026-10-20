# Methane conservative-species controls

The conservative equations improve numerical balances, but do not establish
Liang's nonideal model. These controls change the species discretization
and retain the same total-enthalpy equation, thermodynamics, transport and
chemistry. No physical model coefficient or comparison threshold is fitted.

## Source and verification

Source `6c9cc9b7d5090a947c0f73ad8e2789c9c55110f1`, methane build `125102147`,
binary `7cb1bd1cf59a7d116225e1c6fc41dcfa056ba3a339284eceac361cf1d1675cff`.
The shared conservative class retains its hydrogen numerical expressions.
Hydrogen compatibility build `125102357` passes the full existing checks.

The [qualification record](liang-methane-conservation-qualification-20261021.json)
contains kernel, alpha, Takahashi, Soret and 16 manufactured residual checks.
The global fixture identity error is 1.11e-16. Three invalid option
combinations reject before creating output. Independent copies with altered
species or energy fluxes fail the corresponding audit; captured data remain unchanged.

## Matched phi=1.40 controls

All six attempts use 100 atm, 298 K, identical physical files and the same
steady Cantera guess. Default/tight steady tolerances are 1e-5/1e-11 and
1e-7/1e-13. Wall limits are 45/55 minutes, with one CPU and 3072 MiB.
These steady guesses do not initialize or restart any CFD calculation.

| Case | Default job / speed (cm/s) | Tight job / speed (cm/s) | Tight audit |
| --- | --- | --- | --- |
| 1 | 125102175 / 6.108900523 | 125102244 / 6.109791524 | All checks pass |
| 4 | 125102176 / 5.759065845 | 125102245 / 5.759754637 | All checks pass |
| 5 | 125102177 / 5.716013153 | 125102246 / TIMEOUT | scheduler_TIMEOUT |

Default native-check failures are retained explicitly:

- Case 1, job 125102175: elemental_flux, energy_flux.
- Case 4, job 125102176: elemental_flux.
- Case 5, job 125102177: elemental_flux.

All available native residual/flux identities and physical balance metrics
are retained in the [complete record](liang-methane-conservation-results-20261021.json).
Only tight results passing every native check are added to the conservative overlay.

## Other rich operating conditions

Six tight attempts extend Cases 1/4/5 to phi=1.30 and 1.35. At each condition,
all three use the same completed Case 4 profile as a steady numerical guess.
Only its CSV columns are projected; no state is clipped, normalized or rescaled.
Physical input hashes match the earlier campaign. Each attempt has a 30-minute
limit, one CPU and 3072 MiB.

| phi | Case | Job | Scheduler outcome | Speed (cm/s) | Native audit |
| --- | --- | --- | --- | --- | --- |
| 1.30 | 1 | 125102670 | COMPLETED (00:12:37) | 6.607106753 | All checks pass |
| 1.30 | 4 | 125102671 | TIMEOUT (00:30:21) | Unavailable | No completed output |
| 1.30 | 5 | 125102672 | TIMEOUT (00:30:21) | Unavailable | No completed output |
| 1.35 | 1 | 125102674 | COMPLETED (00:13:48) | 6.354540172 | All checks pass |
| 1.35 | 4 | 125102675 | TIMEOUT (00:30:19) | Unavailable | No completed output |
| 1.35 | 5 | 125102676 | TIMEOUT (00:30:16) | Unavailable | No completed output |

The [rich-condition record](liang-methane-conservation-rich-20261021.json)
retains all terminal outcomes, guess origins, numerical settings, comparisons
and native audit hashes. Failed or incomplete attempts are not plotted as qualified data.
Numerical conservation, grid stability and paper agreement remain separate requirements.

The separate [phi=1.10 Soret tolerance controls](liang-methane-tolerance-controls-20261021.md)
retain the six completed off/on pairs and their native flux checks.
Their largest speed change on tightening convergence is 0.0132%.
Earlier [rich Soret controls](liang-soret-results-20261021.md) remain a
separate physical-model sensitivity; their stage gaps are not recovered.
