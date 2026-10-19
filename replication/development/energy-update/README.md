# Species enthalpy update experiment

This draft isolates the confirmed stale species-enthalpy values used in energy
diffusion. It refreshes the solver-owned fields through composition.HE(i,p,T),
using the current pressure and temperature. The upstream library cache remains
unchanged. This is a controlled solver correction, not a general library repair.
PIMPLE placement, chemistry, transport coefficients and case inputs do not change.

Inputs: the qualified library build 124657926, tracked solver source, phi110 donor
124878193, and the baseline continuation's input hashes (job 124885085). Outputs:
an independently named rfEnergyReactingFoam, red/green enthalpy probes, a short
parallel smoke case, and an isolated continuation to 200 us. The checkpoint and
all original input hashes must match the unchanged baseline before a run starts.
The eight-state probe checks all species in cells and boundary faces at the
original temperature, after +100 K and after -50 K.

Dependencies: solver-comparison for frozen states/probe input generation,
flame-tracking for instrumentation and checkpoint preparation, adaptive field
inspection, pinned OF8 and native libraries, Python and Slurm. Dependents: energy
diagnosis and later promotion review. All generated paths stay in ROOT; external
software is read-only and credentials are not copied. No production library or
active baseline case is modified.

Example: `bash submit.sh plan ROOT RELEASE`; `apply` submits one 8-core, six-hour
job. The job must reproduce a failing legacy probe, pass the refreshed probe,
verify binary links, and pass finite-field/species checks on the smoke case before
continuing. `python instrument.py plan RELEASE NEW_SOLVER` performs read-only
discovery. Verify Python compilation, bash syntax, git diff --check, and scheduled
red/green probe receipts. Passing startup does not establish flame convergence or
justify merging this physics change. Compare speed histories at the same times.
