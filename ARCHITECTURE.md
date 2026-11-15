# Experimental solver boundaries

`replication/runs/20261115-g2-temperature-fields/` maps retained partitioned ASCII
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
