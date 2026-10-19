# Direct premixed displacement-speed diagnostic

This module evaluates Nguyen 2022 Equation (40) on copied 1-D checkpoints.
It does not advance the flame, change solver equations, or establish convergence.
Parent integration revision: `99d64f7cab456488f35df2df9c01f2b1cb1be6d7`.

Inputs are all species, T, p, U, the mesh and dictionaries from an identified
completed job, plus the same qualified real-fluid library build. The preparation
command takes `plan|apply ROOT JOB_DIRECTORY`; the output directory must be new
and inside ROOT. The initial qualification uses phi=1.10, job 124797651, at
0.95–1.00 ms in 10-us increments. Outputs are hashed input receipts, cell-wise
CSV source/diffusion/gradient terms, and OH-isoline measurements. No credentials
are read. Source checkpoints remain read-only; copies, builds and scheduler
logs belong to a new project job. Existing results are never overwritten.

Dependencies: the environment runner, qualified OF8/library build 124657926,
Python 3, wmake and reconstructPar. Dependents: Figure 12 comparison analysis.
There is no Cantera dependency. Build/run under Slurm, including reconstruction.

For each saved state the utility calls `BasicChemistryModel::calculate()` for
instantaneous net mass production, not the time-integrated chemistry `solve()`.
It evaluates `-div(j_OH)` with the four Laplacian terms in the deployed YEqn.H:
ordinary diffusion, mixture-molecular-weight diffusion, and both all-species
mass-flux corrections. All fields and coefficients are evaluated at one saved
state. This is a direct constitutive evaluation of Eq.40 using the solver's
spatial operators, **not** a reconstruction of its sequential/split timestep
residual. In-step averaged chemistry and lagged/sequential diffusion can differ.
The utility does not use the energy-equation YVi field as the species flux.

`rfFlameSpeedTerms -case COPIED_CASE -time 0.00095:0.001` writes one CSV per
time. For fresh gas on the left, analysis interpolates terms to the rising OH
flank, then divides `(omegaOH + minusDivJOH)` by `rho_u * mag(grad(YOH))`.
The fixed primary OH mass-fraction level is 2e-5, consistent with existing
kinematic plots; 1e-5 and 3e-5 are level-sensitivity checks. The paper gives no
specific threshold. rho_u is the mean library density over the first 100 cells.
Do not evaluate at the OH maximum or average invalid/near-zero-gradient cells.
Units: source and diffusion kg/m3/s, gradient 1/m, density kg/m3, speed m/s.

Verification: Python unit tests check interpolation, sign, dimensions through
a manufactured travelling front, missing/ambiguous crossings and nonfinite
inputs. Scheduled checks require successful compile/link, input hashes unchanged,
finite terms, matching saved/recomputed rho, and a mesh with one uniform x-row.
Compare direct and kinematic speed on the same times and marker; agreement is
an observation to measure, not a prerequisite to report. A mismatch is evidence
for estimator/discretization/source-splitting tests, not permission to tune physics.

Example: `python3 -B prepare.py plan /work /work/jobs/NEW`.
Run `python3 -B -m unittest discover -s replication/validation/flame-speed -p 'test_*.py'`.
Expected: analytic diagnostic tests pass; scientific agreement remains measured.
