# Liang energy formulation audit: 20 October 2026

The hydrogen pilot exposes two different questions. A paper-literal reconstruction
uses pure-species enthalpies in the diffusive energy flux. A thermodynamically
consistent mixture formulation uses partial enthalpies. Our current stock
temperature-equation control uses the latter and therefore is not established as
Liang's deliberately approximate Case 3*. Its difference from our total-enthalpy
control also contains a documented SRK enthalpy discontinuity and potentially a
discretization contribution. Changing the equation label alone cannot establish
replication.

This note audits source and frozen profiles. It changes no model or running job.
Pilot source revision: `ff39189850d8ec83277e3abe093cfc037f8da900`.
Pressure is 100 atm, inlet temperature is the assumed 298 K, and kinetics are
Burke 2012. The examples below use the LJ transport control at phi=1.4.

## What the primary sources specify

Liang's Eq. (3), printed p.1734, gives the mixture enthalpy departure and says the
same expression evaluates individual species. Its rejection of
`h = sum(Y_k h_k)` and citation of reference 8 identify a distinction between
mixture and pure-species properties. The paper does not publish its energy
residual, species-property code, or complete Case 3* implementation.
[Liang, Li and Law (2019)](https://doi.org/10.1016/j.proci.2018.06.070)

Reference 8 explicitly evaluates species enthalpy with individual-species SRK
parameters. Its Eq. (5) retains the mixture enthalpy derivative, whereas Eq. (8)
replaces the convective term by a mass-weighted sum of pure-species enthalpy
derivatives. These supply the strongest available interpretation of Liang's
contrast. Reference 8 also distinguishes partial-pressure chemical equilibrium
from fugacity equilibrium; its reported small difference is for its own
counterflow conditions, not proof for every hydrogen flame.
[Jorda Juanos and Sirignano (2017), pp.56–57 and Appendix A](https://sirignano.eng.uci.edu/theme/pdfs/39.pdf)

Cantera explicitly separates mixture, reference-state, standard-state and partial
molar properties. `getPartialMolarEnthalpies` returns partial molar values, not
pure-fluid values. Its kinetic API uses standard Gibbs energies and activity
concentrations to define reversible reaction equilibria.
[Cantera 3.2 ThermoPhase documentation](https://cantera.org/3.2/cxx/dc/d38/classCantera_1_1ThermoPhase.html)

## Definitions and the equation comparison

Use SI mass-specific quantities unless marked molar:

| Symbol | Definition | Unit |
| --- | --- | --- |
| `m = rho*u` | Constant steady planar mass flux | kg/(m2 s) |
| `j_k` | Species diffusive mass flux; `sum(j_k)=0` | kg/(m2 s) |
| `omega_k` | Molar species production rate | kmol/(m3 s) |
| `s_k = W_k omega_k` | Species mass production rate | kg/(m3 s) |
| `h(T,p,Y)` | Full mixture enthalpy including formation terms | J/kg |
| `hbar_k` | Partial molar enthalpy divided by `W_k` | J/kg |
| `h_pure,k(T,p)` | Pure-fluid species enthalpy at mixture T and p | J/kg |
| `cp` | `(partial h/partial T)_(p,Y)` | J/(kg K) |

For the interpretation based on reference 8, the planar energy equation is

```text
m [h' - sum(h_pure,k Y_k')]
  - (lambda T')'
  + sum(j_k h_pure,k')
  + sum(h_pure,k s_k) = 0.
```

Combining it with `m Y_k' + j_k' = s_k` gives

```text
[m h - lambda T' + sum(j_k h_pure,k)]' = 0.
```

Thus the existing `pure-species-flux` option is a reasonable named
paper-interpretation experiment: it changes the enthalpy multiplying diffusion
while retaining mixture enthalpy in convection. This derivation does not establish
that pure-species enthalpies are the correct general thermodynamic transport
closure.

With proper partial enthalpies, extensivity and differentiability imply

```text
h = sum(Y_k hbar_k)
dh = cp dT + sum(hbar_k dY_k), at fixed p.
```

Consequently the consistent temperature form is

```text
m cp T' - (lambda T')' + sum(j_k hbar_k') + sum(hbar_k s_k) = 0.
```

It is analytically equivalent to the total-enthalpy equation with partial-enthalpy
diffusion flux. A temperature variable is not intrinsically incompatible with
nonideal thermodynamics. The failure concerns inconsistent property definitions
or a missing derivative term. These identities require smooth properties; the
original-alpha kernel currently violates that prerequisite at several crossings.

In Cantera 3.2 `Flow1D::evalEnergy`, the steady residual before normalization is
`-m*cp*T' - conduction - sum(omega_k*Hbar_k + j_k*Hbar_k'/W_k)`.
`conduction` represents `-(lambda*T')'`. `updateThermo` obtains partial molar
enthalpies, and `grad_hk` differentiates them spatially, including composition
variation. Thus our overridden partial-enthalpy API makes the stock residual the
consistent partial-enthalpy temperature control.
[Flow1D.cpp, pinned v3.2.0](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp),
[Flow1D.h, pinned v3.2.0](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/oneD/Flow1D.h)

For the reference-8 approximate temperature equation, pure enthalpies depend only
on T at constant p, so its convective coefficient is
`cp_pure_mix = sum(Y_k cp_pure,k)`. Replacing only source/diffusion enthalpies by
pure values while retaining the full mixture `cp` is a different sensitivity.
Liang does not specify enough implementation detail to assert that this latter
hybrid is its exact Case 3*. Keep the alternatives explicitly named.

## The current difference is not a clean energy-formulation experiment

The saved LJ pilot results are:

| Quantity | Partial total enthalpy, job 125069094 | Stock partial temperature, job 125069104 |
| --- | ---: | ---: |
| Speed, cm/s | 75.5093868 | 75.9714449 |
| Burned temperature, K | 2301.445628 | 2302.927421 |
| `h_out - h_in`, J/kg | 29.17179 | 2929.25934 |
| Endpoint enthalpy difference divided by burned Cp, K | 0.01540 | 1.54588 |
| Final points | 1824 | 1822 |

The enthalpy endpoint diagnostic alone does not prove full flux conservation;
finite boundary gradients and diffusion must also be checked. It nevertheless
shows that these two controls are not interchangeable numerical solutions.

### SRK alpha discontinuity

The current kernel uses `sqrt(a_i) = sqrt(ac_i)*abs(1+m_i*(1-sqrt(T/Tc_i)))`
and geometric mixture attraction. Its derivative changes branch at
`Tc_i*(1+1/m_i)^2`. Mixture departure enthalpy contains that derivative and can
therefore have a finite jump even though attraction itself is continuous.
See the [previous alpha audit](cantera-alpha-discontinuity-20261020.md).

A separate NumPy reconstruction of the SRK cubic and departure expression
reproduced sampled C++ profile enthalpies to below `2.32e-9 J/kg`, using the same
NASA ideal enthalpies. At fixed nearest-profile composition, the Case 3 profile
has these jumps for `Tcross +/- 1e-6 K`:

| Crossing species | Temperature, K | Enthalpy jump, J/kg |
| --- | ---: | ---: |
| N2 | 1023.557979 | 2533.962927 |
| O2 | 1323.334982 | 486.704439 |
| HO2 | 1343.692514 | 9.520804 |
| H | 1814.115139 | 7.609027 |

The jumps persist with shrinking offsets. Species sharing one crossing must not
be counted twice. Their scale is comparable to the partial-temperature endpoint
defect, making this a specific falsifiable explanation, not proof that all the
defect has this cause. A smooth-alpha T/H comparison is needed before assigning
the difference to the paper's enthalpy-mixing argument.

### Discrete advection

`TotalEnthalpyFlow.h` uses an upwind enthalpy value at each face and divides the
face-flux difference by the dual-cell width `(dz_left+dz_right)/2`. Stock species
advection uses the upstream derivative divided by `dz_left` for positive flow.
These are different stencils on a nonuniform grid. The saved profiles contain
neighboring-cell width ratios from about 0.339 to 2 within 300–2200 K.

The apparent five-level refinement record is not a strong independent test here:
both nonideal jobs inherited an already fine 1816-point guess. The first four
criteria retained exactly 1816 points; the last added only 6–8 points. Small
changes across those solves do not demonstrate an asymptotic refinement limit.

A useful alternative retains `m_j * upstream_gradient(h)` and adds centered
divergence of conductive and species-enthalpy fluxes. At steady constant mass flux
this is the same continuum equation while aligning the advective stencil with the
species equations. It must be qualified against ideal and smooth-SRK controls on
explicitly refined common grids. Neither discretization should be selected
because its speed is closer to Liang.

### Pure-species root selection

The current largest-real-root SRK evaluation can change branches when used on a
pure species at the total flame pressure. A 1-K scan at 100 atm gives:

| Pure property | Temperature interval, K | Departure-enthalpy change, J/kg | Number of real roots |
| --- | ---: | ---: | --- |
| H2O | 539 to 540 | +1391155.79 | 1 to 3 |
| H2O2 | 584 to 585 | +593939.99 | 1 to 3 |

These are properties of the pure-fluid reference evaluation, not evidence of
condensation in the actual dilute flame mixture. They can affect a pure-species
flux or pure-Cp diagnostic and cause Newton problems. No branch regularization,
partial-pressure substitution, or clipping should be introduced silently.
Liang does not specify the necessary pure-species branch convention.

## Chemistry and reverse rates

`PressureChemistry.h` evaluates net production rates in a separate ideal phase
at the same T, physical p and Y. This includes ideal-state concentrations,
third-body/falloff evaluation and the ideal NASA reverse-equilibrium constants.
It does not combine forward rates from one phase with reverse rates from the SRK
phase. All stages using this adapter therefore retain the same reaction law at
identical T,p,Y. The SRK density is used in the flame equations but does not
silently replace p in this chemistry calculation.

This is a deliberate partial-pressure chemistry model. It is not fully
fugacity-consistent SRK chemistry. SRK VCS equilibrium elsewhere in the program
uses another chemical equilibrium convention, so its HP temperature is not a
required endpoint of these flames. The adapter's other reaction-query APIs are
not an authoritative diagnostic; its documented interface is
`getNetProductionRates`.
[Current adapter](../development/cantera-liang/PressureChemistry.h)

An independent endpoint check should solve ideal TP chemical equilibrium at a
trial temperature, evaluate that composition's SRK mixture enthalpy, and find
the temperature for which it equals the inlet SRK enthalpy. This tests the
actual pressure-chemistry/mixture-energy combination. It must be kept separate
from a fully SRK-fugacity HP calculation.

## Discriminating next tests

1. Keep the existing partial-T and partial-H controls; change their labels so they
   are not presented as confirmed Case 3*/3 implementations.
2. Run ideal T/H and smooth-SRK partial-T/H on common grids, including a genuine
   additional grid subdivision. Check speed, endpoint enthalpy and total flux.
3. Run the paper-interpretation pure-flux H control with the pure-root events
   recorded. Compare its energy flux to the partial-flux control at frozen states
   before interpreting a changed speed.
4. Implement reference-8 pure-Cp/pure-h temperature energy as a named approximate
   control; optionally test full mixture Cp with pure h separately. Preserve the
   thermo phase's partial-property API for all other consumers.
5. Compute the pressure-chemistry equilibrium endpoint described above. If the
   total-H flame misses it after domain/grid checks, diagnose conservation or
   finite-domain chemistry before modifying rates.

No coefficient adjustment or fitted flame-speed correction is supported by this
audit. The rich-hydrogen conductivity rule remains a separate unresolved model
choice.

## Evidence and reproduction

Raw state is outside Git:
`state/liang-hydrogen-20261020/energy-sources/`.
`frozen_audit.py WORKSPACE NEW_OUTPUT.json` reads the immutable LJ input and
pilot snapshots, reconstructs enthalpy, scans alpha crossings and evaluates the
pure-species roots. It requires NumPy and Cantera 3.2 and performs no flame solve.
Existing output paths fail.

- Script SHA256:
  `e306f262b6757d618de5d7902ce02d329e279df4bdc2be8d6a19a9636065ba34`.
- Verified output SHA256:
  `d750a70e639176fdf3ff1095a8c6d45df990b21b7b200454d342da1f78a03db5`.
- Reference-8 author PDF SHA256:
  `8104c6f00cb5b610b9ac9776cc4484be5baad39212a027dcd9a68440f8582a31`.
- Liang owner-provided PDF SHA256:
  `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe`.

These local values qualify the diagnosis only. Publication agreement and CFD
deployment remain pending.

## Follow-up after the pure-property pilots

This section adds the reference-10 audit and independent endpoint checks.
The coordinator reported the following phi=1.4 diagnostic results:
pure-temperature job `125070683` gives 78.686 cm/s and 2312.23 K;
pure-flux total H gives 75.495 cm/s; matching the advective stencil with pure
flux gives 75.541 cm/s. These reported results have not been independently
downloaded in this audit. They do not explain the extracted Liang Case 3 value
of 71.8145 ± 0.3311 cm/s.

### Source-supported choices and ruled-out changes

The author manuscript corresponding to reference 10 explicitly defines radical
LJ attraction at the pseudo-critical temperature, then applies a temperature
function. Constant radical attraction would contradict that sequence. Its
original square root uses an absolute value; its preferred smooth alternative is
`sqrt(alpha) = 1 + tanh(s*(1-sqrt(T/Tc)))` above Tc, with the original bracket
below Tc. This is a different model from the 2024 smoothing diagnostic.
[Giovangigli et al., R.I.688, Eqs.39–43](https://www.cmap.polytechnique.fr/~giovangi/688.pdf)

The manuscript prints `s = 0.48508 + 1.5517*omega - 0.151613*omega^2`.
The last coefficient differs from reference 8's `0.15613` and the current
kernel's original-Soave polynomial. The local page rendering verifies that
`0.151613` is printed; it is not an extraction correction. The manuscript is a
July 2010 report corresponding to the 2011 journal article, so a final published
version should be checked before treating this last digit sequence as settled.

Reference 8 writes the square-root bracket without an absolute value, while
its mixture rule writes `sqrt(a_i*a_j)`. Signed brackets in a squared mixture
sum and positive square roots of squared pure attractions cease to be equivalent
above a species' crossing temperature. Liang does not resolve that choice.
A signed-bracket control is therefore an implementation ambiguity test, not a
justified replacement selected by agreement with Figure 3.

The kernel's departure expression is algebraically Liang Eq. (3):
`R*T*b/(v-b)-a/(v+b) = p*v-R*T`. Both cited treatments reference the ideal
enthalpy at the same temperature and composition, with departure vanishing
at infinite volume. Neither calls for subtracting another departure at 298 K.
A composition-dependent reference shift can change reaction heat and should
not be introduced to lower the flame speed.
[Reference 8, Eqs.17–18](https://sirignano.eng.uci.edu/theme/pdfs/39.pdf)

Reference 10 distinguishes pressure-derived ideal concentrations, actual
high-pressure concentrations, a hybrid equilibrium correction, and fully
activity-based chemistry. Our adapter implements its first model. Its molar
source goes directly into `m*Y_i' + j_i' = W_i*omega_i`; no separate `1/Z`
multiplier is specified. The corresponding equilibrium is ideal TP chemistry,
even when SRK enthalpy supplies the energy constraint.
[Reference 10, Eqs.1,15–19,56–59](https://www.cmap.polytechnique.fr/~giovangi/688.pdf)

At fixed T,p,Y, changing Case 2 to Case 3 leaves this adapter's forward,
reverse, third-body and falloff calculations unchanged. The intended changes
are caloric properties and the energy residual. A rate difference in a frozen
Case 2/3 state would be an implementation defect, not the intended staging.

### The outlet composition reveals a numerical conservation defect

An independent Cantera 3.2 calculation reconstructed elemental mass fractions
from the exported species fields. H decreases and O increases between the
inlet and outlet. This occurs in the stock ideal and EOS-only controls as well
as the total-H solver:

| phi | Case 1 relative H change | Case 2 relative H change | Case 3 relative H change |
| --- | ---: | ---: | ---: |
| 1.0 | -0.3342% | -0.3053% | -0.3433% |
| 1.4 | -0.1986% | -0.1803% | -0.1972% |

For Case 3, the absolute H/O changes are respectively
`-9.78818e-5 / +9.94099e-5` at phi=1 and
`-7.78450e-5 / +7.39894e-5` at phi=1.4. A numerical elemental-flux balance,
including the inlet diffusion flux, should determine the exact source of the
defect. Its presence in the stock controls prevents attributing it solely
to our total-H energy equation.

The outlet composition is already in local TP chemical equilibrium: the largest
mass-fraction change after equilibration is `3.95e-11` and `2.87e-13` in the two
Case 3 profiles. Slow terminal chemistry is therefore not a plausible
explanation for their endpoint difference from feed equilibrium.

For each trial temperature, the independent endpoint calculation equilibrated
the exact 21/79 air feed at T,p, added our independently reconstructed SRK mixture
departure, and solved `h(T,Y_eq)=h_in`. Repeating this calculation using the
outlet's elemental composition isolates the measured elemental drift.

| phi | Equilibrium with feed elements, K | Equilibrium with outlet elements, K | Saved outlet, K |
| --- | ---: | ---: | ---: |
| 1.0 | 2472.7262 | 2470.1352 | 2470.1562 |
| 1.4 | 2299.6360 | 2301.4305 | 2301.4456 |

The remaining 0.021/0.015 K corresponds to the small total-H endpoint defect.
Thus the elemental change accounts for the endpoint-temperature discrepancy
almost exactly. This is evidence to qualify the discretization; it does not
demonstrate that the 3.7 cm/s rich-flame speed discrepancy has the same cause.

Using the reference-10 tanh alpha, including its printed coefficient, changes
feed-equilibrium temperatures only to 2472.5213 and 2299.5355 K. A signed-bracket
mixture gives 2470.5908 and 2297.6982 K. These are frozen equilibrium calculations,
not new flame predictions. The alpha tests principally probe the preheat-zone
enthalpy/Cp variation and its numerical treatment, not a large change of final
equilibrium temperature.

### What to test next

The planned explicit grid subdivision should track elemental flux and energy
flux alongside speed. If the elemental defect shrinks, compare extrapolated
speeds before changing caloric or chemical models. Tightening an adaptive
criterion without adding points does not test this.

Use one common equivalence ratio in the overlap of Figures 3 and 5 to judge speed
and temperature together. Current temperature agreement is at phi=1, whereas
the large speed discrepancy is assessed at phi=1.4, outside Figure 5. It does
not yet establish matching rich-flame temperature. Figure 4's ideal inlet
density at phi=1, `0.085522 ± 0.000140 g/cm^3`, independently agrees with our
298 K value `0.0855255`; an inlet-temperature change is not the leading cause.

The pure-Cp temperature pilot disfavors that particular reconstruction of
Case 3*. It does not establish which approximate residual Liang used.
Mixture Cp with pure-species source enthalpies remains a separately named
interpretation, and must not be silently labeled the published implementation.

New state evidence is in `state/liang-hydrogen-20261020/energy-sources/`:

- `element-conservation-audit.json`, SHA256
  `6e195daf0bd1b841616b4592ffa00a5cc4281267b690711e68d65e05b8abd14f`.
- `pressure-equilibrium-endpoint-audit-corrected.json`, SHA256
  `cef4d08cf41b338e71429ffa67bcbc5b33152a5716618126329f4b45c77e0e67`.
  This supersedes the endpoint screening using air ratio 3.76 in
  `pressure-equilibrium-endpoint-audit.json`; the actual driver uses 79/21.
- `ref10-alpha-page.png`, visual verification of the printed Eq.42.
- Reference-10 source PDF is
  `state/cantera-liang-20261019/giovangigli-2011-transcritical.pdf`, SHA256
  `0e93e18d404857f37b49044813dc5adf799781e87735e34f357a3b8171a256c5`.

These checks used frozen local profiles only. They changed no model, submitted
no job, and fitted no parameter.
