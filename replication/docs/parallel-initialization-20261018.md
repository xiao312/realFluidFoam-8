# Parallel counterflow initialization — 18 October 2026

The original fine-grid jobs invoked `rfPropertyProbe -initial` before decomposition,
without MPI. They allocated 32 cores but used one rank for expensive GRI30
thermodynamic construction. This was a runner sequencing error, not a model
restriction. The owner requested cancellation and parallel execution.

Jobs 124799488 and 124799489 were cancelled after 23:59 and 23:58 respectively,
before inlet finalization, field mapping or reacting integration. Their outputs
remain available. Original coarse donors and other ongoing flame jobs are unchanged.

Source `21d360e69665f2510af3a10ae41c6a4a8853e96d` changes the runner and validation,
without changing C++ thermophysical formulas or solver equations:

1. Compare serial and four-rank inlet rho, Cp and Cv on a 112-cell fixture.
2. Decompose the full fine mesh and run the same property probe on 32 ranks.
3. Require all 32 CSVs and agreement of every inlet-owning rank with the serial
   reference within 1e-12 relative tolerance.
4. Finalize inlet velocities, map the coarse primitive fields and refresh processor
   fields with `decomposePar -fields`.
5. Check processor inlet velocities and mapped fields before starting the 32-rank
   reacting solver.

Mesh generation and OF8 mapFields remain serial preprocessing utilities. MPI
startup alone does not establish speedup or numerical acceptance.

The [replacement register](paper-refinement-mpi-jobs-20261018.json) pins source,
archive hash and resource limits. Current jobs 124802872 (1 atm) and 124802875
(200 atm) use source 8d9ecd2 and each reserve 32 cores for 60 minutes, targeting
only 10 microseconds of physical integration. Library build 124657926 and the pinned OF8 environment are reused.
Long fine-grid continuation depends on successful bounded qualification.

Local verification: shell/Python syntax and whitespace checks passed. Synthetic
rank aggregation accepted split inlet ownership and rejected missing output and
property disagreement. Scheduled serial/MPI evidence follows below. Raw logs and JSON checks remain under each project job
folder; executable hashes, linked libraries and mapped input hashes are retained.

At 22:49:38 CST both fine meshes passed checkMesh. Serial/four-rank fixture
comparisons passed with maximum relative differences of 1.1080e-13 (1 atm)
and 1.0725e-13 (200 atm), below the 1e-12 threshold. The fine meshes were being
decomposed. Full-grid property and reacting startup results were still pending.

The first MPI replacements stopped immediately before the full probe because
`/usr/bin/time` is absent from the pinned container. No full-grid probe or CFD
integration ran in jobs 124802435/124802436. Source
`8d9ecd2a6091b0453350049cd61a23a23adf938c` uses Bash built-in time for both MPI
commands. Timing files contain wall/user/system seconds; obtain memory separately
from scheduler accounting or process measurements. This is a runner correction.

At 22:58:21 CST both current full-grid logs confirmed `nProcs : 32`.
The 200-atm full probe finished, passed the rank/reference property comparison,
finalized inlet velocities and entered field mapping. The 1-atm full probe was
running without a fatal error. Reacting integration had not started at this
observation. Both replacement small-fixture checks passed again.

The 200-atm full probe took 85.698 wall seconds (2603.893 user and 11.117
system CPU seconds). Its previous serial attempt was cancelled unfinished
after approximately 24 minutes, so no exact complete-run speedup is claimed.
