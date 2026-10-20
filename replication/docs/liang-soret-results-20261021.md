# Methane thermal-diffusion controls

The Cantera 3.2 Soret control does not explain the missing Case 4–5 separation.
At phi = 1.40, it changes that separation from 0.044695 to 0.045119 cm/s.
The digitized Liang separation is approximately 0.152981 cm/s.
The six controls completed at 100 atm and 298 K.
No baseline curve or production CFD model changed.

| Case | Soret off job | Soret on job | Off, cm/s | On, cm/s | Change |
|---|---|---|---|---|---|
| 1 | 125085850 | 125085885 | 6.116619431 | 6.041508598 | −1.2280% |
| 4 | 125085918 | 125085926 | 5.807094458 | 5.736048405 | −1.2234% |
| 5 | 125085930 | 125085934 | 5.762399365 | 5.690929398 | −1.2403% |

All six passed the existing final-grid, mass-flow and species-normalization
screens. Each on-run saved Soret as enabled and exported its actual native face
fluxes. These checks establish the stated implementation and numerical screen.
They do not identify Liang's thermal-diffusion setting.

## Source, build and numerical evidence

Source: `c9c2c55b3db6b9b6f379026ad94ff4fdea17d34c`.
Build: `125085658`, completed in 67 seconds.
Executable SHA-256:
`0ff9966ece7d6d822699b4a1b3c37e9988358af2df7de7965bab70ff3322735c`.
All six input-record hashes match:
`8028512f5c42ef2163d94af5d7f2d8e342328d08c61d999d4ec9c41b9e2ac585`.

The [machine-readable record](liang-soret-controls-20261021.json) retains each
run's source, executable, input, profile, native-flux and screening hashes.
The [source audit](liang-soret-control-audit-20261021.md) defines the coefficient
and the explicit Case 5 hybrid assumption.

The independent native-face analyzer passed for all three on-runs:

| Identity | Maximum relative error |
|---|---|
| Ordinary plus thermal equals total mass flux | 2.16e−16 |
| Thermal flux equals minus thermal coefficient times grad(log T) | 8.97e−13 |
| Sum of species total mass flux | 2.93e−12 |
| Sum of species thermal mass flux | 3.40e−12 |
| Sum of projected thermal coefficients | 4.80e−11 |

Each relative error uses the maximum corresponding flux or coefficient as its
scale. Native thermal enthalpy flux is evaluated on the solved on-profile.
It is not an isolated frozen-profile measure of the flame-speed response.

Local evidence is under `state/liang-hydrogen-20261020/soret-native-analysis/`.
The offline analyzer's plan and apply both completed. Its script hash is
`b92438735a1ca6a03fdc73ec357e473bbce677aed3fd6bfcad391409b9a6b759`.

## Energy-probe guard

Build `125087918` uses source
`6155e8bd8d44d18d1701e9fdc278ecf9f41d3e50`.
Its flame executable is byte-identical to the first Soret build.
Only the separate energy diagnostic changed.
Qualification job `125088363` completed in three seconds.

The no-Soret energy output before and after the guard is byte-identical:
`cc7ca783903f6d7abb8adbf6b5b9b4f7d3ee4a083fc6ab396ee26d8256c583fd`.
Passing `soret` now fails explicitly before creating an output file.
This prevents a no-Soret reconstruction from silently omitting thermal enthalpy flux.
Use the recorded native face data for that audit.

## Separate manual-formula control

The [manual formula review](liang-legacy-soret-implementation-review-20261021.md)
supports a distinct light-species diagnostic.
Build `125088900` failed its ideal-pressure fixture.
The fixture incorrectly used a populated SRK phase for an ideal-density check.
No flame was submitted from that failed build.

Source `d0cbc70ff405d7e5a78b1029b74c3d1bdc4c90f2` fixes the fixture by using
an actual ideal-gas phase. Build `125089213` passed in 73 seconds.
Its independent manual binary error was 7.75e−16.
Selected-stage and native-flux checks passed.
The inherited 16-state Cantera 3.2 checks also passed.
Executable SHA-256:
`59c1bef01d1d6f36d2dd6fbbf2fca513422a0bf3b9a6800e28a148e08302760e`.

Matched Case 1/4/5 off/on jobs are `125089458`, `125089460`,
`125089462`, `125089463`, `125089466` and `125089471`.
Their completed results will be recorded separately.
This manual formula follows the published sign convention.
It is not established as Liang's historical PREMIX implementation.

## Comparison figures

The per-case gallery now contains the eight completed earlier diagnostics and
the three completed Cantera 3.2 Soret points.
Each diagnostic has a distinct color/marker combination and a matching legend.
The 65-point baseline and frozen CFD capture remain separate inputs.
The original panel and caption retain their publication dimensions.

Input record:
[Figure 8(a) diagnostics](liang-figure8a-diffusion-diagnostics-20261021.json).
Rendered output:
`output/pdf/liang-figure8a-soret-20261021-0330-v2/`.
No diagnostic point replaces a baseline curve.
