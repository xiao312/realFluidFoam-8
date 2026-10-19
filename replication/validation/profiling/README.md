# Solver section profiling

This module measures wall time per MPI rank for the unchanged reacting algorithm.
It creates a separately named executable from a qualified build's source, adding
timers only. It does not optimize physics or continue the production campaign.

Inputs: qualified build directory, stopped case checkpoints and a new job directory.
Outputs: instrumented source, build log, per-rank CSV timers and copied-case results.
No credentials are consumed. All generated files stay under the project job root;
source builds and original cases are read-only inputs. Python 3, OF8 wmake and the
qualified libraries are required. The environment runner provides containment.

`instrument.py plan BUILD OUTPUT` prints the source and destination without writes;
`instrument.py apply BUILD OUTPUT` copies only the solver files and adds timers.
`run.sh RELEASE JOB BUILD` builds and runs short checkpoint replays under Slurm.
The profiling stage is selected through the validation runner using `RF_STAGE=profile`.

Timers use steady-clock wall time without additional MPI barriers. Child timings
overlap their enclosing sections and must not be added to the parent. Per-rank
spread includes communication waits and is not itself a measure of chemistry load.
CSV output is outside the measured timestep. Initial loading is excluded.

Verification: run the instrumenter plan before apply; compilation must succeed;
each replay must reach `End`, and timers must exist for every MPI rank. Compare
the final fields of an uninstrumented replay with the same instrumented replay.
Short replays qualify section costs at those states, not whole-campaign averages.

`python3 -B summarize.py JOB` emits JSON with per-rank seconds and mean section
shares, using steps 2–4 of each five-step replay. Step 1 and the forced final
write are excluded. The command is read-only and requires all observed profiles
to contain five timesteps.

## Live CPU placement

`python3 affinity.py plan|apply ROOT JOB_ID` inspects only the current allocation's
named OpenFOAM solver processes. Run it in a short overlapping Slurm control step
on that job's node. Plan prints rank/thread affinity and proposed distinct CPUs.
Apply changes only those threads' CPU affinity; it neither stops nor restarts the
solver, modifies a case, changes the allocation, nor copies a transient state.
The older checkpoint profiling workflow above does not override the requirement
for explicit owner permission before any new 1D checkpoint replay.

Inputs are the project root, numeric job ID, its declared decomposition and the
Linux `/proc` records of this user's processes. Output is a JSON receipt on stdout;
save it under the project root. The script requires matching SLURM_JOB_ID, a
complete unique rank set and exactly one allocated CPU per declared rank in the
union of observed affinity masks. It fails without changes if these checks fail.
It never widens placement beyond that observed union or prints process environment
contents. Dependencies are standard Python/Linux affinity APIs and Slurm; no
credentials are used. This is an operator diagnostic, not a solver dependency.
Verify all thread masks after apply, then compare physical-time throughput using
the same continuously running job. Record both plan and apply receipts.
