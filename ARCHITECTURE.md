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
