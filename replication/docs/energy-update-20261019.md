# Species enthalpy correction — 19 October 2026

The isolated correction passes the runtime enthalpy test and parallel smoke test.
Job 124900963 is continuing the phi=1.10 ideal-gas flame from the same 50.018-us
checkpoint as the unchanged job 124885085. Its flame-speed effect is not yet known.
No production library or existing run was modified.

## Change and identity

Branch: `draft/energy-update`; run source: 34f879f5696a9b760a16897a6b3f48909f831ce5.
The shared accessor evaluates `composition.HE(i,p,T)` at the current flow state,
including boundary faces. It replaces the two solver reads of `thermo.hei(i)`:
initial field construction and the existing timestep-end property update. The
library's constructor-only cache remains unchanged. This experiment tests the
energy-diffusion consequences without rebuilding or modifying shared libraries.

Chemistry, SEULEX tolerances, transport models, PIMPLE placement and all other
equations remain unchanged. The solver/instrumentation source is unchanged from
the qualified tracking source 02de163, apart from this accessor and executable
name; later tracking changes are README/history analysis only. The native library
is still build 124657926. The independently named executable is
`rfEnergyReactingFoam`, SHA256:
`d07e6e45ae48aaf3a10ac1555c3630128ee03ed09bd58a50602fbd5722190304`.

The runtime input check confirmed identical checkpoint, original file SHA256
records, time controls and tracking anchors against job 124885085. The case is
100 atm, 298 K fresh methane/air, phi=1.10, 4 mm, 8000 cells, 8 MPI ranks, maxCo=0.1,
maximum timestep 50 ns, and endpoint 200 us. The scheduler limit is six hours.
That endpoint is a comparison checkpoint, not a convergence declaration.

## Verification

The eight-state test evaluates all 53 species in cells and boundary faces at the
original temperature, after +100 K and after a further -50 K. It compares the same
accessor used by the solver against direct scalar species HE at the actual p/T.

| Accessor | Samples | Failed comparisons | Maximum absolute error |
| --- | ---: | ---: | ---: |
| Unchanged thermo.hei cache | 1590 | 1060 | 2,062,192.4 J/kg |
| Current-state species HE | 1590 | 0 | 0 J/kg |

The initial-state comparisons also pass for the old accessor, confirming that
the test changes state rather than changing the enthalpy convention. The red
probe returns 1; the corrected probe returns 0. Both gates run before a flame.

A two-step parallel smoke reached 50.118 us. All 8000 cells have finite inspected
fields; maximum species-sum error is 1.2093e-12. Temperature ranges from 297.9985
to 2229.6607 K, pressure from 10132455.8 to 10132525.5 Pa, and density from 14.7645
to 112.5598 kg/m3. The full continuation then started from the original matching
checkpoint, not from the smoke endpoint. At 17:24 CST it had advanced past 51 us.

The first attempt, job 124900697, compiled successfully but stopped because the
wrapper invoked the probe through an unset PATH. No flame ran in that attempt.
Source 34f879f uses the explicit job-local probe path and passed the gates above.
Local checks covered Python compilation, Bash syntax and instrumentation anchors.

## Interpretation and next comparison

The test proves current-state species enthalpy reaches the corrected solver's
energy-diffusion terms. It does not prove that this defect explains the flame-speed
gap. Compare temperature- and OH-based speeds, thermal/species profiles and heat
release at equal simulation times, after the five-us fit window is populated.
Keep the existing native, stock reactingFoam and DeepFlame histories separate.
Stock/DeepFlame begin from the central-products initial condition; the native
diagnostic pair shares a 50-us restart. This distinction matters because the old
cache is initialized again on restart. A restart-independence check and an energy
balance check remain necessary before promoting the correction.

Raw evidence is retained under SCNet `jobs/124900963`, including
`legacy-probe.log`, `refreshed-probe.log`, `probe/*enthalpy.csv`,
`inputs-check.log`, `smoke-fields.json`, `solver-product.sha256` and the case
tracking/source histories. The parent diagnosis is
[the cross-solver record](solver-comparison-20261019.md).

At 17:29 CST the first valid tracking frame at 55.418 us gave 6.4270 cm/s (T) and
6.0450 cm/s (OH), versus 6.4220 and 6.0485 cm/s in the unchanged case at the same
time. Each median pools the two front sides at one frame only. This early near-
agreement does not establish the correction's later speed effect. The unchanged
baseline has completed 200.018 us: its last 5-us medians are 7.1258/7.2324 cm/s
(T/OH), compared with Cantera 7.4670 cm/s; steady convergence remains unaccepted.
