# Full-chemistry progress-coordinate diagnostic

This module follows a closed, adiabatic, constant-pressure ideal-gas reactor from
an explicitly selected state in an existing FGM table. It asks whether
`C = Y_CO2 + Y_CO` crosses the table's upper bound, then reverses, and whether
`Cwater = Y_CO2 + Y_CO + Y_H2O` is monotonic over the same physical trajectory.
Neither coordinate controls the reactor: Cantera evolves all species and energy.

Inputs are the exact v2 table, mechanism, JSON settings and source/environment
hashes. Table temperature and species use the same bilinear Z/eta interpolation
as the solver. Initial enthalpy is computed from those T/Y values by the pinned
ideal-gas mechanism; it is not replaced by an equilibrium or inlet-mixing value.
An independent HP-equilibrium endpoint uses that same initial enthalpy/pressure.
This is a newly initialized local-state experiment, not a CFD restart.

Dependencies are Python 3.12, NumPy and Cantera 3.2.0. No Spitfire, OpenFOAM,
scheduler, network or credential dependency is introduced. The driver only runs
physical integration inside an admitted Slurm allocation. Its consumers are the
table-coverage diagnosis and offline plots; it does not replace table data or
grant real-fluid CFD acceptance.

Two independent fresh integrations retain (1) every CVODE accepted-step state
from `ReactorNet.step()` and (2) requested observation states from
`ReactorNet.advance()`. The latter are Cantera/CVODE observation values, not a
postprocessed linear interpolation. Both use the same tolerances and initial
state. The accepted-step trace may end just beyond the requested horizon; its
actual final time is always recorded. CSVs contain all Y and mass sources,
temperature, pressure, density, heat release, h, mass and elemental fractions.
The diagnostics preserve raw extrema, monotonicity excursions, source signs and
mass/enthalpy/element drift. They do not claim global monotonicity from a finite
trajectory. Tiny negative species or extrapolated NASA ranges are reported, not
silently clipped by this driver.

`settings.json` predeclares two actual failure-related states, 2 ms duration,
1 microsecond maximum CVODE step, numerical tolerances and conservation limits.
The observation grid includes 200 microseconds. Source/equilibrium/trajectory
failures retain partial CSVs and a failure receipt in a new output directory.

```sh
python run.py --settings settings.json --table /inputs/physical.tbl \
  --mechanism /inputs/gri30.yaml --plan
# Run the same command in an allocation with --source-commit SHA \
# --environment-sha256 SHA --out /workspace/results/new-diagnostic
```

Verification: `python -m py_compile run.py table_state.py diagnostics.py`, then
the read-only plan against the actual frozen table and mechanism. The meaningful
execution checks are finite full-chemistry sources, actual time coverage,
independent accepted/observation traces and declared conservation residuals.
No synthetic pass substitutes for these physical checks.

Primary API references: [Cantera constant-pressure reactor example](https://cantera.org/3.2/examples/python/reactors/reactor1.html)
and [ReactorNet API](https://cantera.org/3.2/python/zerodim.html).

`plot.py --input RETAINED_SNAPSHOT --out NEW_FIGURE_DIRECTORY` is an offline
consumer requiring Matplotlib. It checks selected-column curve hashes against
the collection receipt and original full CSV hashes against the scientific run
receipt. It plots accepted steps without fitted curves or new interpolation;
its output identity is separate from the executed reactor source.
