# Fresh initial-state flame runs

This module launches the eleven native ideal-gas flames and the phi110 enthalpy
correction from freshly generated time-0 fields. It does not copy a donor state,
modify solver physics, or authorize automatic restart after scheduler termination.
The owner requires explicit permission before any intermediate-state continuation.

Inputs: ideal-baseline seeds and generator, Cantera temperature anchors, qualified
native solver build 124883260, corrected solver build 124900963, library 124657926
and property probe 124878193. Outputs: isolated cases, initial-file hashes,
start-policy checks, job identities and the existing in-situ histories.
Configuration: family native/energy, phi090–phi140 (energy only phi110), 100 atm,
298 K, 8000 cells, central 0.2-mm equilibrium products, initial U=0, initial
deltaT=1e-10 s, maxCo=0.1, maxDeltaT=50 ns, endpoint 200 us. Native phi090 has a
48-hour wall-time allowance because the previous segment was unusually slow;
all other jobs have eight hours. These are scheduler ceilings, not predicted cost.

Dependencies: ideal-baseline and premixed-paper generation/finalization,
flame-tracking instrumentation/checks, pinned OF8 container, Slurm and Python.
Dependents: four-solver diagnosis and the native phi sweep. Every generated path
is inside ROOT; credentials are external and the pinned binaries are read-only.
The energy binary remains an experimental draft and shares unchanged libraries.
Both families now support every declared phi. An optional final endpoint in
microseconds (200, 300 or 400; default 200) creates a new original-zero run with
that duration. It never extends or copies the completed 200-us case. The endpoint
is part of ledger identity. Eight-hour scheduler limits remain unchanged except
for native phi090; these limits do not authorize checkpoint continuation.

Example: `bash submit.sh plan ROOT RELEASE native phi110` validates the request
and prints placement; `apply` submits the same plan with a deduplicated ledger.
`python prepare.py plan native phi110 NEW_CASE` is read-only. Apply always invokes
the original initial-state generator. `python prepare.py verify FAMILY CASE`
must pass after decomposition and before execution: startTime=0, startFrom=startTime,
no positive-time directories and complete original 0 fields for all eight ranks.
No smoke checkpoint is used as a production initial state.

Example longer fresh run: `bash submit.sh plan ROOT RELEASE energy phi110 300`.
Preparation accepts the matching `--end-us 300`. Verify start-policy guards with
`python3 -B test_policy.py /contained/project/test-state`; generated controls and provenance must
agree on the chosen endpoint while the earliest time remains zero.

Verification: Python compilation, shell syntax, start-policy negative checks,
scheduled mesh/density checks, binary hashes, earliest runtime tracking time=0,
and matching native/energy phi110 initial fields. Completion uses the existing
finite-field/tracking check and does not establish steady convergence.
