# Diagnosis of the staged Cantera discrepancy

19 October 2026. The first extension changes more than the intended high-pressure
corrections. Frozen-state probes expose a large dilute conductivity difference
and near-zero radical diffusion. These are actionable model problems; the
publication mismatch is not resolved by the earlier numerical screening.

## Reproduction

Run from the fork checkout:

```sh
python replication/development/cantera-liang/paper_stage_check.py \
  replication/docs/cantera-liang-results-20261019.json --require-paper-agreement
```

The report fails publication agreement. At phi=1.10 the successive speed changes
are -0.09555, -0.41389 and +1.02650 cm/s. The reference checks use deliberately
wide visual bounds from Liang Fig.8(a), not exact author data. They must not
be used to fit physical parameters. The original PDF hash and overlay calibration
remain in the staged-result record.

## Frozen-state findings

Build 124931898 and probe 124932004 use source
`d9393b13b46f15de00408c4c7e5447c20cee7923`, the pinned Cantera 3.2 SDK,
and saved profiles from ideal pilot 124919519 and SRK-caloric pilot 124919531.
Each comparison holds temperature and composition fixed and varies pressure
between 1 and 100 atm. Small negative numerical species values are projected
to zero for this diagnostic. No solved flame or transient initialization changes.
The [JSON summary](cantera-model-diagnosis-20261019.json) records exact values
and the raw CSV hash.

| Temperature | Baseline lambda | Ely–Hanley at 1 atm | Ely–Hanley at 100 atm |
|---|---:|---:|---:|
| 298 K | 0.026969 | 0.028496 | 0.034830 |
| 1499.5 K | 0.112966 | 0.129864 | 0.131613 |
| 2099.8 K | 0.151281 | 0.175874 | 0.177311 |

Conductivity units are W/(m K). At 1499.5 K, replacing the dilute model adds
14.96%, while raising the Ely–Hanley pressure from 1 to 100 atm adds only
1.35%. At 2099.8 K these changes are 16.26% and 0.82%. Thus Case 4 is not an
isolated test of density-dependent conductivity. This is a confirmed property
difference; its contribution to flame speed requires the controlled flame test.

Takahashi gives OH diffusivity ratios of 4.22e-9 at 298 K and 1.20e-15 at
399.3 K, relative to the same dilute binary base. CH4 ratios are 0.984 and
about 1.02 respectively. At 600 K and above both approach ordinary order-one
corrections. This severe selective collapse is a plausible cause of the slow
Case 5 solves, but a timed corrected solve is needed to establish causation.

The inherited [Cantera implementation](https://cantera.org/3.2/cxx/d2/d89/HighPressureGasTransport_8cpp_source.html)
evaluates the species-pair correction at the pair reduced temperature and
replaces negative results with `Tiny`. That small factor enters the denominator
of the mixture diffusion sum. The inspected Nguyen `chungTakaTransportI.H`
instead bounds reduced temperature to [1,5] and pressure above at 5, and
interpolates toward unity below reduced pressure 0.1. These are distinct
implementations, even though both cite Takahashi. Nguyen also has a different
coefficient at reduced pressure 3; do not copy it without checking the source.

The [original Takahashi paper](https://doi.org/10.1252/jcej.7.417) describes an
empirical chart using reduced state and pseudocritical properties. It does not
justify arbitrary extrapolation until a correlation becomes negative. A bounded
diagnostic is not proof that Liang used Nguyen's bounds or species-pair rule.

## EOS and energy checks

Case 2 changes fresh density from 112.56049 to 112.87529 kg/m3 (+0.280%),
but burning mass flux also drops from 8.39919 to 8.31304 kg/(m2 s) (-1.026%).
Its speed change therefore is not solely a fresh-density conversion.
On identical reaction-zone states, the physical-concentration SRK chemistry
has net-production-vector L1 norms about 4–5.5% below ideal-gas chemistry.
Near equilibrium that ratio is ill-conditioned and is not used to judge error.

One remaining hypothesis is that Liang's CHEMKIN coupling retained
pressure-based ideal concentrations while updating flow density. The
[CHEMKIN API manual](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/pdf/Ansys_Chemkin_Application_Programming_Interface_Manual.pdf)
provides separate pressure and density input rate interfaces. Their existence
does not establish which interface Liang modified. Compare pressure-based and
physical-concentration chemistry explicitly before changing the default.

Endpoint enthalpy differences h_b-h_u are -395/-323/+3002/+3241 J/kg for
Cases 1–4. This requires a full energy-flux/domain/grid audit; endpoint h alone
omits any remaining boundary diffusion and heat flux. Cantera 3.2 calls the
custom partial molar enthalpies and differentiates them in its energy residual.
A temperature variable does not by itself imply omission of real-fluid
enthalpy. Verify the conserved quantity
`F = mass_flux*h + sum(J_k*hbar_k/W_k) - lambda*dT/dx` before replacing that
equation. Liang's species-enthalpy interpretation remains a separate question.

## Controlled next step

Source `5543d41` adds the optional `dense-increment` conductivity diagnostic:

`lambda = lambda_baseline + lambda_EH(T,rho,X) - lambda_EH(T,rho->0,X)`.

The dilute evaluation uses 1 Pa and ideal molar volumes. Default `full` retains
the earlier model; this variant is not called an exact Liang implementation.
Build 124932388 and frozen probe 124932492 passed; all pre-existing property
columns matched probe 124932004 within relative 1e-12 for both input profiles.
The diagnostic gives lambda=0.114817 W/(m K) at 1499.5 K, versus the baseline
0.112966 and full Ely–Hanley 0.131613. Pilot 124932554 is running at phi=1.10,
using the same original steady numerical guess as the full-model pilot.
Use this one pilot before any new curve sweep. It tests whether the large
Case 4 shift mostly comes from replacing the dilute baseline. The enhanced
frozen probe identifies OH pair contributions and checks the new limit.

The enhanced probe identified the specific diffusion failure. At 399.3 K,
the OH–CH2CO pair has reduced temperature 0.69592 and reduced pressure 0.78929.
The inherited implementation replaces its negative factor by 1e-20; that pair
then supplies 95.61% of the OH mixture-diffusion denominator. CH2CO mole fraction
is only 5.41e-6. At 298 K the OH–HCN pair similarly supplies 97.43% of the
denominator despite an HCN mole fraction of 1.72e-12. These trace-species effects
make the need for an explicit correlation-range policy concrete. They do not
establish the physically correct coefficient outside the correlation range.

Next, qualify the diffusion correlation range and pseudocritical mixing,
then test EOS/chemistry conventions and full energy-flux conservation. Require
a low-pressure control as well as the 100-atm pilot before expanding to all
equivalence ratios. Do not tune conductivity or critical data to the target speed.

The pending automatic Case 5 sweep gate 124922744 was cancelled after the
diffusion collapse was found. Original pilot jobs 124919950, 124920962 and
124922397 are retained as controls. Their results are not publication-qualified.
No original-zero OpenFOAM run was restarted or modified.
