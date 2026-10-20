# Diffusion measurements: species and pressure checks

20 October 2026, Asia/Shanghai. This extends
[issue 4](https://github.com/xiao312/realFluidFoam-8/issues/4).
Chemistry, thermal models and the flame results are unchanged.

The tests identify dilute transport discrepancies and show that the current
Takahashi correction substantially improves measured methane self-diffusion.
They do not establish the cause of the remaining Liang Case 4-to-5 speed gap.
Changing reaction rates is not supported by these results.

## Results

| Property check | Result with author transport / Cantera 3.2 | Qualification |
|---|---|---|
| H2 in N2, 303.15-453.15 K | 3.20-3.81% low; 0/6 mean values inside estimated 2% band | Measured Taylor diffusion in N2 carrier |
| H2 in O2, same temperatures | 3.91-6.34% low; 0/6 inside band | Measured Taylor diffusion in O2 carrier |
| H2 in air, same temperatures | 2.59-4.71% low; 0/6 inside band | Exact reported 79.4/20.6 N2/O2 volume composition |
| N2 in H2, same temperatures | 0.22-1.58% low; 6/6 inside band | Reverse carrier retained separately |
| OH in air, 296 K | 0.311703 versus 0.217105 +/- 0.026316 cm2/s; 43.57% high | Ivanov 2007; exact air composition not qualified |
| OH in air, 300 K | 0.319120 versus 0.260526 +/- 0.026316 cm2/s; 22.49% high | Liu 2009; inferred from He/air measurements |
| H2O-N2 versus NIST evaluated fit, sampled 300-2000 K | 3.33-11.18% low | Reference fit, not new experimental points |
| H2O-CO2, same sample temperatures | 4.10-7.31% low | Reference fit |
| CH4-N2, sampled 300-1200 K | 3.51-4.89% low | Reference fit; distinct from previous McGivern measurement gate |
| O2 self-diffusion, sampled 300-2000 K | 3.83-7.76% low | Reference fit |
| CH4 self-diffusion, 28 high-pressure points within Table 2 range | Mean absolute error falls from 20.56% dilute to 3.82% corrected | Conditional pure-fluid comparison; maximum corrected error 9.89% |

The dilute author and stock GRI30 values differ by at most 0.151% across
the hydrogen and NIST-fit samples. This supports an input/model limitation
shared with standard transport; it does not identify a new adapter coding error.

The hydrogen measurements come from
[Matsunaga et al., Table 1, p.190](https://doi.org/10.1299/kikaib.67.189).
Replicates and detector distinctions are preserved in the fixture. The reported
2% is an estimated uncertainty without a stated confidence level; it is not
reduced by averaging replicates. The carrier dependence also limits a single
composition-independent binary coefficient.

The OH measurements are separate observations from
[Ivanov et al.](https://doi.org/10.1021/jp066558w) and
[Liu et al., paragraph 10](https://doi.org/10.1029/2008GL036170).
The units in those sources are pressure-normalized `Torr cm2/s`; division by
760 gives the listed values at 101325 Pa. Do not pool temperatures or attach a
95% label to the reported errors. At 296 K, the model's entire N2/O2 bath
range is 0.310700-0.315536 cm2/s, so an uncertain N2/O2 ratio alone cannot
explain that difference. Other experimental assumptions remain relevant.

The current OH transport has diameter 2.75 angstrom, well depth 80 K and no
dipole entry, the same collision diameter and well depth as O.
Liu instead compares OH measurements with a polar H2O analogue, using
effective collision parameters different from stock GRI30 H2O. The exact
published parameters are recorded as evidence, not installed as a new model.
Room-temperature agreement would not qualify an extrapolation to a hot flame.

[NIST TN2279, Table 1a](https://doi.org/10.6028/NIST.TN.2279) supplies the
evaluated temperature fits. Only temperatures inside each published fit range
are sampled. The listed uncertainty ranges are retained without interpreting
them as uniform 95% confidence intervals.

## Pressure dependence

The [Dawson source qualification](liang-high-pressure-diffusion-source-20261020.md)
explains the original dissertation table, units and remaining pressure-basis
assumption. Pure-methane self-diffusion avoids the Fick/Maxwell-Stefan conversion
needed for finite mixtures. It cannot validate radical binary diffusion.

All 35 warm-gas measurements are retained. With the actual input values
`Tc = 190.6 K`, `Pc = 4.61 MPa`, 28 lie inside `0.1 <= Pr <= 5` and
`1 <= Tr <= 5`. The other seven are excluded from the in-range statistics.
The plus-one-atmosphere pressure interpretation changes predictions by up to
4.64%; the table does not explicitly label its PSI basis. No formal
acceptance interval is invented from the separate 3% systematic and about
1.5% scatter components.

To isolate pressure trend from a constant dilute-scale bias, each near-isotherm
also compares `(Dmeasured/Ddilute)/(Dmeasured/Ddilute)first` with `F/Ffirst`.
The first measured state is not a zero-pressure reference. The common gradient
calibration cancels, while measurement scatter and small model-based temperature
normalization remain.

| Approximate isotherm | In-range points | Normalized trend error range |
|---|---:|---:|
| 257 K | 10 | -8.22 to +2.76% |
| 297 K | 6 | -1.74 to +2.32% |
| 323 K | 7 | -0.002 to +3.30% |
| 354 K | 5 | 0 to +3.22% |

This supports the correction's broad pressure dependence, with residual
limitations. It gives no basis for applying a global diffusivity multiplier
or claiming that the high-pressure binary validation gate is closed.

## Decision and next experiment

Keep the current baseline and chemistry fixed. The next model investigation is
species/pair-specific collision data and their temperature dependence. Qualify
an OH polar-analogue calculation against its own low-temperature measurements,
and obtain H-atom data before treating radical transport as validated.
The H2O comparisons also justify examining its important bath pairs.
Rank their contributions at saved flame states before an expensive sweep.

Any alternative must alter diffusion alone in both Cases 4 and 5, preserving
the thermal baseline, critical table and chemistry. Changing a species transport
entry without isolating conductivity/viscosity would confound that comparison.
A hot-flame extrapolation can be an explicitly labelled sensitivity test, not
a validated correction. Compare both absolute speeds and the Case 4-to-5
decrement at phi=1.40 before extending the curve. Do not fit parameters to Liang.

No new flame was launched in this batch. The 0.04475 versus 0.15298 cm/s
decrement remains unresolved. The existing CFD jobs 125043700 and 125046769
were still running at the scheduler check (elapsed 3:36:32 and 3:14:33,
eight CPUs each); no field or initialization was changed.

## Reproduction and provenance

Source base: `f73f2455677d4d045f039849d712ccaabf505b1b`; this change adds only
validation tools, fixtures and reports. Input mechanism SHA-256:
`c6e72c25dbf5af75a16b71042e071aed15ca4fd4a8a854fd8720a820ce1986c6`.
Both calculations use pinned Cantera 3.2.0 and the existing author input directory.
The `phi110` directory label identifies the mechanism bundle; these are prescribed
property states, not a phi=1.10 flame calculation.

```text
python -B replication/validation/diffusion/light_species.py INPUTS/ideal.yaml
python -B replication/validation/diffusion/light_species.py INPUTS/ideal.yaml --output NEW_LIGHT.json
python -B replication/validation/diffusion/self_diffusion.py INPUTS
python -B replication/validation/diffusion/self_diffusion.py INPUTS --output NEW_SELF.json
python -B replication/validation/diffusion/property_report.py NEW_LIGHT.json NEW_SELF.json PREVIOUS.pdf
python -B replication/validation/diffusion/property_report.py NEW_LIGHT.json NEW_SELF.json PREVIOUS.pdf --output NEW_DIRECTORY
```

The light-species runner exits 1 because 18/24 hydrogen means fail their
source's estimated band. This is a recorded scientific comparison failure,
not an execution failure. The self-diffusion runner reports residuals without
claiming statistical acceptance. No source coefficient is tuned.

Committed result files:
[light species](liang-diffusion-light-species-20261020.json) and
[self-diffusion](liang-diffusion-self-20261020.json).
Their source/input hashes are part of each report. Original publications and
intermediate outputs stay under the ignored
`state/diffusion-light-species-20261020/` and
`state/diffusion-high-pressure-20261020/` directories.

The expanded three-page property PDF is at
`output/pdf/diffusion-validation-20261020-published/diffusion-validation.pdf`.
It preserves the earlier verification page and adds the two new comparison
pages. The two page renders were inspected after fixing a legend/caption
overlap. The Lark update replaces its existing property attachment; the
Liang flame image and its paper crop retain their current data.

Verification covered 90 prescribed property states, staged-source hash parity,
all four self-diffusion isotherms, and exact preservation of the original PDF
page render. The final added page renders match the inspected versions.
Published PDF SHA-256:
`1a17eab5ab7bddc1f49661d3825fd80cee8c87cdc71ca567108da40040b2a3fa`.
