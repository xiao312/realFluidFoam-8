# Liang Case 5 diffusion verification and validation

[Issue #4](https://github.com/xiao312/realFluidFoam-8/issues/4) tracks the open
scientific discrepancy. The first property checks narrow its causes but do not
yet improve the flame-speed curve. This record supersedes the proposed first
checks in the [reference audit](liang-diffusion-literature-20261020.md).

## Results, 20 October 2026

| Check | Result | Meaning |
|---|---|---|
| Saved Case 5 paper screen | Fails at phi=1.30, 1.35 and 1.40 | Repeatable symptom; the discrepancy remains |
| Dilute CH4-N2, NIST Table 2, 250–550 K | All eight values are below the reported uncertainty interval; residuals -3.53% to -5.39% | A measured-property discrepancy already exists before the pressure correction |
| Actual staged adapter versus Takahashi Table 2 | 798 states checked; largest factor relative error 8.89e-16 after explicit boundary classification | Correlation implementation verified at the sampled states |
| Deliberately restored Pr=3 coefficient error | 45 failures, maximum factor error 7.84% | The harness detects the known error |
| Binary symmetry / mixture reconstruction | Symmetry error zero; maximum reconstruction relative error 4.27e-9 | Within the declared trace-bath tolerance; ordinary flame checks retain their tighter criterion |
| Eight frozen Case 4 faces, 22,048 ordered pair samples | Maximum low-Pr denominator fraction 7.02e-10 across all species; 7.95e-21 among ten major species | The low-pressure branch has negligible weight at these sampled states |
| Remove only the upper Tr clamp, independent replay | CH4/H/H2/OH mixture D changes +0.36% to +0.76% at sampled 900–2100 K states | Small extrapolation sensitivity, not a validated model change |

At 300 K and 101300 Pa, the author-mechanism dilute calculation gives
0.224298 cm2/s and stock Cantera GRI30 gives 0.224198 cm2/s. The measured value is
0.237 +/- 0.003 cm2/s (95% expanded uncertainty).
[McGivern and Manion, Table 2](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=931779).
The stock control makes a newly introduced adapter error less likely. It does not
establish Liang's exact dilute transport implementation. The experimental
uncertainties share a systematic component; these are not eight independent
statistical rejections. The exact breathing-air composition is unspecified, so
the additional 21/79 O2/N2 comparison is exploratory.

The refined flame-speed reduction remains 0.0447465 cm/s versus the digitized
paper's 0.1529809 cm/s at phi=1.40. No new flame result is implied by these
property checks. The existing physical transport and solver implementations
were not changed.

## Boundary finding

The adapter uses unity below Pr=0.1, then the first tabulated factor at Pr=0.1.
These values are generally discontinuous. Seven initial failures arose when
thermodynamic-state and pair-normalization rounding selected opposite sides at
exactly that threshold. This was not another erroneous table coefficient.

The revised gate reports all 21 exact-boundary samples separately and requires
them to match one of the two limiting values. Added samples at Pr=0.09999999 and
0.10000001 retain the strict 1e-10 factor tolerance. All other samples retain
the original criterion. This explicitly qualifies the representation of the
boundary; it does not silently relax the correlation test.

The species table includes estimated radical critical pressures as high as
796.719 MPa for atomic carbon, so 100-atm operation alone cannot exclude the
low-Pr branch. The frozen calculation instead measures its actual denominator
weight. It samples the saved finer Case 4 profile at eight face temperatures
near 300, 400, 600, 900, 1200, 1500, 1800 and 2100 K.

Upper-Tr-clamped pairs account for about 82–93% of the CH4/H/H2/OH mixture
denominators at the hotter sampled states. Their coefficient sensitivity remains
below 0.8% because the correlation is already close to its high-Tr limit.
Denominator fractions are not additive flame-speed sensitivities. The unbounded
calculation is an independent extrapolation, not a new actual-adapter flame run.

## Reproduction and provenance

Use [validation/diffusion](../validation/diffusion/README.md). Its commands support
read-only planning, fresh outputs, source/fixture hashes and a negative control.
`flame_gate.py` accepts future screened results and refuses to pass if the three
previously failing conditions are omitted.

| Attempt | Source | Result |
|---|---|---|
| Initial submission | 405aa150e14a9e95e148d7b06590ee068ab33a75 | Rejected before job creation: 4 GiB exceeded the one-CPU partition allowance |
| 125059886 | 405aa150e14a9e95e148d7b06590ee068ab33a75 | Compiled; exited 127 after 21 s because compute-node PATH lacked Python |
| 125060304 | ed3eb83c96beef5ea12803fa90056b8da27ccea5 | 27 s; seven exact-boundary failures preserved |
| 125060880 | 8c0fdb6837a24f37566df86e306cf6310858bfd3 | Completed in 24 s, exit 0; corrected and negative-control checks behaved as specified |

All jobs requested one CPU in `kshcnormal` with a ten-minute cap. Accepted
submissions used default partition memory. The C++ SDK is the existing Cantera
3.2 build in job 124917358; GCC is 11.2. The repaired runner explicitly uses the
project's Python 3.12.15 executable and records its hash. The local dilute and
frozen calculations use pinned Python Cantera 3.2.0.

Remote releases, raw outputs and scheduler logs are under
`/public/home/dfagent/FlamePilot/trials/realfluidfoam/`.
Local raw records are under `state/diffusion-literature-20261020/`, and the
two-panel PNG/PDF is under `output/diffusion-validation-20261020-final/`.
Downloaded papers remain outside Git.

- [Dilute values and source/fixture hashes](liang-diffusion-dilute-20261020.json)
- [Adapter gate and executable/input hashes](liang-diffusion-adapter-20261020.json)
- [Frozen-state contributions and profile hash](liang-diffusion-frozen-20261020.json)

The frozen profile is job 125027407, SHA256
`2a7bc2454a9853ab70f9edc30d4f3961950a03012fdce2ec49b5db31077685ba`.
The NIST PDF SHA256 is
`d846166e59e4a00c09a2d8197b47d6da8a2188a9949fff11a3905a5a71c05b1d`.
The frozen probe uses that profile with the same author mechanism/critical
parameter set; its input directory's phi label is irrelevant to prescribed T/p/Y.

## Next decision

Keep issue #4 open. First obtain a qualified high-pressure self/tracer isotherm,
with the original table and diffusion definition, then extend dilute checks to
the important hydrogen/radical pairs using evaluated or primary references.
Do not scale all diffusivities to match methane's dilute data or extrapolate its
250–550 K measurement fit through the entire flame.

A property-supported candidate must pass these gates and the existing
conservation checks before paired Case 4/5 flames are compared at phi=1.40,
then 1.10/1.30/1.35. Preserve the thermal/chemical background across each pair.
If the pressure correction and important binary properties remain consistent,
the next question is Case 4's internal flame structure and diffusion sensitivity,
not another global fitted multiplier.
