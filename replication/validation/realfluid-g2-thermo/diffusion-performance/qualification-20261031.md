# Full-SRK unused-diffusivity qualification, 31 October 2026

The opt-in passed numerical equivalence checks in Slurm job **126418954**.
All six physical property/inversion pairs produced identical output bytes.
The fresh source-disabled CFD pair produced identical recorded scalar/vector
fields and integrated energy histories. The optimization is qualified for this
bounded FGM/Fourier path; source-enabled split integration and G2 flame physics
still require their own checks. No paper comparison or scientific acceptance
is implied.

The scheduler reports COMPLETED, exit 0:0, 1194 s and two CPUs. TotalCPU was
24:53.060; batch MaxRSS was 2532164 K. The payload completed at
2026-10-30T19:58:21Z (03:58:21 Shanghai), and terminal accounting was checked at
20:00:07Z. Container staging/checking took 336 s before qualification execution.
The basic library built in 154 s and reactionThermo in 478 s. The other thirteen
libraries were retained with verified hashes; chemistry was not rebuilt.

The science candidate was `ce76de25f24cfd8572b04324b192ae9544a5dbc9`, package
`2459eeb50a0dd2372bc58a83c785ee345c9c74d3`, using the qualified OF8/GCC11.2
environment `f46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793`.
All 1096 selected Git blobs were checked before recorded compiler-option
adjustments. The complete fifteen-library build receipt has SHA256
`21958f5e4bc7c8ca9544a8c013d978d2795c476a9e88d87766ded5a308fb7b6e`.

| Product | Bytes | SHA256 |
|---|---:|---|
| libfluidThermophysicalModels.so | 11993512 | bc9a64839eda0903d32a84c4fbf31374ee6bb05c8a0eb301b1decad6e225537b |
| libreactionThermophysicalModels.so | 38584920 | 122dd8d1305199245780b6c726e8e3894ed469de0503d72be5a80a1ad5ad834c |
| reactingFoamSolveZ | 1009104 | 337a6cd8305b0ca2fa549226acf450da258fa83a2a766090831e5864d78c39cd |
| realFluidG2ThermoProbe | 218944 | 824605bc4977f67f05a090047fef5746bb13d5561b295d6606dfaa4049c1fac2 |

Each property timing covers twenty unchanged-state thermo corrections on 128
cells. These are measured single-run timings, not an uncertainty-qualified
benchmark. Density, Cp, Cv, Hs, Ha, viscosity, conductivity, alpha, recovered T
and the four enthalpy inversions were identical within each pair (maximum
recorded relative error zero; configured equivalence limit 1e-12).

| Physical state | Baseline seconds | Opt-in seconds | Correction speedup |
|---|---:|---:|---:|
| Pure oxygen | 7.0465 | 1.7498 | 4.027 |
| Pure methane | 7.6342 | 1.6938 | 4.507 |
| Unburnt mixture | 7.3018 | 1.7098 | 4.271 |
| Reacted mixture | 8.0057 | 1.7325 | 4.621 |
| Reacted mixture, 0.9 reference pressure | 7.8236 | 1.7121 | 4.570 |
| Reacted mixture, 1.1 reference pressure | 8.1338 | 1.7567 | 4.630 |

All five negative controls failed with the intended error: incompatible
transport, incompatible combustion, mutable runtime configuration, internal
Dimix access and boundary Dimix access. No missing field was silently replaced
with zero diffusivity.

The CFD pair used 48 periodic cells, actual cold-table compositions at eta=0.8,
Z=0.2+0.005*sin(2*pi*x/L), initial p=5.61 MPa and velocity 1 m/s. Full-SRK Ha
was independently initialized in each time-zero case and its hashes matched.
Both executed twenty 1 ns steps with progress source explicitly disabled.
All 53 species, T/p/rho/h/Ha/Z/C/U at four written times and all energy-state,
source and bounds records had zero recorded pair difference. Each retained
11,568 table lookups, zero corrections, relative mass drift 1.78e-15 and relative
total-energy drift 8.91e-15. Initial mean T was 2964.2203 K. This short test
qualifies equivalence during transport; it is not a resolved flame transient.

OF8's integer-second ClockTime reported total runtime 9 to 7 s and the interval
from first completed step to final step 4 to 2 s. Those coarse timings suggest
an advancing-step improvement but cannot support a precise CFD speedup claim.
The property timings provide the more precise measurement of the changed path.

Durable receipts remain under the admitted trial's
`runs/codex-agent/results/of8-unused-diffusion-r1` and the runtime under
`runs/codex-agent/build/of8-unused-diffusion-r1`. Small local receipt copies are
in the operator workspace's `state/forge-direct-20261030/results/diffusion-performance-r1`.
Use `parity-result.json`, `negative-controls.json`, `cfd-parity-result.json` and
`build-qualification.json` together; the property receipt alone deliberately
does not assert later CFD/negative-control qualification.

The next integrated allocation can reuse this runtime without rebuilding its
libraries. Add an otherwise identical source-enabled split pair, starting both
cases at zero with explicit Fourier/absolute-enthalpy/fgmTable settings and the
same table. Compare evolving composition, density, temperature and Ha as well
as integrated source and energy. The current result does not authorize a change
to Takahashi diffusion, a species cutoff or a different turbulence model.
