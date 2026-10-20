# Pressure-chemistry comparison, 20 October 2026

At 02:48 Asia/Shanghai, all five baseline cases had completed all 13 equivalence
ratios: 65 numerically screened points. The baseline uses pressure chemistry,
the dense conductivity increment, original SRK alpha and the legacy Takahashi
coefficient. Corrected-table and smooth-alpha pilots remain separately labelled.
The rich Case 5 discrepancy persists: +0.0993 cm/s at phi=1.35 and +0.1120 cm/s
at phi=1.40 (1.69% and 1.99%).

| Case | Matching paper points | RMS error (cm/s) | Maximum absolute error (cm/s) |
| --- | ---: | ---: | ---: |
| 1, ideal | 11 | 0.01291 | 0.02611 |
| 2, SRK density | 10 | 0.01328 | 0.02552 |
| 3, SRK enthalpy | 10 | 0.00775 | 0.01620 |
| 4, dense conductivity increment | 10 | 0.01481 | 0.02550 |
| 5, legacy Takahashi | 11 | 0.05900 | 0.11201 |

The comparison screen, specified before the full-curve evaluation, is
`abs(error) <= max(0.05 cm/s, 0.01*reference) + digitization uncertainty`.
Raster uncertainty is 0.015–0.04 cm/s. No extrapolation is used; marker series
are compared only at matching nominal phi. These are numerical comparison
screens, not scientific acceptance or proof of Liang's unpublished model inputs.

The plot contains all 65 screened baseline points and four labelled diagnostic
points. It replaces the existing Lark gallery in place,
retaining the paper panel, caption and physical size. The plotter corrects the
axis calibration using measured tick centers; this does not alter solved speeds.
The black-curve digitizer excludes the y-axis tick region before sampling.
The machine-readable snapshot is `cantera-pressure-complete-20261020.json`.
The [verified Lark comparison](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnbRqBgmSNSmENThGJgS5aVh)
retains the paper's 204-by-175-point panel and its original caption beside the
overlay. The phi=1.44 endpoint is retained in data but outside the printed axes.

## Takahashi table discrepancy

The primary [Takahashi paper](https://doi.org/10.1252/jcej.7.417), Table 2 on
printed page 419, specifies **B=2.39031 at Pr=3.0**. Cantera v3.2.0 instead has
3.39031 in `src/transport/HighPressureGasTransport.cpp`. Nguyen's upstream
`chungTakaTransportI.H` has the primary value 2.39031. The downloaded primary
PDF SHA256 is `88e9eaa011e6b17b4ea2dd1253c36e363865776f4c8a8fa4db8fb507ada3945e`;
the table was checked visually as well as by text extraction.

At Pr=3 and Tr=2, the original Cantera function gives 0.991467; Table 2 gives
0.941602. The regression first reproduces that discrepancy, then passes with
the isolated `takahashi-table2` option. Other pressure rows and interpolation
continuity remain checked. No parameter has been fitted to a flame curve.
This option preserves the existing reduced-temperature bounds and changes only
the one coefficient's contribution. Both forms remain available for comparison.

Source/build 8a0c8d0/124940280 passed on SCNet. Case 5 correction pilots:

| phi | Pressure (atm) | Job |
| ---: | ---: | --- |
| 1.00 | 100 | 124940384 |
| 1.10 | 100 | 124940385 |
| 1.40 | 100 | 124940386 |
| 1.10 | 1 | 124940387 |

The correction gives 7.049275 cm/s at phi=1.10 and 5.762399 cm/s at phi=1.40,
slightly higher than the corresponding legacy values 7.036205 and 5.754747.
Twelve corrected-table sweep conditions have completed as of 03:32 CST;
only phi=1.00 remains running. The completed lean values are 5.63654545 cm/s
at phi=0.92 (124942489) and 6.00985335 at phi=0.95 (124942493).
Independent Case 4 guesses give 5.63650031 and 6.00977336, respectively,
differences below 0.000081 cm/s. An additional phi=1.00 trial124954912 uses
the completed phi=1.02 Case 5 profile only as a steady numerical guess.
Smooth-alpha pilots reduce the phi=1.10 and 1.40
completed values to 7.018570 and 5.733852, respectively. They do not close the
rich-end gap. The full retained pressure sweep
uses cf40834/build124937336. Added phi=1.02 conditions use a10cd1b/build124938314.
The ideal phi=1.02 job 124938861 failed before entering the solver because site
Bash treats an empty array as unbound under nounset. Source96ba5de fixes the
wrapper; retry124940112 uses build124939982. The failed receipt remains retained.

## Energy and CFD follow-up

Smooth-alpha Case 3 pilots 124939642/124939652 completed in about six minutes.
Physical-concentration and pressure-chemistry speeds are 6.910495 and 7.027479
cm/s, respectively. Energy audit124940475 compares their frozen fluxes with
the original-alpha controls. See the separate enthalpy-discontinuity record.

All twelve original-zero 200-us CFD jobs completed. For phi=1.10, 180–200-us
mean OH speeds are 7.2022 cm/s for native124916221 and 7.3970 for corrected
124916226. Temperature-marker means are 7.0838 and 7.2596. Both markers still
drift upward; a final OH sample near7.45 is not a steady convergence result.

Source6d22c3e launches the corrected binary124900963 at all eleven CFD phi
conditions and the native binary124883260 at phi1.10 to **300 us from newly
generated original-zero fields**. It does not resume the completed runs.
The phi1.10 pair has matching physical-input hash
`b61cf0f9c15769e9f1e391803996285b46e2ca4486389a5c13f7c7b0a8b8aa3f`.
Jobs124939589/594/600/606/611/614/620/636/647/655/658 are the corrected phi
0.90–1.40 sweep; job124939663 is the native control. Each uses eight cores and
an eight-hour ceiling. All twelve were running with verified time-zero starts.

An ideal Cantera transport control (124942608) and the newly qualified optional
Cantera CP-chemistry pilot (124950538) also start from original zero. The latter
uses source2ead1ab, solver124950245 and bridge124947872. Its independent reactor
and CFD startup qualification is recorded on branch `draft/cantera-bridge` in
`replication/docs/cantera-cfd-coupling-20261020.md`. These runs are still developing.

No corrected production solver merge or new 2D campaign is justified by these
developing 1D data yet. Remaining checks include time/mesh/domain independence,
the model-specific energy balance, and the full corrected diffusion curve.

## Enthalpy-flux interpretation under test

Liang p.1734 discusses species enthalpy evaluated using its departure formula.
The cited [Jorda Juanos/Sirignano paper](https://doi.org/10.1016/j.combustflame.2017.01.030),
p.57, explicitly replaces mixture parameters by individual-species parameters.
This supports testing pure-species diffusion enthalpies separately from the
thermodynamic partial-molar values. It does not identify Liang's private code.
The author-hosted PDF SHA256 is
`8104c6f00cb5b610b9ac9776cc4484be5baad39212a027dcd9a68440f8582a31`.

Frozen audit124950946 changes only the enthalpy multiplying species fluxes.
The maximum pure-minus-partial flux magnitude is 284078 W/m2 for smooth Case 3
at phi=1.10, 272508 W/m2 for smooth corrected-table Case 5 at phi=1.10, and
233800 W/m2 at phi=1.40. These are about 2.2--2.5% of peak conduction. The
ideal control has exactly zero difference. A frozen flux difference is not
a flame-speed prediction.

Source90da17c/build124951545 adds explicit opt-in total-enthalpy and
pure-species-flux diagnostics without changing the phase's thermodynamic API.
Scheduled controls are 124951843/124951845 (ideal), 124951846/124951853
(smooth Case 3, phi=1.10), and 124951856/124951859 (smooth corrected-table
Case 5, phi=1.40). Within each pair, only the diffusion enthalpy choice differs.
The partial-molar total-enthalpy case also controls for changing the discretized
energy equation. Ideal parity, refinement and total-flux balance must pass
before interpreting these pilots.

The ideal pair completed with byte-identical saved profiles and speeds
7.45755238 cm/s. This is 0.03833% above the stock fine-grid ideal control
(7.45469524); the last refinement changes speed by 0.12175%. Audit124953754
finds an upwind total-flux range of 2806.89 W/m2, 0.02156% of peak conduction,
for both definitions. Their pure-minus-partial flux difference is exactly zero.
These are numerical controls, not a nonideal replication result.

21 October reconciliation: the four nonideal pilots also completed. Their
collected profiles match the previously recorded hashes exactly, and fresh
numerical screens pass. The earlier "running" status is superseded by the
[completed evidence](liang-methane-legacy-energy-20261021.json).

| Case and phi | Partial diffusion enthalpy, cm/s | Pure-species diffusion enthalpy, cm/s |
| --- | ---: | ---: |
| Case 3, 1.10 | 7.022453 | 7.019939 |
| Case 5, 1.40 | 5.727907 | 5.725730 |

Both Case 3 points pass the existing paper screen. Both Case 5 points fail:
their errors are +1.509% and +1.471%, respectively. Switching the diffusion
enthalpy changes the Case 5 speed by only −0.002177 cm/s. Thus this
interpretation does not resolve the rich methane discrepancy.
The two ideal profiles remain byte-identical.
Historical build associations are explicit because these older job directories
did not retain their executable hashes or build paths.
