# Temperature-inversion flame qualification

This module tests a selected native library build with fresh ideal-gas flames.
The second inversion draft tightens the Newton temperature-step tolerance to
1e-9 relative. The first draft retained the final Newton update but failed
the existing nonideal increment and property checks (125003821, 125003825).
The bisection fallback and physical property models remain unchanged. These
checks must pass before the draft is used for the flame comparison sweep.
It preserves the native chemistry and transport models. Species enthalpy fields
use current pressure and temperature, as in the existing energy-corrected draft.
It does not change the PIMPLE equations or infer scientific convergence.

Inputs are a committed source release, a qualified full library build, a condition
key, eight or 32 ranks, and build/full mode. Build mode compiles a separately named
`rfThermoReactingFoam` and runs 100 ns from original zero fields. Full mode uses
that verified executable but generates new zero fields and runs to 300 microseconds.
For 32-rank full runs, an explicit completed global-field parity receipt is required.
Outputs include binary/library hashes, CPU assignments, initial-state hashes,
front histories, heat-release fields, finite-field checks and endpoint status.

Dependencies: `flame-tracking` instrumentation, `fresh-start` initialization,
`premixed-paper` boundary finalization, `cantera-cfd/partition.py` for the optional
balanced 32-rank decomposition, and the shared adaptive field reader. The native
solver does not call Cantera. `environment` supplies the pinned OF8 container.
The comparison gallery consumes these results. Credentials remain external.
All generated paths stay under the configured project root. Existing builds
and cases are read-only inputs; no saved CFD state is used for initialization.

Example: `bash submit.sh plan ROOT RELEASE LIBRARY_JOB 8 phi110 build none none`.
Use `apply` after inspecting the plan. Full mode takes the completed smoke's job
ID and a parity job ID. The latter must contain `parity.json` with `passed: true`.
The parity receipt must identify this smoke and the same library build.

Verify Python syntax, `bash -n` for the module's shell files and `git diff --check`.
The library must pass the small-increment regression before flame qualification.
Then compare eight/32-rank global initial and final fields with
`cantera-cfd/decomposition_parity.py`; do not relax its limits after a failure.
Each MPI rank is assigned one distinct CPU from the batch process's existing
allocation. A rank/count mismatch fails before the solver starts.

`python3 pipeline.py plan ROOT RELEASE LIBRARY_JOB` lists a bounded job graph.
`apply` submits two property checks after the library build, two independent
8/32-rank startup checks, and eleven 8-rank flames after the eight-rank check.
Every smoke also tests ideal-mixture small increments before time integration.
Failed dependencies cancel children; the runtime wrapper also checks test receipts.
Each full case has a 12-hour wall limit and a 300-microsecond physical endpoint.
The sweep reserves at most 1056 core-hours. Endpoint completion does not prove
steady state. A source-keyed ledger prevents duplicate submission. The pipeline
does not authorize 32-rank full runs or staged nonideal CFD models.
