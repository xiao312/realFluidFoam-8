# Checkpoint correction — 18 October 2026

Jobs 124805217 (1 atm) and 124805218 (200 atm) replay the qualified mapped
fine-grid initial states on 32 ranks, with a three-hour limit and unchanged
10-microsecond qualification target. The [job register](paper-refinement-replay-jobs-20261018.json)
separates runner source, reused solver source and library build. Run controls
remain maxCo=0.2, maxDeltaT=1e-6 s and initial deltaT=1e-7 s.

The status check at 23:35 CST found both prior jobs advancing without a fatal
error. Mesh, serial/MPI inlet properties, mapped fields and processor inlet
velocities had passed checks. Full property probes took 73.876 seconds (1 atm)
and 85.698 seconds (200 atm). Reacting steps cost about 212–218 wall seconds.
At cancellation both had fully completed 1.466964 microseconds and were working
on the next step. The latest completed-step maximum temperatures were about
1968.6 K and 2272.4 K; these are log diagnostics, not saved comparison profiles.

The one-hour allocation was insufficient. The old controlDict wrote only at
10 microseconds and set runTimeModifiable=false. Global write-now signals were
disabled, so no supported live checkpoint request was available. Slurm rejected
both attempts to increase the running allocations to two hours with
`Access/permission denied for job`. Jobs 124802872/124802875 were then cancelled
after 47 minutes each. Their logs, initial fields and executable remain intact;
unsaved reacting progress cannot be recovered.

Runner source a244ce46c7dbc098cbf554cd437b0cd04ae2d0c8 copies the already checked
mesh and mapped initial fields into independent job directories, verifies file
hashes, verifies the original executable hash, rechecks initial fields, and runs
that executable against the same qualified library. It avoids rebuilding,
remeshing, probing inlet properties and remapping the coarse donor.

New output controls write every 1 microsecond, retain the latest two output
times and enable runtime control rereading. Because adjustableRunTime aligns
steps to output times, individual step sizes can differ from the previous run.
The physical models, chemistry tolerances, PIMPLE settings and maxCo are unchanged.
Future fresh fine-grid preparation now uses the same checkpoint controls.

Verification: Python/shell syntax and whitespace checks passed; both remote
read-only replay plans passed before cancellation/submission. Scheduled copy
hashes, initial-field checks, MPI startup and saved checkpoints are separate
milestones. Startup alone does not establish a scientifically accepted result.

A provisional estimate is 1–2 hours after replay startup to reach 10 microseconds,
subject to chemistry cost and adaptive time steps. Check after about 30 minutes
for the first saved checkpoint. This does not estimate steady-state convergence.

At 23:44:10 CST both replays had completed copied-file hash verification and
initial-field/inlet checks. Both solver logs reported 32 ranks and no fatal
error during thermodynamic startup. The generated controls were read back:
writeInterval=1e-6, purgeWrite=2, runTimeModifiable=true. No nonzero replay
checkpoint or endpoint result was yet available.
