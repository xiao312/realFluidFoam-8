# Transported-Z reacting solver

This experimental executable adds mixture-fraction transport to the fork's
reactingFoam and consumes the registered FGM progress and composition fields.
The base reactingFoam executable remains unchanged. It is not yet qualified for
reacting MASCOTTE predictions.

The case supplies the usual OF8 dictionaries and, for `fgmTable`, `Z`, `c`,
species fields and a table. The table supplies species, progress production and
volumetric heat release. The thermophysical model owns density, temperature and
sensible energy. Positive `Qdot` on the energy equation's right side heats the
fluid. A mass-fraction progress source already has units kg/m3/s; it must not be
multiplied by density again. A single constant normalization span is supported;
a mixture-fraction-dependent normalized coordinate is not implemented.

The v2 table interface instead transports raw C and normalizes only lookup
coordinates using Cmin/max(Z). Progress and energy sources are captured at the
same pre-progress-solve state. Composition is refreshed after solving C and
before energy inversion, avoiding output species from the preceding C state.
The source written by the model after this refresh can differ from the source
actually assembled; `energyEquation sourceW` records the latter. Z and C join
the multivariate convection field list. This ordering still requires physical
verification; it does not make a projected table composition exactly equivalent
to solving every species equation.

`writeEnergyBudget yes` in `controlDict` enables equation-stage and end-step
records in the solver log and writes the actual `rho` and `he` fields. The
`energyEquation` records report domain-integrated assembled terms in watts,
before pressure correction or thermodynamic reconstruction. `energyState`
reports actual discrete state integrals in joules and kilograms. Diagnostics
retain additional matrices, so leave them disabled for routine production.

Dependencies are the fork's combustion, thermophysical and transport libraries
and OF8 finite-volume libraries. The module reads case files only; it does not
handle secrets, submit jobs or choose remote paths.

Build in the qualified Linux OF8 environment with `wmake` in this directory.
Run `reactingFoamSolveZ -case CASE`. The direct verification module at
`replication/validation/fgm-of8/direct-verification` supplies small, clean-start
heating and passive-scalar transport cases and analytical checks. A successful
build alone is not a physical verification result.

## Absolute enthalpy FGM mode

The opt-in `fgmEnergyForm absoluteEnthalpy` setting in controlDict transports
`Ha=hs+sum(Yi*Hfi)` with pressure work, kinetic-energy terms and the selected
unity-Lewis enthalpy diffusion. Chemical Q is omitted from this equation and
retained as a diagnostic. After solving, `hs=Ha-sum(Yi*Hfi)` is passed to the
thermophysical inversion. This closes chemical energy even when projected
table composition does not have exactly the same source tangent as tabulated Q.
The default `sensibleEnthalpy` path retains the existing equation.

Absolute mode requires an explicit time-zero `Ha` field and its boundary
conditions. It must use sensibleEnthalpy thermodynamics and Fourier or
eddyDiffusivity transport; other diffusion closures are refused. Ha is the
initial energy authority, so initial T is recomputed from Ha and the table's
composition and initial mass flux is rebuilt. Fixed-temperature and fixed-Ha
boundaries must represent the same inlet state. The first diagnostic uses
constant transport, not a claim of matched preferential diffusion or real-fluid
physics. Solver controls must include Ha. Sources in fvOptions must explicitly
target Ha if needed.

This design follows the source-free absolute-enthalpy branch in
[DeepFlame baseFGM at 7cb3294](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/src/dfCombustionModels/FGM/baseFGM/baseFGM.C)
and the hs/ha distinction in its
[energy equation](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/applications/solvers/dfLowMachFoam/EEqn.H).
The compressible kinetic/pressure terms here remain those of OF8. There is no
copied spray source or implicit use of DeepFlame's table-temperature closure.
