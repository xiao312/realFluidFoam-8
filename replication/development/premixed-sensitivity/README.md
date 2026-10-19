# Premixed numerical sensitivity

This module tests the disagreement between instantaneous Eq.(40), the source
used in the OH equation, and tracked OH fronts. It does not change solver physics
or accept a flame speed from its proximity to a paper curve.

Inputs are the eight-rank products checkpoint at 79.9834968798 us from job
124864929, qualified spatial executable 124870644, library build 124657926,
and the locked OF8 container. `study.json` defines three fixed time steps over
the same 20 us interval. Every branch starts from the same copied fields.
The 100 ns branch also measures restart effects against the uninterrupted donor.

Outputs are input hashes, immutable executable identity, contour histories,
spatial source/gradient snapshots, native Qdot fields, and comparison plots.
All data and scheduler output remain inside the configured project root.
No credentials are read or stored. Donor directories are read-only inputs.

Dependencies: premixed-spatial binary and contour definitions, premixed-paper
diagnostics, validation/environment runners, Python 3.8+, Slurm, and MPI.
Local analysis uses numpy/matplotlib. Dependents are the numerical diagnosis
and project record. No production job depends on this module.

Example: `bash submit.sh plan ROOT IMAGE RELEASE dt100` prints a read-only plan.
Use `apply` with identical arguments to reserve eight cores for two hours.
Repeat for dt50 and dt25. The complete first stage reserves at most 48 core-hours.
Submission is locked and deduplicated by release and case key.

`prepare.py plan JOB KEY` checks checkpoint completeness and destination paths.
`apply` copies fields with before/after hashes, removes copied runtime functions,
and changes only time/output controls and diagnostic frequency. Initial chemistry
substep history is reconstructed by the solver; restart equivalence is not assumed.
Spatial and contour output share a 0.5 us interval. Native fields use 5 us output.

`analyze.py OUTPUT KEY=CSV ...` creates stage and contour comparisons. Optional
`--reference CSV` adds the uninterrupted donor over the same physical window.
Tracking uses the fitted contour velocity relative to local fluid velocity,
multiplied by local/unburned density; laboratory contour velocity is also retained.
All three OH levels and both sides remain in the numerical summary.

`gate.py CSV --end-us 79.9834968798` is a fast failure signal on recorded solver
output. It rejects stage disagreement or marker spread above 0.5 cm/s during
the preceding 5 us. This is a declared diagnostic threshold, not a paper tolerance.
Failed gates identify unresolved numerical behavior, not a particular code bug.
Transient flame structure can also fail this screen.

Verification: `python -B -m unittest discover -s replication/development/premixed-sensitivity`,
`bash -n` on both shell scripts, and `git diff --check`. The scheduler runner checks
the pinned binary, finite histories, final time, and Courant maximum below 0.1.
These operational checks do not establish temporal or spatial convergence.

Next decision: compare 50/25 ns over the last 5 us, after the first 2 us of restart
relaxation. Seek changes below 0.5 cm/s in each signed Eq.(40) contour speed and
tracked speed. Require stage and marker agreement separately. If temporal changes
remain large, halve the step again before a mesh study. If they are small, compare
0.5 and 0.25 um meshes at a qualified step. A tighter ODE-tolerance branch then
separates chemistry integration from transport/coupling error. Mesh mapping and
restart controls require their own qualification; they are not submitted here.
