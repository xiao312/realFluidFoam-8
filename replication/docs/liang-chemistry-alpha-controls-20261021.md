# Chemistry and Soave-factor controls

21 October 2026, 02:32 Asia/Shanghai. None of these controls closes the
remaining Liang flame-speed discrepancy. Baseline figure curves remain
unchanged. The [20-run identity ledger](liang-chemistry-alpha-controls-20261021.json)
records the observed source, executable and result hashes.

## Activity-based chemistry

Eight hydrogen controls use the author pair table and C4-smoothed alpha.
The activity law applies fugacity to both forward and reverse mass action,
with physical SRK concentrations for collision partners. It retains ideal
equilibrium constants without an additional reverse fugacity correction.

| phi | Case 3 pressure-based, cm/s | Case 3 activity-based, cm/s | Jobs |
| --- | ---: | ---: | --- |
| 1.10 | 56.579288 | 57.821042 | 125082503 / 125082504 |
| 1.40 | 75.565875 | 77.265324 | 125082521 / 125082523 |

The activity law raises speed by approximately 2.2%, worsening agreement.
The paired ideal controls agree exactly at both conditions.
Build 125082121 uses source
`234975609868a84103d568a6fa03cfd7e70c2091`.
The executable SHA256 is
`5ad31c80c8d05ccb27dc09f9d58f17919cca8b88406cda1b00a227bf85b7c8d2`.
Six frozen-state checks give maximum relative error `1.1e-15`.
The equilibrium detailed-balance residual is `3.7e-8`; elemental error is
below `2.3e-16`.

## Signed Soave factor

Twelve controls isolate the signed polynomial from the absolute square root
in the attraction mixing rule. The [source audit](liang-srk-root-sign-audit-20261021.md)
explains why this is an identified implementation alternative, not an
established Liang prescription.

| phi | Energy form | Absolute-root speed, cm/s | Signed-factor speed, cm/s | Jobs |
| --- | --- | ---: | ---: | --- |
| 1.10 | Consistent total enthalpy | 56.581852 | 56.301602 | 125083806 / 125083812 |
| 1.10 | Partial-enthalpy temperature | 56.931061 | 56.293809 | 125083816 / 125083818 |
| 1.40 | Consistent total enthalpy | 75.582880 | 75.243065 | 125083830 / 125083833 |
| 1.40 | Partial-enthalpy temperature | 76.008679 | 75.237555 | 125083836 / 125083840 |

The consistent formulation changes by approximately 0.5%, which is
insufficient. Signed-factor temperature and enthalpy forms almost coincide.
The absolute-root cusp contributes to their earlier difference. The ideal
controls agree exactly, and no signed variant replaces the baseline.

Build 125083598 uses source
`615f3f70d1e698cce22b87c719f05fdff8351b2c` and executable SHA256
`6bccddd543f7869b0223017c436366cd9b5ca0dee7d831ed5577275740905316`.
Its qualification covers 48 states, including 22 negative mixed factors,
polynomial identities, heat capacity, Gibbs–Helmholtz derivatives,
partial-enthalpy consistency, pure-species limits and zero crossings.

## Prompt-HCO methane control

The [publisher-source audit](liang-hp-historical-source-audit-20261021.md) identifies
the exact HP input. The prompt-off variant removes only the six specified
correction/direct-product channels. Parent reactions and other HCO pathways
remain unchanged.

| Variant | Job | Speed, cm/s | Burned temperature, K | Final points |
| --- | --- | ---: | ---: | ---: |
| Prompt-on, matched numerical guess | 125082807 | 3.971810 | 2230.3354 | 2158 |
| Prompt-off | 125082800 | 3.964975 | 2230.5225 | 2163 |

Both use 100 atm, 298 K, phi 1.10, ordinary mixture-averaged transport,
and the same saved steady numerical guess. They are separate steady solves.
The change is -0.006835 cm/s (-0.172%); Liang's reading is
2.9220 +/- 0.0473 cm/s. This switch cannot explain the gap.

The driver source is `f74de8091814920b54e0f8563375414e2af77b05`,
build 125081320, executable SHA256
`2df9816827ca39e52a787a7126c11800000cbfba6b02c9be851cf6b24181401d`.
Input preparation uses `b024acd0adf3b396d49bcfd32f21db7134316d33`.
The prompt-off input SHA256 is
`aec705319b232278613acbc3f5784a61f9c5ace9e9a21578a0343d309f9d8caf`.
The collected outputs and scheduler states are retained under
`state/liang-hydrogen-20261020/snapshot-prompt-0232`.

The versioned fixed-pressure HP preparer reproduces the previous input
byte for byte. Its 3204-temperature rate comparison gives maximum relative
error `9.0e-15`; complete forward-rate checks give `1.2e-14`.
This qualification applies only at 100 atm and 298–3500 K.
