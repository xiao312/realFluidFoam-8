# Spatial displacement-speed audit

Evaluate local Nguyen Eq.(40) across the products-seeded flame at four saved
times, retaining instantaneous checkpoint chemistry and the actual source used
by one isolated replay step. This module does not alter the live donor, select
an estimator for its agreement with the paper, or claim restart equivalence to
the uninterrupted run. Parent integration: a406e79.

Inputs: donor 124864929, eight-rank checkpoints near 20/40/60/80 us, native solver
qualification 124868494, library build 124657926 and pinned OF8 environment.
Outputs: per-cell source, diffusion and gradient CSVs, copied-input hashes,
one-step output-on/off field equality, contour checks and plotted profiles.
Configuration is explicit in prepare.py; submit.sh plan/apply ROOT IMAGE RELEASE
reserves eight cores for 30 minutes. No credentials are read. Copies, temporary
files, compiler products and logs remain inside the new scheduler job.

Dependencies: premixed-paper generator/diagnostics, qualified solver/library,
the contained Slurm runner, Python, wmake and MPI. Plotting uses numpy/matplotlib.
Dependents: flame-speed interpretation and the project record. The generated
rfSpatialReactingFoam is separate from all production executables.

instrument.py plan/apply RELEASE OUTPUT extends only generated diagnostics.
It writes an instantaneous checkpoint evaluation before advancing, then both
source-used and instantaneous stages after one 100 ns step. The first replay
is also run with the qualified native solver; all original field bodies must
match. Checkpoint states and their replay endpoints are explicitly distinguished.
Input-copy hashes detect changes during copying. Controls and fresh CSV paths
are the only changes to the copied case; the donor remains read-only.

Each spatial CSV retains x, OH mass fraction, signed dYOH/dx, local rho/U/T/p,
net OH mass source, diffusion used by that diagnostic stage, and the two-term
Fickian diffusion from paper Eq.(39) evaluated at that stage's state. The latter
is a constitutive comparison, not the full deployed four-term species operator.
Fresh rho is averaged independently over the outer 5% on each side. All
calculations use SI units; plotting converts m/s to cm/s exactly once. Gradients
near zero must be masked and the mask reported; there is no speed at the OH peak.

Verification: generator anchors, shell syntax, scheduled compile/link and
one-step old/new field equality. Compare checkpoint instantaneous contour values
with the live CSV at the same saved time to quantify reconstruction error.
Example: bash submit.sh plan ROOT IMAGE RELEASE. Expected result: a bounded
read-only plan; apply submits only that isolated analysis job. Scientific
acceptance additionally requires time/marker/mesh and source-stage agreement.

`analyze.py DOWNLOADED_JOB OUTPUT` creates spatial and OH-marker PNG/SVG plots,
SI-term contour tables and input hashes. The speed plots use only the fresh-side
rising OH flank with YOH>=1e-7 and gradient greater than max(1e-6,0.001 times the
peak gradient); raw CSVs retain all cells. `python -B -m unittest discover -s
replication/development/premixed-spatial` checks mass-source units, density
weighting, both front signs and the single conversion to cm/s on analytic data.
