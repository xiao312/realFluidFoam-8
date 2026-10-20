# Liang hydrogen flames: energy and elemental conservation audit

The completed Case 3 profiles do not show a missing energy flux large enough to
explain the paper discrepancy. Their total-enthalpy flux varies by less than
0.019 K when expressed as an equivalent outlet-temperature change. A separate
elemental conservation defect is measurable and largely explained by the
nonuniform-grid advection stencil. Correcting that defect would lower the rich
flame's outlet temperature further, away from Liang's Case 3 temperature.

This audit reads nineteen completed profiles and evaluates local properties;
it launches no flame calculation, changes no solver, and fits no coefficient.
It extends the [previous energy follow-up](liang-energy-followup-20261021.md)
with reconstructed face fluxes and an explicit discrete conservation balance.

## What was reconstructed

Let `m=rho*u`, `j_k` denote species diffusive mass flux, and `hbar_k` the
mass-specific partial enthalpy. The audited energy flux is

```text
F_h = m*h_upstream - lambda*(T_right-T_left)/dx
      + sum_k(j_k*hbar_k).
```

For each face, temperature and mass fractions are arithmetic means of the two
nodes. The calculation uses the saved model's SRK density, mixture-averaged
mole-fraction diffusion, stock or midpoint correction velocity as configured,
and the same ideal conductivity used by Cases 1–3. Where configured, the ten
author binary-diffusion polynomials replace the corresponding dilute pairs.
The positive-velocity advective face state is the left node, matching
`TotalEnthalpyFlow.h`. These operations follow the pinned
[Cantera 3.2 source](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/src/oneD/Flow1D.cpp).

The independent Python SRK expressions reconstruct every saved node's density
within `8.8e-11 kg/m3` and enthalpy within `8.3e-9 J/kg`. Across these files,
`max|sum(Y)-1|=6.7e-10`, and the largest residual sum of diffusive mass fluxes
is `9.5e-10 kg/(m2 s)`. Thus normalization or a molar-to-mass conversion error
does not explain the measured balances.

All results and nineteen face-flux CSVs are under
`state/liang-hydrogen-20261020/energy-conservation-audit/`.
The JSON records the individual profile hashes and configuration, not merely
their job numbers.

## Energy is conserved closely in the baseline total-enthalpy runs

The normalization below is `Delta F_h/(m*Cp_outlet)`. This expresses an energy
imbalance in kelvin; it is not an independently solved temperature correction.

| phi | Job | Speed, cm/s | Outlet T, K | Outlet-minus-inlet energy, equivalent K | Maximum energy-flux span, equivalent K |
| --- | --- | ---: | ---: | ---: | ---: |
| 1.1 | 125071829 | 57.29224 | 2448.55726 | +0.01438 | 0.01870 |
| 1.3 | 125071904 | 73.06141 | 2348.55728 | +0.01361 | 0.01444 |
| 1.4 | 125069094 | 75.50939 | 2301.44563 | +0.01540 | 0.01541 |

These are original-alpha, LJ-transport, Case 3 runs. The mass-flow span is below
`1.8e-10` relative in this subset. Inlet conductive plus species-enthalpy
diffusive flux is below `7e-14 K` equivalent. The inlet and outlet elemental
diffusive fluxes, divided by mass flow, are below `1e-13` in mass-fraction units.
The flame therefore has effectively flat boundary states. Neither finite inlet
heat conduction nor outlet diffusive leakage can supply a several-kelvin error.

For comparison, the original-alpha Case 3star run at phi=1.4 has a `+1.546 K`
energy endpoint defect and a `2.391 K` span. Smooth-alpha partial-temperature
controls reduce that defect substantially. This is consistent with the earlier
alpha regularity finding; it does not expose an omitted term in the conservative
Case 3 equation.

## The elemental defect follows the nonuniform-grid stencil

For an element with mass fraction `Z`, chemical production sums to zero.
Cantera's positive-velocity interior species equations imply

```text
m_j*(Z_j-Z_(j-1))/dx_left + (J_j-J_(j-1))/w_j = 0
w_j = (dx_left+dx_right)/2.
```

Summing after multiplying by `w_j` leaves a non-telescoping advective sum when
`dx_left != dx_right`. With nearly constant mass flux and flat end states,

```text
Z_out-Z_in =
  -sum_j[(w_j/dx_left - 1)*(Z_j-Z_(j-1))]
  -(J_out-J_in)/m
  + nonlinear-solution residual.
```

This is a derivation from the documented finite-difference scheme, not an
assumption about chemical mass conservation. Cantera documents its
[upstream advection and centered second derivatives](https://cantera.org/3.2/reference/onedim/discretization.html).
The species inlet condition conserves `m*Y_k+j_k` against the prescribed feed;
it does not force every first-node mass fraction independently. In the audited
profiles the inlet diffusion term is already negligible.
[Boundary implementation](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/src/oneD/Boundary1D.cpp)

| phi | Relative H-element change | Measured absolute change | Predicted nonuniform-grid change | Remaining absolute residual |
| --- | ---: | ---: | ---: | ---: |
| 1.1 | -0.25586% | -8.00181e-5 | -8.01430e-5 | +1.24884e-7 |
| 1.3 | -0.19376% | -7.12078e-5 | -7.11905e-5 | -1.73603e-8 |
| 1.4 | -0.19724% | -7.78450e-5 | -7.78706e-5 | +2.55953e-8 |

The audit includes the tiny mass-flow and boundary terms in the residual.
The stencil predicts more than 99.8% of the H defect in each baseline Case 3
profile. Oxygen changes in the opposite direction. This is a finite-resolution
conservation limitation, also present in the stock ideal-gas control, rather
than evidence for a missing chemical energy source.

At phi=1.4, the smooth partial-temperature grid controls make the consequence
clear:

| Grid multiplier | Job | Points | Relative H-element change | Speed, cm/s | Outlet T, K |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 125071518 | 1824 | -0.19729% | 75.52361 | 2300.87770 |
| 2 | 125071524 | 3631 | -0.09919% | 75.44738 | 2300.08472 |
| 4 | 125071526 | 7258 | -0.04836% | 75.46081 | 2299.91284 |

The elemental defect halves, but the largest speed change is only `0.0763 cm/s`.
The finest control retains an energy endpoint defect equivalent to `0.317 K`,
so this is not a formal asymptotic extrapolation. It does establish that these
observed grid changes do not approach Liang Case 3's approximately
`71.81 +/- 0.33 cm/s` at this phi.

## Removing the elemental defect would worsen the temperature comparison

An independent algebraic calculation sets ideal TP chemical equilibrium at
each trial temperature and then solves `h_ideal+h_SRK_departure=h_in`.
It first retains the feed's elements, then repeats using the saved outlet's
elements. It uses the exact 21/79 O2/N2 feed, 298 K and 100 atm; it does not
solve or initialize another flame.

| phi | Equilibrium with feed elements, K | Equilibrium with outlet elements, K | Saved outlet, K | Temperature increase caused by element drift, K |
| --- | ---: | ---: | ---: | ---: |
| 1.1 | 2446.58580 | 2448.54348 | 2448.55726 | +1.95767 |
| 1.3 | 2346.81314 | 2348.54395 | 2348.55728 | +1.73081 |
| 1.4 | 2299.63601 | 2301.43048 | 2301.44563 | +1.79447 |

The remaining saved-temperature differences are only `0.014–0.015 K`, in
agreement with the direct energy-flux audit.

At phi=1.3, the extracted paper Case 3 temperature is
`2351.865 +/- 0.817 K`. The current baseline is already `3.308 K` lower; the
feed-conserving equilibrium is `5.052 K` lower. Thus improved elemental
conservation is necessary for numerical qualification, but it cannot explain
why the paper simultaneously reports a lower speed and a higher temperature
for this case. The phi=1.1 paper-temperature reading has a much larger
uncertainty (`+/-4.421 K`) and is a weaker discriminator.

## Remaining interpretation and next discriminating check

Liang's PDF numbers its thermodynamic equations (1)–(3). The expanded species
and energy equations (4)–(5) belong to its reference 8. That source evaluates
mixture enthalpy from the mixture departure and species enthalpies using pure
species parameters. Substitution of its species equation into its energy
equation leaves the divergence of advective, conductive and species-enthalpy
fluxes. It does not require an additional mixture-composition heat source.
[Jorda Juanos and Sirignano, Eqs.4–5 and 17–18](https://sirignano.eng.uci.edu/theme/pdfs/39.pdf)

The current implementation already advects full formation-plus-departure
enthalpy. This audit supplies a direct conservation check of that implementation.
It finds no additional pressure-work, sign, or unit correction justified by
the primary equations. The paper's Case 3star implementation remains
underspecified; equality between a consistent partial-enthalpy temperature
equation and total-enthalpy equation does not establish what approximate
temperature equation the authors actually used.

The newly recovered dissertation narrows one untested interpretation. Its
printed page 169 defines Case 3star by saying that the **heat capacities** are
updated, whereas the journal uses the broader wording "thermodynamic
properties." A named `Cp-only` control would therefore retain ideal species
enthalpies in the chemical and diffusive terms of the stock temperature
residual, while changing its mixture Cp to SRK Cp. That is distinct from the
partial-enthalpy temperature control and the pure-species Cp/enthalpy control.
The wording supports testing this approximate residual; it does not prove the
authors left every enthalpy term ideal.
[Liang dissertation, printed pp.166 and 169](http://imgsvr.riss4u.net/ddod8/201812/14998/128/14998128.pdf)

There is also a source-level interpretation inconsistency. The dissertation's
conclusion on printed page 176 attributes the extra reduction from the enthalpy
form to a lower flame temperature. Its Figure 8-4, like journal Figure 5,
visibly places the red Case 3 temperature above the blue Case 3star temperature.
Both legends were checked in rendered pages. Preserve those published labels;
do not silently swap them or infer a new heat source from the prose.

A useful isolated numerical control would conserve species and total enthalpy
with one common face-advection/divergence construction, tested first against
the ideal baseline and then Case 3 at phi=1.3. Acceptance should include
elemental and energy fluxes, not only the last refinement's speed. Tightening
the nonlinear tolerances separately would establish whether the finest-grid
energy residual is a solve tolerance limit. Neither change should be selected
or tuned to lower the speed toward the paper.

## Reproduction and identity

The state scripts default to a no-write plan. `--apply` requires a new result
destination; `endpoints.py` refuses to overwrite its existing output. Use the
project's local `state/equilibrium-venv/Scripts/python.exe`, Cantera 3.2.0:

```text
python -B state/liang-hydrogen-20261020/energy-conservation-audit/audit.py
python -B state/liang-hydrogen-20261020/energy-conservation-audit/audit.py --apply --output NEW_DIRECTORY
python -B state/liang-hydrogen-20261020/energy-conservation-audit/endpoints.py
```

SHA256 evidence identities:

- `results/audit.json`:
  `279f09fc3cfcc9de02705009156f46e22dcd495d30655d53c90688a1bdabb760`.
- `endpoints.json`:
  `d2e30f5901b9f87b408e1c162c0070b526b354ae764651dd0b943175fc114466`.
- `TotalEnthalpyFlow.h`:
  `8be15adf1ec4e1534423456b9be32a55e3a6a26c29de3147b2361cd6714aed75`.
- `EnergyFlows.h`:
  `8f6f665265902493d01cfb21b1b172fa5f332db58eda8d9e08f48debdd0c0aa9`.
- `SrkPhase.h`:
  `9dfbd1a36a1fd642d85662d0b069d3da842a84001208b6a1e0f5faac6ea022e0`.
- `SrkKernel.h`:
  `7b59979b9145455669db405b2d4461ae00edc415a411d20ccf30c5d90518e8c3`.
- Pinned Cantera `Flow1D.cpp`:
  `c6b16e3dcc46c05738386501cd1fdf3d143c7b0cb7f858f570a291d037b56b79`.
- Liang dissertation, retrieved from the public RISS copy:
  `806906f751d2b257dae7a9e66111158c5aaa8ec227fdd8f5ea909a57a52c3a85`.
  Rendered PDF pages 176, 179, 180 and 186 are saved beside the audit scripts.

The primary paper PDF hash remains
`24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe`;
the figure readings and their uncertainties are preserved by the earlier
digitization evidence, not adjusted using these computations.
