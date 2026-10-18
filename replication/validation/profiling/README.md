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
