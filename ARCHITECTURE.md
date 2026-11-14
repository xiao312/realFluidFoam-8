# Experimental solver boundaries

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
