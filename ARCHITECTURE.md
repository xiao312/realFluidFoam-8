# Experimental solver boundaries

The psi-thermo Dimix policy has an explicitly bounded split-FGM RANS path.
Only kEpsilon/unity-Lewis eddyDiffusivity Prt0.7 is eligible; its scalar fluxes
use alphaEff. The RANS case module declares this optional optimization, while
the compiled thermo policy and rejecting Dimix accessors remain authoritative.
Matching concrete thermo products and physical parity/timing must be qualified.

The tapered-injector module also owns optional analytic duct-velocity priming.
It consumes executing inlet density receipts and geometry, modifies only fresh
internal duct U and records the initial-condition change. It owns no thermo
recovery, source integration, scheduler operation or developed precursor state.

The optional nonlinear caloric-audit lifecycle is solver owned: intermediate
scalar/pressure iterates report finite caloric defects, while the original
enforcing audit remains mandatory after the complete PIMPLE loop. Nonphysical
trial states, source history and pressure retry bounds retain separate guards.

The retained-temperature-field module additionally owns internal-cell
CFD/table thermal-state audits. It consumes immutable mesh/field receipts and
the existing renderer, measures volume and absolute-source weighted departures,
and never modifies the source table, CFD fields or acceptance limits.
Its species audit reads hash-bound case-sensitive archive members directly,
preserving atomic H versus sensible h and measuring element/progress consistency
against the exact mechanism metadata. No species normalization is performed.

The direct-FGM case module owns explicit inner/density-Ha/differential-pressure
experiment configuration and dictionary provenance. It selects existing solver
helpers, never implements EOS recovery, grants scheduler resources or changes
scientific acceptance. The compiled solver remains the execution authority.

The solver inner scalar/energy lifecycle supports the existing split FGM
source only through its unchanged old-time transport anchor. Source first-half
ownership remains outside PIMPLE; repeated corrections recompute the second
half instead of advancing the previous iterate. The density/Ha pressure
predictor and its acceptance criteria remain separately owned by the solver's
existing SRK recovery helper. No thermo library ABI or default mode changes.

The real-fluid thermo probe's captured-point interface can explicitly retain
transported rho/Ha as well as p/T/h/Y. Its separate one-cell recovery query
depends on the existing solver SRK recovery helper and never owns CFD state
or restart authorization. Default thermodynamic-only extraction is unchanged.

`mascotte-g2/rans-diagnostic` additionally configures an explicitly declared
raw-C FGM case on the normal full-property transport path. It shares the
existing kEpsilon/eddyDiffusivity runtime and direct-FGM initializer/checker;
it does not extend the suppressed-Dimix constructor policy or implement PDF
averaging. The original optimized steady-flamelet path remains separate.

Within `replication/validation/realfluid-g2-thermo`, the explicit Kong parameter
estimator consumes an existing author-parameter manifest and the deposited
Chemkin transport file. It adds only the missing CH3O2 LJ/SRK estimate to a
separate input; `export.mjs` remains the dictionary owner. It does not change
the Cantera mechanism, fit kinetics or establish a measured critical state.

`replication/fgm/g2-manifold/` selects the actual TF streams and orchestrates
the existing `direct-flamelet` physical transient and table exporter. Node owns
phase receipts; pinned Cantera/Spitfire own chemistry/integration. It consumes
no CFD state and depends on neither scheduler nor agent libraries. The OF8 FGM
reader/case generator are downstream consumers only after separate qualification.

`replication/validation/mascotte-g2/paper-injector-wedge/` owns a separate
coarse tapered-injector geometry sensitivity. It generates dictionaries using
Node, with allocated OF8 mesh tools as the qualification boundary. It does not
alter registered mesh assets or select CFD closures. Its topology test shares
the ASCII mesh parser from `coarse-wedge`. Its measured-asset loader is consumed
by the explicit injector mode in `direct-fgm/prepare.mjs`; mass-flow areas and
profile origin come from the measured inlet/exit geometry, not schematic pixels.

Within `replication/fgm/maders-coflow`, `field_audit.py` consumes hashed exported
NPZ tables and retained CSV profiles. It independently compares mapped-C lookup
and inlet enthalpy; NumPy is its only external dependency. It never changes CFD,
reference data, diagnostic fields or scientific acceptance.

`replication/runs/20261115-g2-temperature-fields/` includes a receipt-driven
single-case renderer with explicit ranks/time for tapered injector meshes. It
shares the local-only plotting boundary and never advances a simulation.
The module maps retained partitioned ASCII
OpenFOAM temperatures onto actual axial/radial cell polygons. It reads hashed
local collections and writes images/data receipts for Forge. It has no solver,
scheduler or network dependency and cannot advance CFD.

`replication/validation/written-time/` owns read-only mapping from physical log
times to unique serialized output directories. Post-run qualification readers
depend on its Node filesystem interface; the solver, EOS and scheduler do not.
It uses explicit case output precision rather than a scientific-error tolerance.

The upstream thermophysical libraries under `src/` own EOS, caloric inversion
and transport properties. `applications/solvers/reactingFoamSolveZ/` owns the
experimental transported-coordinate flow/energy equations. It depends on those
libraries and OF8, never on a scheduler or agent runtime.

Within `src/combustionModels/relaxedTable/`, `relaxationClock.H` validates and
evaluates the source clock. The model and one-cell qualification probe share
this header. Default per-step relaxation, opt-in Euler fixed-time and exact frozen-target
fixed-time diagnostics use
the same species update; the clock cannot alter thermodynamics or field bounds.

Within that solver, `createLowMachPressure.H` selects an optional uniform
thermodynamic-pressure/separate mechanical-pressure model. `pEqn.H` owns the
projection, `EEqn.H` the selected energy equation, and
`lowMachPressureAudit.H`/`energyState.H` report actual model diagnostics.
The existing coupled compressible path remains the default. No library ABI
change is introduced by this model selection.

`replication/` owns case generation, independent references, validation and
plotting. Run wrappers submit through external FlamePilot HPC adapters;
scientific source does not depend on controller/session/scheduler state.
See the solver README and replication/README.md for configuration and checks.

The optional contact-averaging audit in the realfluid-g2-thermo probe consumes
the same registered SRK mixture and existing solver type aliases. It performs
property queries and conservative-state averaging only; it cannot submit jobs,
advance CFD or change the library's EOS/root policy. Probe outputs remain
separate from scientific acceptance and the CFD solver's source identity.

The optional manifold-enthalpy audit similarly queries the existing SRK THs
inversion for reacting-table and passive compositions on an affine inlet-Ha
baseline. It adds no phase model or CFD operator. Its pressure/composition map
is a zero-step feasibility diagnostic, not an evolved solution or a flamelet.

`replication/validation/mascotte-g2/passive-cold` creates a separate analytic
unburned composition table and fresh-case configuration. It depends on the
strict steady-flamelet input reader for its original header provenance, and
reuses the existing C++ table reader as a passive affine lookup. It does not
alter that reader, physical profiles, EOS libraries, source terms or acceptance
criteria. The active diagnostic manifest remains separate from factory inputs.

`src/combustionModels/relaxedTable` owns a conservative-species predictor's
post-transport relaxation toward the strict one-dimensional table target.
The combustion interface explicitly separates Z transport, composition ownership,
absolute-Ha support and post-transport correction. The solver owns transport and
energy, while the model owns its target/source update. This changes the custom
combustion ABI and requires a full consistent library/application rebuild.

`replication/validation/mascotte-g2/relaxed-source-control` prepares original-zero
one-cell model-source diagnostics using the frozen build probe factory. It
depends on the relaxedTable solver/probe and strict table inputs, not on HPC
control; its output is not a physical flow solution.

The solver's optional `densityPredictorTimeStep.H` owns a source-free fixed-mesh
Euler mass-predictor step bound using accepted rho and mass phi. It constrains
Time before field transport, never modifies thermodynamics or field values,
and adds no library/controller dependency. Physical guards remain unchanged.

The property probe's optional density/Ha audit depends on the field-independent
`reactingFoamSolveZ/srkRhoHaRecovery.H` and existing concrete SRK mixture APIs.
This header evaluates the same coefficients in rho/T form and returns explicit
caloric/stability/root-consistency verdicts. It owns no fields or scheduler
operations and is not activated in CFD by introducing the diagnostic.

The optional `srkRhoHaPredictor.H` consumes the qualified density/Ha recovery
API and the solver's current transported fields. `pressureThermoCorrector.H`
owns retrying the existing pressure/property solve after a predictor change;
it cannot advance species or chemistry. Existing audits remain authoritative,
and the default path executes one unchanged pressure solve.


`replication/runs/20261115-g2-source-clock` freezes controlled source-clock and
cold-state recovery experiments. Its plotting code consumes retained cell data;
the optional Node importer consumes the existing local Forge catalogue/export
schema and appends diagnostic views without changing primary comparisons. Neither
component submits compute, publishes a site or grants scientific acceptance.

`replication/validation/schmitt-contact/apec` owns a serial pure-oxygen APEC
contact prototype with direct conservative rho/e recovery. It depends on shared
ContactDF state types, the contact initializer/factory and executing SRK library.
It has no reacting-solver dependency edge in the reverse direction and cannot
advance G2 or implement multicomponent APEC by its presence.

`replication/runs/20261115-g2-overnight` owns frozen fresh-case pressure and
property experiments. It depends on prior qualified source-clock/thermo products
and existing factories, and feeds the paper-review visualization. It changes no
production solver interface or scheduler dependency.

The solver's default-off `speciesTransportAudit.H` consumes the species
predictor, closure bookkeeping and rho/phi residuals from `YEqn.H`. It reports
clipping/closure defects and retains invalid predictor witnesses before source
relaxation. It owns no numerical correction, acceptance gate or library ABI.

The retained-field source audit optionally depends on local Cantera3.2 for
pointwise pressure-based chemistry replay. It has no CFD execution or source
correction authority; simulation and tabulation modules do not depend on it.

Maders finite-window statistics depend on the existing local sampled-profile
reader and NumPy. Its optional receipt flows into paper plotting; the plotter
does not depend on the averaging implementation or grant statistical acceptance.
