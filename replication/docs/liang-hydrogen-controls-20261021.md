# Hydrogen domain and thermal-diffusion controls

Domain length does not explain the tested hydrogen flame-speed discrepancy.
Thermal diffusion lowers the rich-flame predictions, but spoils the ideal
control and leaves Cases 4 and 5 above Liang. These are diagnostic results;
no production model changed and no new OpenFOAM campaign was released.

## Domain length and numerical initialization

Cases 1 and 3 were solved at phi = 1.0 and 1.4, 100 atm, 298 K, with
5, 10 and 20 mm domains. Source, executable, author-pair inputs and model
options were matched within each three-run group. All twelve completed
profiles passed the existing grid, mass-flow, species and thermodynamic checks.

| Case | phi | Speed span across domains | Relative span | Endpoint-temperature span |
|---|---:|---:|---:|---:|
| 1 | 1.0 | 0.0002792 cm/s | 0.0006618% | 0.002140 K |
| 1 | 1.4 | 6.58e−11 cm/s | 8.64e−11% | 1.85e−5 K |
| 3 | 1.0 | 1.48e−6 cm/s | 3.56e−6% | 1.03e−5 K |
| 3 | 1.4 | 3.35e−10 cm/s | 4.43e−10% | 9.38e−8 K |

These are observed spans, not asymptotic error estimates. They are much smaller
than the nonideal paper mismatch. Source is
`615f3f70d1e698cce22b87c719f05fdff8351b2c`, build `125083598`.
The [domain record](liang-hydrogen-domain-controls-20261021.json) includes
all job identities, input/output hashes and numerical checks.

The six ideal flames started from independent broad ideal-HP ramps. All six
first Case 3 attempts failed before a converged grid: Cantera's pseudo-time
step reached its `1e-16` lower bound. Their logs and hashes are retained.
Each Case 3 then converged from its same-phi, same-domain ideal steady profile.
These are numerical initial guesses for a steady Cantera solve, not CFD restarts.

## Matched thermal-diffusion controls

Build `125091444` completed in 79 seconds from
`ae10e5c32ea9e794a2ab584f1f03eb72af4788cd`.
Executable SHA-256:
`34d8c6f84618dbacd3b71820f92b5640904334999c391ba25a3382a4e0463e1f`.
All 15 independent collision fixtures and the pressure, ordinary-transport,
native-flux and parser qualification checks passed.
The four baseline physical input files are byte-identical to the earlier
author-pair inputs. The added collision sidecar has SHA-256
`349eb56bbcd097a7215c076eb6c96e5f2d934f932edd19d32dc3f63cefd363ad`.

Twenty-four matched runs completed: Cases 1/3/4/5, phi = 1.0/1.4, and thermal
diffusion off, Cantera 3.2, or the published manual formula with author A*/B*/C*
pairs. The [control record](liang-hydrogen-soret-controls-20261021.json) retains
each run's observed configuration, build, source and hashes.

At phi = 1.4, all twelve runs pass the existing numerical screens:

| Case | Liang, cm/s | Off, cm/s | Cantera 3.2 Soret | Manual / author pairs |
|---|---:|---:|---:|---:|
| 1 | 75.8281 | 76.1323 | 73.0306 | 72.4288 |
| 3 | 71.8145 | 75.5460 | 72.5227 | 71.9773 |
| 4 | 70.1841 | 76.3135 | 73.2771 | 72.7283 |
| 5 | 68.2739 | 75.3807 | 72.3404 | 71.7888 |

Both thermal closures pass the existing Case 3 speed screen at this point.
Both fail the ideal Case 1 screen and still fail Cases 4/5. The paper's
thermal-diffusion setting is unidentified. Selecting different settings by
case to obtain agreement would not reconstruct a documented model.

At phi = 1.0, the eight thermal-diffusion runs changed by 0.545–0.715% on the
last refinement, exceeding the existing 0.5% screen. Their values are not
qualified comparison points. A matched 24-run twofold-grid subdivision check
was submitted using the same executable and physical inputs; the initial
ledger identifies these pending jobs separately. No figure tolerance changed.

## Native flux and output precision

The shared strict methane audit remains unchanged. The hydrogen diagnostic
retains its failed residual checks instead of silently accepting them:
the largest initial rich-case coefficient-sum residual is `7.47e-10`, above
the strict `1e-10` limit. The largest thermal-flux reconstruction residual
is `1.18e-10`, also just above that limit.

The second residual is accounted for by decimal output precision. Both writers
save 16 significant digits; subtracting adjacent coordinates on subnanometre
cells amplifies that rounding. An independent interval calculation bounds every
thermal-flux reconstruction residual in all sixteen on-runs. A 100 ppm injected
thermal-flux error lies outside the bound and is detected by the regression
check. This explains the output arithmetic; it does not waive the strict audit.

For the first residual, Cantera 3.2's `Flow1D::setGasAtMidpoint` uses
`setMassFractions_NoNorm`. Its `MixTransport::getThermalDiffCoeffs` subtracts
`Y_k * norm` from each unprojected coefficient. Thus the remaining sum is
`norm * (1 - sum(Y))`, up to floating-point error. The maximum observed
face-composition sum error is `8.92e-10`, at the same face as the largest
coefficient-sum residual. The manual closure normalizes its transport
composition and closes near machine precision.
This source inspection explains why exact zero is not guaranteed; the current
offline probe does not independently reconstruct the unprojected native `norm`.
[Cantera 3.2 Flow1D](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp),
[MixTransport](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/MixTransport.cpp).

These residuals are far too small to account for percent-level speed errors.
The reported strict failures remain visible, and no solver coefficient,
normalization rule, scientific tolerance or baseline was changed to remove them.

## Reproduction

From `replication/development/liang-hydrogen`, run:

```sh
python -B compare_domains.py plan DOMAIN_MANIFEST domain-report
python -B compare_domains.py apply DOMAIN_MANIFEST domain-report
python -B analyze_soret.py plan RICH_MANIFEST REFERENCE_JSON soret-report
python -B analyze_soret.py apply RICH_MANIFEST REFERENCE_JSON soret-report
python -B soret_roundtrip.py plan ALL_SORET_MANIFEST roundtrip.json
python -B soret_roundtrip.py apply ALL_SORET_MANIFEST roundtrip.json
python -B test_soret_roundtrip.py ALL_SORET_MANIFEST new-fixture-directory
```

The ordinary methane six-run analyzer was rerun after exposing its inspection
helper: all original strict checks still pass, with unchanged measured results.
All analyses use collected local snapshots and make no remote writes.
