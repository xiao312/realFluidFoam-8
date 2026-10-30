# Direct finite-volume verification

This module isolates energy-source sign, closed-domain energy conservation and
mixture-fraction transport before larger MASCOTTE diagnostics. Its tables are
explicitly analytic fixtures, not chemical flamelets or paper replication data.

`schemes.mjs` owns the explicit discretization entries needed by the selected
reactingFoamSolveZ/Stokes/Fourier operators. Both verification cases and the
warm/cold G2 generator consume it. The analytic default remains Gauss linear;
G2 retains `default none` with named entries. Stokes calls the explicit tensor
divergence `div(((rho*nuEff)*dev2(T(grad(U)))))`, also present in the official
OF8 counterflow tutorial. Fourier's species/enthalpy terms use the declared
default Laplacian. `node --test schemes.test.mjs` checks this runtime operator
contract; it does not replace the actual first CFD step or model validation.
Primary-source audit: [OF8 viscous stress](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/MomentumTransportModels/momentumTransportModels/linearViscousStress/linearViscousStress.C),
[Fourier transport](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/ThermophysicalTransportModels/laminar/Fourier/Fourier.C),
and [counterflow schemes](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/tutorials/combustion/reactingFoam/laminar/counterFlowFlame2D/system/fvSchemes).

`prepare.mjs --out DIR --kind heating|contact|conversion [--cells N] [--delta-t S]`
creates a new case, refusing an existing destination. Without `--out`, it prints
the inputs and expected analytical problem without writing. All cases start at
time zero. They use constant-composition nitrogen, ideal-gas hConst thermo and
laminar Fourier transport in a periodic one-dimensional box.

The heating case has uniform positive Q = 1e6 W/m3. Its independent expectation
is `T(t)=T0+Q*t/(rho0*Cv)` and `E(t)-E(0)=Q*V*t`. Four outer pressure/enthalpy
correctors resolve closed-volume pressure work. An independent constant progress
source of 0.1 kg/m3/s checks `c(t)-c(0)=Sc*t/rho0` without a second rho factor.
The contact case transports
`Z=0.5+0.2*sin(2*pi*x/L)` at U=1 m/s; its continuum solution includes Fourier
diffusion `D=mu/(Pr*rho)`. Composition is deliberately independent of Z to
isolate the scalar equation, not to represent two-fluid mixing.

The `conversion` case tests the optional absolute-enthalpy route. Two analytic
species have identical Cp/molecular weight but differ by 1e6 J/kg in formation
enthalpy; raw C increases under a source of 0.1 kg/m3/s. Total internal energy
must stay constant while temperature rises from the loss of chemical energy.
The table deliberately carries a different Q=1e6 W/m3, which must not enter the
absolute-enthalpy equation. This detects double chemical heating and checks the
v2 coordinate, refreshed composition and thermo inversion in a real FV solve.
These manufactured species are verification inputs, not a methane mechanism.

`check.mjs CASE LOG` reads the solver's direct energy records and written Z
field, then writes `verification.json`. It checks actual time advancement,
mass/energy or scalar error and equation residuals. Synthetic parsing checks do
not establish physical success. `run.sh CASE SOLVER` runs blockMesh and the
solver only inside an already-admitted FlamePilot Slurm allocation. Build and
run identities are the operator's immutable admission record.

The three analytic cases also enable `writeEnergyResidualAudit`. Their unchanged
1e-6 assembled-residual criterion now uses the once-only coupled-neighbour
evaluation. The audit separately checks that the legacy OF8 residual differs
by exactly its duplicate coupled source (within 1e-8 W) and reports absolute
linear residual, reconstructed normalization scale and iteration ceilings.
This catches the executed r5 periodic diagnostic defect without changing the
equation or accepting a large dimensional error. A high normalized residual
on a near-constant field is not by itself proof of a large physical error.

Dependencies: Node.js >=18 for preparation/analysis, the qualified OF8 solver,
and `blockMesh` at runtime. Outputs are dictionaries, a manifest, logs and
small JSON summaries. No credentials, remote connections or scheduler access
are used by this module. Keep raw output outside Git.

Example: `node prepare.mjs --out /project/trial/heating --kind heating`, then
`bash run.sh /project/trial/heating /project/build/reactingFoamSolveZ` inside
the allocation. Expected result: finite T increasing in the heating case,
energy increment within 0.5% of QVt, mass conserved to 1e-7 relative, and a
small assembled equation residual. Acceptance is measured, never inferred
from these declared thresholds.

## Matching species thermodynamics for subsequent physical tables

`thermo-export.mjs INPUT.json [--out NEW_DIR]` converts a complete ordered
Cantera NASA7 species export into an OF8 `janaf/perfectGas/sensibleEnthalpy`
dictionary. Without `--out` it validates and prints the proposal only. The input
includes species molecular weights, NASA7 temperature ranges and coefficient
arrays, mechanism identity and gas constant. All species are retained. The
output records the input SHA256 and the fork's historical gas constant
8314.47 J/(kmol K), whose small difference from modern Cantera is not hidden.

The initial conversion uses explicitly declared constant transport
mu=1.8e-5 Pa s and Pr=0.72 for every species. This is a diagnostic energy/EOS
interface, not matching flame transport. It changes no source coefficients and
does not claim that OF8 has executed the dictionary; the physical solver must
still load and exercise it before qualification. Heat-release tables for this
energy convention must use formation enthalpies at 298.15 K, not the separate
current-temperature total heat-release diagnostic.

`--nasa-extrapolation 200,6000` explicitly extends inversion limits for a warm
diagnostic. It changes no NASA coefficient, transition temperature or molecular
weight. The export receipt retains every original and effective species range.
Without the option, original ranges remain; OF8 mixture arithmetic intersects
them (GRI30: 300–3000 K). A flamelet above 3000 K is therefore not qualified by
the default dictionary. Cantera evaluates the existing polynomial outside its
declared range; the option reproduces that evaluation policy, not new validated
thermodynamics. Solver caloric closure must still be measured.

The solver's opt-in `writeFgmThermoClosure` recomputes literal h(p,T,Y) through
the executing library and compares it with stored h after thermo correction,
at initialization and every energy correction. Successful summaries are written
at field-output times; failures are reported immediately. It reports maximum/RMS error in J/kg and
normalizes by max(1, |h|, |h(T)|, |Cp*T|). A configured limit fails the run;
it does not overwrite h or T. Warm stock-OF8 diagnostics declare 1e-4, matching
the stock relative temperature iteration tolerance. Full282 source-splitting
checks use 1e-8 with the tightened 1e-9 temperature iteration tolerance.
The evaluation precedes the subsequent pressure correction. It does not replace
a final-state nonideal pressure/enthalpy coupling or outer-convergence check.

`probe-v2.C` is a compact check of the compiled reader: unchanged v1 source
normalization, v2 raw source/mapping, degenerate pure-stream row and counted
diagnostic clipping. The positive invocation takes `positive linear.tbl
mapped-v2.tbl`; the negative invocation takes `negative` and the same paths and
must fail specifically on an inadmissible raw C at zero span. Build and execute
inside the same Slurm environment as the library, then proceed to actual
finite-volume physical cases; these four arithmetic checks are not a flame.

`prepare-physical.mjs --table-dir DIR --metadata FILE [--out NEW_CASE]` prepares
a uniform eight-cell constant-volume diagnostic from a hashed finite-rate v2
table. It samples Z=0.2 and interior lookup eta=0.5, exports every NASA7 species,
and initializes raw C, Y and absolute enthalpy consistently. Without an output
it validates and prints a plan. The short duration is reduced until the
projected constant-volume pressure drift is below 0.1%; the actual run must stay
within 0.2% of the table pressure. Chemistry uses its fixed declared table
pressure, so this is a bounded coupling diagnostic, not a constant-pressure
reactor or a counterflow flame comparison. The check requires real progress
change, total-energy and mass conservation and zero lookup clips.
# Declared physical progress coordinate

`physical-input.mjs` exposes the table's nonempty, unique `progressSpecies`
list after checking it against the actual mechanism. Callers must use that list
when comparing raw transported progress with species fields; CO2+CO is not a
universal coordinate. The table's mass-fraction/source units remain unchanged.
