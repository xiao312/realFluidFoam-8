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
The direct residual evaluator handles purely diagonal operators without
accessing absent off-diagonal storage. Only the optional legacy-API witness
allocates zero off-diagonal storage after solving, because that API otherwise
aborts on a diagonal matrix. This changes diagnostic storage only.

The equation budget now evaluates cell-integrated `source - A*he` explicitly
from internal and boundary coefficients, counting each coupled neighbour once.
OF8's scalar residual() applies coupled interfaces and then adds their source
again. The retained r5 constant periodic cases exposed this exactly: the contact
error was phi*h plus both cyclic diffusion coefficients times h. The new helper
does not change the solved equation, coefficients or acceptance threshold.
`writeEnergyResidualAudit yes` adds a diagnostic comparison against that legacy
API and the predicted extra coupled contribution. It also reports the initial
absolute residual and independently reconstructed OF8 normalization scale,
alongside the actual solver iteration count. Near-constant fields can make that
normalization scale approach roundoff and hit an iteration ceiling despite a
small dimensional residual; the two facts must be reported separately.
The implementation follows the actual coefficients used by OF8's
[scalar solve](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/fvMatrices/fvScalarMatrix/fvScalarMatrix.C)
and reconstructs its
[normalization definition](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/OpenFOAM/matrices/lduMatrix/lduMatrix/lduMatrixSolver.C).
Runtime and parallel verification remain necessary; reading those sources alone
does not qualify this implementation.
The optional audit also measures the absolute stored matrix summands and a
per-cell scalar operation count. A gamma_n bound (unit roundoff = epsilon/2)
describes rounding in residual evaluation, separately from actual physical
conservation or model error. It does not change the linear solver tolerances,
acceptance thresholds, coefficients, or equation.

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
composition and initial mass flux is rebuilt. Inlet velocity conditions are
reevaluated after the initialized density is set,
so a mass-flow boundary does not retain an ideal-gas placeholder velocity after
an EOS change. Kinetic energy is refreshed from that velocity before the first
energy equation, including its inlet patch values. Fixed-temperature and fixed-Ha
boundaries must represent the same inlet state. The first diagnostic uses
constant transport, not a claim of matched preferential diffusion or real-fluid
physics. Solver controls must include Ha. Sources in fvOptions must explicitly
target Ha if needed.

In absolute mode a fixedValue-class temperature patch must have a fixed-value
Ha patch. After composition refresh and each pressure correction, the solver
updates that Ha value to the executing thermo's patch Hs(p,T,Y) plus ideal
formation enthalpy. This uses the current patch pressure and includes the EOS
departure exactly once. It does not replace a temperature-gradient or insulated
boundary with a fixed energy boundary. The same update occurs at initialization.
Mixed/inletOutlet patches are left to their declared boundary conditions; they
are not treated as fixed temperature merely because `fixesValue()` returns true.
For real-fluid initialization, first use the runtime thermo probe to construct
Ha from fresh prescribed p/T/Y; do not copy ideal-gas Ha into the new EOS case.
Opt-in `fgmRequireHaInitialization yes` requires its time-zero marker and the
same thermoType dictionary before reading Ha. This prevents executing cold-case
placeholder energy; the default remains off for existing analytical/warm cases.
The admitting wrapper must retain the initialized field and runtime hashes.
`fgmProgressSourceEnabled no` is an explicit nonreacting transport diagnostic:
the table still supplies composition, but its progress source is not applied.
It requires absolute-enthalpy mode, where Q is already diagnostic only. The
default is `yes`. Logs retain both tabulated and applied integrated source;
disabled-source runs must not be presented as reacting flame calculations.
Qualification requires a fixed-T pressure perturbation (Ha changes with PR/SRK
departure) and a negative case with incompatible Ha boundary type, as well as
the unchanged periodic heating/contact/conversion checks. These source changes
do not retroactively qualify an earlier executable or result.

This design follows the source-free absolute-enthalpy branch in
[DeepFlame baseFGM at 7cb3294](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/src/dfCombustionModels/FGM/baseFGM/baseFGM.C)
and the hs/ha distinction in its
[energy equation](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/applications/solvers/dfLowMachFoam/EEqn.H).
The compressible kinetic/pressure terms here remain those of OF8. There is no
copied spray source or implicit use of DeepFlame's table-temperature closure.

## Optional source splitting

`fgmSourceIntegration explicit` is the default and keeps the existing source
assembly. Opt-in `strangFixedState` requires global Euler time stepping, enabled
FGM source, absolute enthalpy, and a v2 raw-C table. LTS is refused.
The mesh must remain stationary.

At each physical timestep, the first half source stage uses old C, Z and density
once. The solver keeps the original oldTime fields unchanged. Its source-free
transport equation receives `rho.oldTime()*deltaC_half/deltaT`, which changes the
transport initial state to the cached half-reacted state. Scalar under-relaxation
is omitted on this opt-in transport solve, so previous outer-iteration reaction
cannot enter through an under-relaxed matrix source.

Each PIMPLE outer iteration solves transport from that same initial state.
The second half source stage starts from the freshly solved transport field,
never the preceding outer iteration's reacted field. Composition then updates
through the existing table lookup. Ha remains the energy authority; no extra
chemical Q is added. Existing inlet and coupled boundary conditions remain owned
by the case. Any source-domain exit stops with its event evidence.

The source stages freeze Z and density separately at their input state. Global
Euler transport and variable-density coupling do not give a second-order CFD
method. Refine the physical timestep and compare outer-corrector counts.
The [verification plan](../../../replication/validation/fgm-source-split/README.md)
uses actual table source curves and clean-start 0D/1D cases. Neither a source-ODE
pass nor synthetic tests qualify a reacting G2 calculation.

The history handling follows OF8's
[GeometricField storage](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/OpenFOAM/fields/GeometricFields/GeometricField/GeometricField.C).
The first-stage correction follows the stored `rho.oldTime()*c.oldTime()` source
in its [Euler matrix](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/finiteVolume/ddtSchemes/EulerDdtScheme/EulerDdtScheme.C).
Runtime checks still verify these assumptions with the executing field objects.
# Caloric closure with source stages

`writeFgmThermoClosure yes` recomputes literal executing `thermo.he(p,T)` after
inversion and compares it with stored sensible enthalpy at initialization and
written corrections. It reports internal/boundary maximum errors and internal
RMS in J/kg. The normalized error uses max(1, |h|, |h(p,T)|, |Cp*T|).
The default is off; enabled default limit is 1e-8. Nonfinite/unstable caloric
states or excess error are fatal, without overwriting T or h. This catches
false convergence at a JANAF bound. The source-stage full282 qualification uses
1e-8 with its 1e-9 temperature iteration tolerance. Original polynomial ranges
and any explicit diagnostic extrapolation remain separate input records.
