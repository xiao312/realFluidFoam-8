# Transported-Z reacting solver

Optional `fgmPostIgnitionMaxDeltaT SECONDS` caps the adaptive global timestep only
after the configured scheduled ignition. The default `-1` disables it and retains
the original arithmetic. Enabled values must be finite and positive, with a
fresh scheduled split-FGM/absolute-Ha case and adaptive global timestepping.
The cap applies inside the event's initial timestep reset and after every later
`readTimeControls`, before `setDeltaT`; cold transit is unchanged. It changes no
field, chemistry, source, pressure/density repair, or final acceptance criterion.
This is an explicit temporal-resolution diagnostic for a newly frozen zero-time
case, not a way to relabel or continue a failed state. No external dependencies
or secrets are involved. Example: `fgmPostIgnitionMaxDeltaT 2e-9;` alongside a
scheduled ignition. Qualify compile/link identity, actual default-off field parity,
rejection of invalid values and an enabled physical ignition control whose first
and subsequent accepted timesteps respect the cap, then execute the real case
through the Slurm adapter. A tiny timestep alone does not establish convergence
or physical agreement.

Optional `realFluidConservativePressureDamping yes` limits a pressure correction
that would consume more than90% of the continuity-based reference cell density.
It blends pressure and mass flux by the same global factor, then solves the
original density equation. No density, temperature, species or energy is clipped.
Only global Euler on a fixed mesh with empty fvOptions, compressible
rho/Ha coupling, conservative transport density and pressure/thermo refresh is
supported. Inputs are current/old density, previous/candidate flux and pressure;
outputs are a damped nonlinear trial and its factor. A damped trial requires
another pressure solve; it cannot complete the pressure/property iteration.
The final undamped solve and all original closure/acceptance checks remain.
Exhausting `maxRhoHaPressureIterations` still rejects and saves the state.

This is an experimental admissibility step, not a proven pressure-equilibrium
method or residual-based Armijo search. The reference Euler state must already
be positive; nonfinite states and unsupported configurations fail explicitly.
It follows the general principle of rejecting nonlinear steps outside a physical
domain rather than weakening that domain (PETSc SNES documentation:
https://petsc.org/main/manual/snes/). No PETSc dependency or code is introduced.
Default-off execution allocates no reference fields and retains prior arithmetic.
Example control: enable this option on the qualified densityHaDifferential case
and allow20pressure/property iterations. Verify default-off actual-field parity,
the shared factor's conservative/positive witness and rejection of invalid input,
then repeat the exact originally failing G2case from timezero. A numerical
witness or successful compilation is not injector/flame validation.

Optional `writeInvalidSourceState yes` saves the current rejected p/T/rho/Ha,
progress, Z, velocity/flux and species immediately before a source stage receives
invalid density. It does not repair density or replace the source integrator's
existing refusal. Such files are rejected nonlinear states, never accepted
timesteps or restart inputs. Default-off behavior performs no additional scan.

Scheduled ignition optionally accepts `fgmIgnitionAxialOrigin` in raw mesh metres
(default0). Its region is `[origin, origin+fgmIgnitionAxialLength]`, retaining
local Z, absolute Ha and the existing source-peak/upper-progress choice. The
reviewed legacy injector exits at raw x=.01m; using the old default would ignite
an upstream passage. Log selected cell count and actual min/max x. This is a
same-process event following original-zero cold flow, never a saved-state restart.
No new thermodynamic model, threshold, library ABI or dependency is introduced.
Verify compiled default-origin parity and shifted-region selection in a physical
zero-flow control, then fresh injector cold-flow/ignition with measured budgets.
An ignition event changes composition/density numerically; retain its mass and
Ha accounting. It is not a paper-defined ignition procedure or acceptance.

Experimental `realFluidDeferCaloricTrialAudit yes` distinguishes an unfinished
coupled iterate from an accepted timestep. It requires absolute Ha, the inner
scalar/energy loop, pressure refresh and enforcing audit. Energy and
pressure subiterations report caloric discrepancies without immediately
terminating; nonfinite/nonpositive thermodynamic trials still terminate. After
the complete PIMPLE loop the unchanged original internal/boundary caloric
criterion is enforced, before energy reporting or timestep output. A final
failed state is saved and rejected. Predictor mechanical/root checks, pressure
retry bounds, old-time source anchors and default-off behavior are unchanged.
This permits a later energy correction to respond to the trial pressure; it
does not guarantee that such a correction exists. Qualify default-off parity,
physical inner-count controls and fresh-zero failed-flow reproductions before
making claims. No library ABI, EOS or acceptance-limit change is introduced.

`writeFgmSpeciesTransportAudit yes;` is a default-off, read-only predictor
diagnostic. It reports the raw negative species, existing clipping addition,
sum before/after clipping (excluding the closure species), implied unclipped
closure and dimensionless continuity defect before table relaxation. If the
nonclosure sum exceeds1+1e-8, it retains the actual predictor fields; these are
not authorized restart inputs. It changes neither the existing closure formula
nor the model's positivity/sum/caloric criteria. Inputs: existing species,
rho/phi and time; outputs: logs/diagnostic snapshots; no new dependency or ABI.
`speciesTransportAudit.H` owns only this diagnostic, called from `YEqn.H`.
Verify a solver-only build against pinned libraries, actual default-off parity,
then fresh-zero physical controls comparing predictor defects and acceptance.
Compilation alone is not scientific validation. No secrets or network access.

## Relaxed table target candidate

The experimental `relaxedTable` model transports actual species and Z, then
relaxes the pure-mixing species predictor toward a fixed table. It retains
absolute Ha and uses formation-enthalpy change as diagnostic Qdot only. Cr100
follows Schmitt Eq.12; the first target remains the existing finite-chi profile,
so it does not claim the paper's exact equilibrium/PDF/LES closure. See the
model's local README for configuration and qualification boundaries.

The optional fixed-time source diagnostic shares `relaxationClock.H` with the
model's one-cell probe. It retains the default paper Cr100 mode, absolute-Ha
equation and all field/thermo criteria. Probe CSVs append the selected mode and
source time. A matched-alpha comparison must preserve the original recurrence;
physical cases must separately test timestep/source-clock sensitivity from zero.

The combustion lifecycle interface now distinguishes transported Z from
prescribed composition and declares absolute-Ha support explicitly. Existing
models inherit their old behavior. This interface changes the custom-library
ABI: qualify a complete frozen rebuild before running any candidate. The
existing qualified934/R37 baseline must remain intact.

## Experimental constant-background low-Mach model

Default-off `realFluidLowMachPressureSplit yes` separates uniform EOS pressure
`p` from momentum/projection pressure `pMechanical`. It requires an explicit
positive `realFluidThermodynamicPressure` (Pa) matching the original time-zero
pressure and sensible-enthalpy thermodynamics. It transports thermal enthalpy
without kinetic-energy or dynamic-pressure-work terms. Absolute-Ha composition
coupling and all caloric/species acceptance limits remain unchanged. This is a
separate governing-equation approximation, not a compressible-solver repair.

Inputs are the usual original-zero case, the two control entries, and pressure
solver/scheme entries for `pMechanical` and `pMechanicalFinal`. Closed/periodic
cases also supply `pMechanicalRefCell` and `pMechanicalRefValue` in PIMPLE.
The solver writes both pressures and reports actual SRK sound-speed Mach,
mechanical-pressure departure, EOS/transport-density discrepancy and mass
residuals. Compare mechanical pressure with contact/paper pressure; a uniform
EOS pressure alone is not a pressure-equilibrium pass. Thermal H is the relevant
constant-p0 energy budget; H+K-p0V remains a state diagnostic, not an exact
conserved target of this approximation. Large Mach or mechanical-pressure
departures invalidate the intended asymptotics and must remain visible.

No library ABI or external dependency changes. `createLowMachPressure.H` owns
field selection/configuration; `lowMachPressureAudit.H` owns model diagnostics.
No secrets or scheduler operations. Unsupported transonic/LTS, internal-energy,
or simultaneous differential-density pressure modes fail explicitly. This
model does not cover acoustics, varying background pressure or closed-vessel
thermodynamic-pressure evolution.

Minimal example: set `realFluidLowMachPressureSplit yes;` and
`realFluidThermodynamicPressure 6000000;` in a fresh contact controlDict, and
add matching `pMechanical` solver controls. Build with qualified OF8 `wmake`.
Verification requires an exact default-off control against c73e176, then fresh
oxygen/mixed contacts measuring pMechanical/U, caloric closure, density and
thermal conservation. Compilation or terminal0 alone is not model validation.
Runtime qualification is pending at the introduction of this option.
The first R45 app compiled/linked, but its low-Mach branch failed physically:
one case exited0 with catastrophic mechanical velocity/density. A copied psi
coefficient retains old-time storage in OF8; zeroing its current field cannot
represent an absent compressibility time term. The revised projection uses a
stationary zero diagonal and logs the copied-history witness. R46 confirmed
the nonzero old coefficient and qualified build/link/runtime linkage; both
default-off controls exactly matched R43 fields. Its physical model still
failed: mixed contact crashed near87.9us; oxygen reached3ms with24.5% mechanical
pressure departure and53.2% velocity error. No reacting G2 applicability or
contact-physics pass is established. Terminal0 is insufficient.

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

The separate `steadyFlamelet` model does not transport c. It maps a single
physical fixed-dissipation profile from transported Z, then refreshes composition
before the absolute-Ha equation. `cEqn.H` is entered only when the selected model
reports `transportsProgress()`. The established FGM lifecycle is unchanged.
Steady-flamelet cases require explicit/no-progress-source mode and full SRK
enthalpy inversion; tabulated Q and T remain diagnostics. They are laminar
delta-PDF diagnostics, not qualified turbulent paper replication. See the model's
local README for table ownership and approximation/provenance requirements.

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
every energy correction. Successful summaries are emitted at written times;
failures are emitted immediately, even between field writes. It reports internal/boundary maximum errors and internal
RMS in J/kg. The normalized error uses max(1, |h|, |h(p,T)|, |Cp*T|).
The default is off; enabled default limit is 1e-8. Nonfinite/unstable caloric
states or excess error are fatal, without overwriting T or h. This catches
false convergence at a JANAF bound. The source-stage full282 qualification uses
1e-8 with its 1e-9 temperature iteration tolerance. Original polynomial ranges
and any explicit diagnostic extrapolation remain separate input records.

The audit runs immediately after thermo inversion, before the following pressure
equation updates pressure. For a nonideal EOS it therefore qualifies inversion
closure at that stage, not final post-pressure consistency or PIMPLE convergence.
The latter still needs coupled residual and outer-iteration diagnostics.

At written timesteps, `thermoPostPressureClosure` records the same measured
quantity after the final pressure correction. It is a separate report-only
witness: no field is changed and the inversion limit is not enforced there.
Nonideal pressure dependence can produce a departure after a successful
inversion; compare this drift under timestep and PIMPLE-outer refinement.
The `limit` field is retained only as the inversion diagnostic's reference
scale, not as post-pressure acceptance. Invalid counts remain visible.

# Optional wall-time attribution

`writeFgmTiming yes;` in `system/controlDict` enables a local steady-clock
diagnostic; the default is off and the setting is read once at solver startup.
The timer is declared in `createFields.H`, before field initialization. OF8 also
includes this header through its post-processing path, so initialization timing
must not depend on a variable declared only in the normal solve path. That path
does not emit a timing summary or add a gather.
It does not change equations, solver tolerances, guards or model selection.
It times startup after mesh creation, complete steps, the main equations,
source half-stages, reaction/table updates, thermo correction, caloric checks,
energy bookkeeping and field writes. Equation/step categories are inclusive:
for example energy includes thermo correction and its caloric audit, while
progress includes the second source stage and subsequent table update.
Source stages include their field copies/history checks and boundary updates,
not only the scalar ODE kernel. `continuity` is the standalone step-start density
solve; density solves inside pressure correction are included in `pressure`.
`reactionCorrection` includes actual model/table updates in species/progress
equations. Constructor work remains part of `startup`.

Each region uses local clock reads only. At existing field-write points and
normal termination, one Pstream gather collects the cumulative seconds, call
counts and longest individual call from each rank. The master writes explicit
`fgmTimingRank` records and `fgmTimingCategory` records with rank-0 and maximum
values, plus the rank responsible for each maximum. Different maxima may come
from different ranks; their sum is not a critical path or job wall time.
Times include waits already present in the measured code. Reporting itself is
outside the step/region counters but inside elapsed time since timer creation.
No new synchronization occurs at region boundaries. A fatal path retains only
previous complete summaries; no destructor attempts an unsafe MPI gather.

Dependencies are C++ steady_clock and existing OF8 Pstream/List interfaces;
there are no files, network operations, secrets or library ABI changes. The
initial thermo constructor is included in startup rather than attributed to
thermo.correct. Allocation setup, meshing and compilation are outside this
instrument. No timing is a scientific acceptance result.

Minimal use: add `writeFgmTiming yes;` to a new time-zero qualification case,
run the exact rebuilt solver and retain its log. Read-only checks before an
allocated build are `git diff --check` and review of the timing-only diff.
The intended allocated check is a small existing physical case with timing off
and on: the fields and scientific verdicts must agree, enabled logs must contain
finite nonnegative counters, and rank identities/call counts must match the
executed serial/MPI configuration. Compilation and that parity check remain
pending until an admitted run supplies evidence.

The `fgmZEndpoint` diagnostic subtracts0/1 before formatting the actual global
Z range. It records out-of-range magnitudes without changing Z or its equation.
This separates floating-point endpoint representation from material overshoot.

The default-off `writeMixtureFractionBudget` diagnostic records the exact
assembled Z residual, its ratio to the effective diagonal, and cellwise
`ddt(rho)+div(phi)` after the scalar solve. A private constant-one field checks
the conservative operator identity with the same density/flux and patch types.
It changes neither Z nor rho. Each rank reports its worst out-of-range cell,
coordinates, old/current Z and density, diagonal, residual and a separately
reassembled post-solve diffusion witness. That last value is not a stored
deferred correction for a nonorthogonal scheme. These reports distinguish
iterative error, continuity mismatch and transport behavior; they impose no
acceptance criterion or lookup-bound change. The stock compressible continuity
message instead compares density with its EOS value and is not this residual.

The opt-in `conserveTabulatedDensity yes;` control is a pressure-correction
candidate for tabulated composition. Its default is off; selecting it with a
non-tabulated model is an error. OF8 `pressureControl::limit()` returns true
whenever pressure limits are configured, even when it changes no pressure.
The inherited caller then replaces continuity-solved density with EOS density.
Job126434026 measured a resulting local continuity defect that predicts the
mixture-fraction overshoot; tightening the scalar solve did not remove it.

The candidate retains that pressure/EOS update and then solves the unchanged
conservative density equation again before the next outer scalar solve. It does
not add a scalar source, alter pressure bounds or modify Z. With
`writeMixtureFractionBudget yes;`, stage-labelled continuity records bracket the
EOS replacement and the optional density solve. Both controls are in
`system/controlDict`; no new dependency, network access or secrets are involved.
Verification requires a solver-only allocated build, a fresh baseline that
reproduces the defect, and a separate fresh candidate retaining the existing
endpoint and conservation checks. No runtime qualification is claimed here.
Use the same original Z tolerance in the two cases; the tighter tolerance was
not a cure. This change does not alter the separate end-of-step EOS assignment:
the next timestep still begins with the existing continuity solve. The audit
brackets it as `beforeFinalEOSDensity` / `afterFinalEOSDensity`. Its effect
on the reported final-state energy/mass balance remains an explicit coupling
diagnostic, rather than being silently included in this pressure-loop repair.
The upstream return-value contract is visible in
[OF8 pressureControl.C](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/cfdTools/general/pressureControl/pressureControl.C).

`projectTabulatedZRoundoff yes;` is a separate, default-off numerical policy.
It requires tabulated composition and `conserveTabulatedDensity yes;`. After
each Z solve, the original algebraic audit runs first. A global scan then
refuses nonfinite Z, invalid positive density/volume weights, or any internal
or boundary excursion larger than exactly64 double-precision epsilon. Nothing
has been projected on any rank at that refusal. Within that unchanged bound,
only internal Z values outside0..1 are set to the corresponding endpoint;
oldTime and prescribed boundary values are never changed. Boundary conditions
are reevaluated and checked. This differs from the existing lookup-only policy,
which leaves the transported field unchanged and allows ulps to accumulate.

Every call reports actual pre/post global extrema, corrected cell count and
maximum delta, signed/absolute sums of rho*V*deltaZ, and cumulative signed/
absolute mass corrections over all outer solves. `fieldsModified` explicitly
identifies correction. These are recorded changes to transported mixture
fraction, not exact scalar conservation. The pressure, energy, lookup and
material-overshoot criteria are unchanged. Fresh100us qualification must retain
this ledger and the independent conservation audit; bounded interior cases
must remain unchanged. The header probe exercises the same decision routine
at0/1,64/65epsilon and the retained4e-9 material error before actual CFD tests.
Compile/run it in the admitted allocation with `g++ -std=c++11
zRoundoffProbe.C -o zRoundoffProbe && ./zRoundoffProbe`. No new runtime library,
network access, input file, credential or model ABI is introduced.

The subsequent `fgmZEndpoint` line is report-only and records whether the
roundoff policy is enabled. Actual field changes and their mass correction are
reported by `fgmZRoundoffProjection`; the endpoint line does not claim that an
earlier projection left Z unchanged.

Optional `fgmThermoCorrectionPasses` (integer1..3, default1) repeats the selected
thermo's energy-to-temperature inversion at unchanged internal sensible enthalpy.
It is intended to refine OF8's temperature-step stopping near a NASA polynomial
switch; coefficients, energy and caloric acceptance limit are unchanged. Each
extra pass verifies and reports zero internal h mutation. Maders selects2 only
after an actual-runtime switch probe. No new dependency or network/secrets.
Verify thermo_switch_probe.C in the selected fresh case, then the actual clean-
start flow; compile success alone does not qualify closure or paper agreement.
The Foundation OF8 thermoI.H T() stops on temperature increment, so a small step
crossing a discontinuous polynomial switch can require a second correct().

## Scheduled cold-flow ignition

Optional `fgmIgnitionTime` (seconds, default negative/disabled) enables a cold-flow
stage and one ignition event in the same timezero process. This requires the
existing raw weighted-C FGM, global time and absolute-enthalpy mode. Until ignition,
both source half-steps have zero duration; transport and thermo still evolve.
The case supplies `fgmIgnitionTable`, `fgmIgnitionAxialLength`, and Z min/max.
The ignition reader uses the same validated table format. For each selected cell,
its current Z identifies a source curve and the positive source maximum sets C.
No Z, inlet boundary, absolute enthalpy or historical CFD state is fabricated.
A50ms cold-flow Z/U-change diagnostic and the ignition mass/enthalpy jump are logged.
The hook runs before advancing the clock so oldTime for the next transport step
includes the ignited state. This is numerical ignition, not a new chemical model.
Dependencies are the existing FGM reader and thermo modules; no network/secrets.
Example: `fgmIgnitionTime 0.9; fgmIgnitionTable "constant/physical.tbl";`.
Verify with a compiled staged cold-flow run: zero cold source, exactly one ignition,
unchanged Ha at ignition, runtime EOS correction and continued reacting evolution.

For controlled ignition sensitivity, `fgmIgnitionMode` is `sourcePeak` (unchanged
default) or `upperProgress` (the local upper table progress state). Both preserve
specific absolute enthalpy, use one event and log the selected mode. The latter is
an ignition diagnostic, not an equilibrium-chemistry replacement or a claim that
the author used that state. Compare sustained reaction after the event, not the
prescribed ignition temperature. Reproduce the original extinction before using
this control as evidence. The Z region remains separately configurable.

Scheduled ignition also requires numerical state consistency. Default-on
`fgmIgnitionNumericalReset` reconstructs phi from the changed density/current U,
applies the existing MRF relative-flux operation, resets the event timestep to at
most `fgmIgnitionDeltaT` (default1e-6s), and reruns the existing Courant/adaptive-step
selection before time advancement. Existing Ha ownership/equation is unchanged.
The event logs old/new dt, pre-refresh Courant and changed internal mass flux.
Explicit `fgmIgnitionNumericalReset no` reproduces the original event ordering for
a matched control. Check actual following-step Co/temperature histories; this
initialization correction alone is not proof of a stable flame or paper agreement.


## Non-tabulated contact verification

Energy-state diagnostics omit cmean when the selected model has no c field;
they never invent a zero progress measurement. Tabulated diagnostics retain the
same cmean expression and units.

Only tabulated composition models enter ZEqn. Direct-species and none models do
not construct a Z field and retain the ordinary species/energy path. The existing
tabulated FGM equation order is unchanged. Nonreacting H2/O2 contacts have zero
species formation enthalpies, so their sensible h and absolute Ha share the same
reference. This does not change reacting absolute-Ha ownership. Verify an actual
none-model Schmitt contact without Z and a fresh tabulated G2 startup against the
same compiled libraries. Compilation alone is not physical validation.

On an enforcing caloric failure, the solver logs each rank's worst internal
cell (p,T,h,evaluated h,Cp and non-negligible species) and writes the failed
T,p,h,Y state at its actual time. These diagnostic snapshots preserve the
original failed verdict and must never be relabelled as time-zero CFD inputs.
No equation, caloric threshold, or success-path field is changed by this output.

Experimental conserveTransportDensity yes applies the existing post-pressure
continuity re-solve to non-tabulated contacts too. Its default is the legacy
conserveTabulatedDensity value. Conflicting explicit values are rejected; the
legacy option still requires a tabulated model, and Z projection still requires
tabulation. This selects the existing density equation, changes no EOS, energy
reference or caloric threshold, and is not proof of pressure-equilibrium recovery.
Compare stage-labelled continuity and actual paper profiles before acceptance.

## Experimental author pressure-time correction

`realFluidDensityTimeCorrection yes` in controlDict selects the density-time
correction used by the upstream realFluidFoam pressure equation. The default is
no and preserves the existing psi-product operator. The selected pressure time
operator becomes fvc::ddt(rho)-fvc::ddt(psi,p)+fvm::ddt(psi,p). No EOS parameters,
absolute-Ha transport, source terms, density-restoration policy or acceptance
limits are changed. The first timestep/write records which operator was used.

This ports only the pressure time term. Upstream realFluidFoam also puts species
and energy solves inside the pressure corrector loop; this option does not yet
change that ordering and must not be described as the complete published PIMPLE
algorithm. The source reference is the unchanged upstream files at674468c.

Inputs/dependencies remain the existing OF8 time operators and controlDict;
outputs remain pressure/flux/density diagnostics. No network or secrets are used.
Build with wmake, verify exact parent15-library linkage, then compare separate
fresh uniform/interface controls with the flag off/on. Follow with independently
fresh G2 condition sets. All original EOS/caloric checks and failed states remain.
Compilation and the opt-in setting do not qualify a reacting-G2 prediction.

## Experimental inner scalar/energy correctors

`realFluidInnerThermoCorrectors yes` moves the existing species, transported-Z,
composition refresh and energy block inside each pressure correction, following
the upstream realFluidFoam placement of Y/energy. The default remains no. The
pressure-time correction is an independent switch, permitting isolated tests.
The equations, time-old fields, absolute-Ha basis and numerical acceptance limits
are unchanged; this changes nonlinear coupling order and work per timestep.

Initial scope is combustionModel none or steadyFlamelet. Finite-rate ODE and
transported-progress/source-splitting lifecycles need separate qualification;
repeated source integration must not silently advance chemistry multiple times.
Use those modes with the existing default until their inner lifecycle is tested.
`solveScalarsAndEnergy.H` is deliberately a multi-include statement block, without
an include guard, used inside mutually exclusive runtime scopes.

Verification is a matched flag-off/on fresh interface experiment with the same
qualified parent libraries, followed by independently initialized G2 cases. A
normal exit alone does not establish mass/energy conservation or paper agreement.


## Experimental SRK pressure density slope

realFluidDifferentialPressure yes replaces only the nontransonic global-time
pressure matrix's density linearization. Default no preserves existing behavior.
The coefficient beta=(partial rho/partial p) at fixed T,Y is computed analytically
from the executing SRK mixture coefficients and its selected density root. The
matrix is ddt(rhoEOS)-explicit_ddt(beta*p)+implicit_ddt(beta*p). Freeze the explicit
offset once per pressure assembly so nonorthogonal passes do not shift the
linearization reference. This is not a replacement psi=rho/p field or an EOS fit.

Initially only the exact sensible-enthalpy SRK Chung mixture, global time and
nontransonic pressure form are supported. Unsupported combinations fail with an
explicit message. Negative/nonfinite slopes are retained as failures, never
clamped or absolute-valued. This is an isothermal matrix slope, not the complete
fixed-Ha coupled Jacobian. Energy equations, chemistry, inversion and caloric
thresholds stay unchanged; no density/energy projection is introduced.

Inputs are the existing executing mixture and one controlDict switch; output
includes startup/write slope-to-rho/p ranges. The helper owns only this pressure
preconditioner. No network, secrets or separate property database are involved.
Verify the algebra against the retained coefficient/finite-difference audit,
compile against the exact parent runtime, then compare independent fresh off/on
O2 and mixture contacts. A normal exit is not paper or conservation acceptance.


## Experimental cold-contact energy projection

realFluidColdEnergyProjection yes is a separate, default-off nonreacting contact
experiment. After the energy solve, before thermo inversion, it reconstructs T
from transported rho, current p and Y using the executing SRK coefficients. In
the strongly nonideal region Z=p/(rho*R*T)<0.9 it replaces sensible h with the
executing Hs(p,T). This deliberately changes the energy discretization and logs
the signed/absolute rho*delta_h*cellVolume for every application. That adjustment
is not exact energy conservation and must not be hidden inside an inversion.

This follows Schmitt2020 Eq25's cold-region stiff energy-relaxation idea, but the
filter and placement differ: our finite-volume energy transport is followed by
projection inside the pressure loop, rather than AVBP artificial-viscosity splitting.
Do not describe it as an exact port. Boundary fields retain their configured
conditions. The target temperature must reproduce the executing selected EOS
root to the existing1e-8 density criterion; no root/range clipping is permitted.

Initial scope: combustionModel none, sensible enthalpy and the exact SRK Chung
mixture. Reacting/FGM application needs a separately verified absolute-Ha/source
budget and is not enabled by this experiment. The original caloric audit still
runs after thermo correction. Inputs are existing rho,p,Y and one switch; outputs
include adjusted h,T and explicit correction witnesses. No external data/secrets.

Verification: fresh off/on O2 and H2/O2 contacts with unchanged mesh, properties,
transport, timestep and1e-8 closure checks. Only after short controls complete
prepare independent20ms cases and compare paper profiles, mass and energy defects.
The earlier differential-pressure-only candidate failed and stays disabled here.


realFluidProjectionRegion cold|all selects the projection mask; cold remains the
default Schmitt-inspiredZ<0.9 region. The all setting is a nonreacting diagnostic
of mask-induced pressure-equilibrium errors, motivated by the independently
qualified all-cell contact double-flux control. It is not a fitted threshold and
must not be enabled for reacting/FGM production: Schmitt explicitly cautions that
all-region nonconservative treatment can produce temperature errors. Both modes
retain exactly the same EOS-root, caloric and temperature-range checks and report
all applied energy adjustments. Verify independent fresh1ms then20ms controls;
a short normal exit is insufficient (both R29 short families passed but all six
longer controls failed). The existing nonreacting-only scope remains enforced.


## Experimental post-pressure property refresh

realFluidPressureThermoRefresh yes, default no, calls thermo.correct immediately
after each pressure solve at held internal sensible enthalpy. EOS density is
assigned only when conservative transport density is not selected. The existing boundary-Ha update follows it.
The initial diagnostics use nonreacting/global-time/nontransonic contacts. The
operation changes the nonlinear pressure/energy coupling order, not chemistry
integration, EOS parameters or the transported energy equation. Internal h must
remain unchanged, as in the existing energy-inversion refinement check. The same
caloric audit enforces the returned state and continuity is measured after the
EOS density update; no mass-conservation pass is inferred from caloric closure.

This tests a remaining lifecycle issue: psiThermo::rho returns cached p*psi,
so changing pressure alone does not perform a fresh nonlinear EOS evaluation.
Compare four independent3ms mixed controls: refresh off/on crossed with2/12 outer
correctors, plus oxygen anchors. Keep transport/mask/limits fixed and retain all
failed states. Increased outer corrections are nonlinear iterations within the
same physical timestep, never repeated chemistry advances or a CFD restart.
Inputs are existing controlDict/thermo fields; outputs are updated T/psi/rho and
closure/continuity witnesses. No network/secrets or new dependencies are involved.
Build against the exact parent runtime and inspect normal-exit profiles and
budgets before any scientific or reacting-FGM qualification.


The R33 G2 smoke regression exposed a policy interaction: unconditional density
replacement after property refresh undid the continuity correction and produced
Z overshoot on the first timestep. Refresh now preserves continuity-consistent
rho when conserveTransportDensity is selected, including the final step update.
Thermo cache and transported density differences are reported explicitly; this
preservation is not a claim that EOS and mass density have converged. The fixed
Z bound and caloric checks are unchanged. Verify the actual original-case smoke
from zero before proceeding; do not classify the old MPI-abort aftermath as the
primary failure or reuse its evolved fields.

## Experimental fixed-enthalpy pressure increment

With `realFluidDifferentialPressure yes`, the optional control
`realFluidPressureDensityConstraint enthalpy;` selects the fixed-h,Y density
tangent. The default `temperature` retains the earlier isothermal experiment;
all normal runs with differential pressure disabled remain unchanged.
Only nontransonic global-time operation is supported, as before. Invalid
constraints or nonpositive/nonfinite caloric derivatives fail explicitly.

At fixed composition the new helper evaluates
beta_h=(Cv*beta_T+alpha)/Cp using the executing SRK mixture, where
beta_T=(partial rho/partial p)_T and alpha=-(partial rho/partial T)_p/rho.
The existing offset pressure-time operator keeps its current reference density;
the EOS psi field is not overwritten with beta_h because psiThermo::rho uses
p*psi. Post-pressure exact held-h refresh remains a separately selected control.
No temperature projection, chemistry change, phase rule or caloric bound is added.

Inputs are explicit controlDict values and the actual SRK p/T/Y state. Outputs
are the selected pressure increment and logged density-constraint/slope ratios.
The helper is shared with the probe's finite-difference audit; it adds no library
ABI, network, credential or external dependency. Example controls are the two
entries above plus the existing `realFluidPressureThermoRefresh yes` for a
separately identified pressure/enthalpy coupling experiment.

Verification: build and qualify the exact solver/probe against one full runtime,
replay fixed-h finite differences, then fresh nonreacting contacts and bounded
G2 controls with unchanged closure/continuity limits. R39's original audit is
partial:24/24 rows passed at pressure step1e-4, but7/72 rows failed across all
three step sizes. This supports a labelled development experiment, not approval.

The Z endpoint pre-lookup scan also requires finite positive transported rho,
cell volume and rho*V. A valid Z range does not imply that these other checks
passed. The failure-only `fgmZInvalidTransportState` report captures stored
p/T/Hs/Ha/rho/oldRho/Y and location for up to16 invalid cells per rank. It does
not recompute an EOS, mutate a field or change any validity/roundoff limit.
Qualify this solver-only diagnostic against the consistent combustion ABI,
then replay the exact fresh case; it does not qualify the failed state.

## Optional mass-predictor timestep bound

`limitDensityPredictorTimeStep yes` restricts the proposed global Euler step
before Time advances. For source-free mass continuity on a fixed mesh,
`rhoPredictor = rhoOld - dt*div(phiOld)`. A cell with positive net mass outflow
therefore requires dt<rhoOld/div(phiOld), independently of the usual half-sum
convective Courant convention. The bound uses a fixed numerical margin0.9,
then takes the global minimum and the existing proposed step. It changes only
deltaT, never rho, p, T, species, fluxes or validity/acceptance criteria.

Inputs: accepted transported rho, actual mass phi, immutable controls. Requires
adaptive global Euler, fixed mesh and empty fvOptions (no unaccounted mass
sources). Outputs: selected deltaT and proposed/selected mass-depletion ratios.
This owns only the initial explicit continuity predictor; it does not guarantee
later pressure/scalar iterates, cure a caloric branch gap or qualify paper means.
Dependencies: the existing FV divergence/MPI reductions/Time API. No new library
ABI or external dependency. Defaultoff preserves the old timestep path.

Verification: replay the actual R58 failed Euler cell with its stored old/new
rho and deltaT; its previous proposed mass loss exceeds unity. Then compile
and run independent original-zero Cr1 Schmitt/Cavalieri cases with unchanged
physics, maxCo, field checks and source settings. Retain original failures and
any later new failure; successful predictor admissibility is not science approval.

The mass predictor equation is verified against the official OF8 source:
https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/cfdTools/compressible/rhoEqn.H
The fvOptions emptiness check explicitly selects fv::optionList because the
options wrapper also inherits IOdictionary. No constraint/source is ignored.

## Caloric-failure evidence

When the existing enforcing caloric check fails, `fgmThermoClosure.H` retains
the stored thermodynamic fields and species. It also writes available registered
transported density, absolute enthalpy, kinetic energy, coordinates, velocity
and mass flux (`rho`, `Ha`, `K`, `Z`, `c`, `U`, `phi`). These are existing
objects, not values reconstructed from the EOS. Missing objects and write
results are reported explicitly. No new switch or numerical operator is added.

The failure record includes transported density at the reported cell when it
exists. This supports distinguishing a conserved-density/internal-energy
diagnostic from an EOS-density hypothesis. Failure snapshots remain unauthorized
for CFD restarts. The code does not repair the failed state or change its verdict.
No external service or secret is involved; files stay in the existing case.

Verification requires compilation with the pinned OF8 runtime and a bounded
deliberate failure control that checks field presence, values and nonzero exit.
A normal-run comparison checks that the added failure-only path leaves sampled
fields unchanged. Until those checks execute, this is an unqualified draft.

`srkRhoHaRecovery.H` is a field-independent, density/absolute-enthalpy state
recovery experiment. Inputs are the executing SRK mixture, density, Ha,
reference pressure and temperature guess. Outputs include p/T, residuals,
mechanical stability and selected-root consistency. It changes no fields,
correlations, library ABI or existing solver path. The property probe owns its
initial compiled qualification; CFD activation requires separate development.

The experimental `realFluidRhoHaPredictor yes` switch enables a constraint-based
p/T recovery only where the existing post-inversion caloric audit would fail.
It holds transported density and internal Ha values, changes p/T only for a
mechanically stable state that also matches the executing library root, then
refreshes boundaries and properties. It does not add heat, normalize species,
change an audit limit or overwrite old-time fields.

A post-pressure recovery is a predictor, not an accepted mechanical pressure.
`pressureThermoCorrector.H` reruns the normal pressure equation until no such
recovery is needed, up to `maxRhoHaPressureIterations` (default 6). A final
recovery with no subsequent pressure solve is not accepted; exhaustion writes
a failed snapshot and stops. Species/source and energy equations are not
advanced again inside these added pressure/property iterations.

This mode requires absolute Ha, conservative transport density, inner
scalar/energy correction, post-pressure property refresh and at least two PISO
correctors so the momentum matrix is retained. It remains off by default.
The density/Ha API has compiled point controls; the pressure predictor still
requires original-zero flow and conservation/momentum qualification. Record
all recovery counts, pressure changes and extra pressure iterations.

The inner scalar/energy lifecycle additionally supports `fgmTable` only with
`strangFixedState`. Its first half-source is frozen once per physical timestep
before PIMPLE. Each inner correction re-solves Euler transport from unchanged
old-time Z/C/rho plus that same first-half contribution, then recomputes the
second half from the new transport solution. It does not advance the previous
inner iteration's reacted C. The existing old-time equality checks remain
enforcing. Other finite-rate source lifecycles remain excluded.

This permits the existing density/Ha predictor to be tested with physical FGM
without changing its caloric, mechanical-stability, selected-root or pressure
iteration criteria. Qualification requires a fixed-source zero-flow control at
different inner iteration counts, an unchanged default-off flow anchor, captured
rho/Ha point recovery and original-zero inlet-flow diagnostics. Neither point
recovery nor a converged source iteration establishes G2 agreement. Record
`fgmSourceOldTime`, predictor changes and all extra pressure solves; retain any
iteration exhaustion or unresolved caloric gap.


## Pre-inversion witness

Optional `writeThermoInversionWitness yes` records the exact inputs immediately
before energy, pressure-refresh and accepted-predictor calls to thermo.correct().
`thermoInversionWitnessStartTime` defaults to0 seconds and must be finite and
nonnegative. Default-off performs no field scan or file write. The helper owns
capture only; it changes no field, root policy, iteration, tolerance or acceptance.

Each rank atomically replaces one CSV per call stage in its case-owned
`thermo-inversion-witness/` directory. The metadata line identifies time, rank,
stage and sequence; internal cells and boundary faces contain p/T/h/rho/Ha/allY.
These are inputs of a nonlinear trial, never accepted-timestep or restart files.
They are stored separately from numerical time directories. Native case-sensitive
species names remain distinct CSV columns, avoiding Windows h/H aliasing.

Dependencies are existing OpenFOAM fields and standard C++ file streams; no new
library, network access or secret input. The diagnostic probe can explicitly
capture its initialized one-cell state with `-audit-inversion-witness`.
Example: enable the option and set start time0.00222 on a new original-zero G2
case. Qualify actual compiled one-cell CSV contents, default-off behavior and
unchanged parent libraries before the bounded full-case reproduction. A captured
trial or successful build is not physical validation.

The probe audit respects the configured enable/start controls, permitting an
actual default-off check; enable the runtime option to capture the initialized
state. It never forces a bypass of those controls.
