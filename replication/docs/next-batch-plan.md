# Next scaling and convergence batch

The owner was asked for a CPU core-hour cap on 2026-10-17 after the first measured
counterflow pilot. The current bounded startup jobs are separate from that next
batch. Do not treat elapsed time without an answer as budget approval.

## Evidence and cost limit

The 320-cell oxy-fuel pilot at 1 atm took 197 seconds of solver wall time for
100 timesteps (195.39 seconds CPU). It used one solver process inside a two-CPU
allocation. Chemistry was GRI30 with ode/seulex; dt was 1e-8 s. It reached only
1 microsecond and did not establish a steady flame. This timing is an observed
startup cost, not a production forecast; chemistry stiffness, timestep choice,
mesh size and parallel overhead can change it substantially.

A naive linear extrapolation to 1 million cells and 100,000 steps is about
171,000 serial CPU core-hours. That extrapolation is deliberately not a request
to launch such a run. It shows why measured scaling and a cheaper convergence
path are required. The paper's counterflow grids have about 1,000 radial cells
and hundreds to roughly 1,000 axial cells; a coarse pilot is not an alternative
validation mesh.

## Proposed sequence within the chosen cap

1. Reuse the verified build and runtime. Compare the same startup case on one
   and two MPI ranks; require successful mesh reconstruction, finite fields,
   species sums within 1e-8, and relative peak-temperature difference below 1e-5.
   Record field norms as well as summary extrema. The existing environment MPI
   probe does not establish solver-level parallel correctness.
2. Increase to 1,280, 5,120 and 20,480 cells with short fixed-step runs. Test 2,
   8 and 16 ranks where cells per rank are sufficient. Use actual Slurm allocated
   CPUs times elapsed time for budget accounting, including failed runs.
3. Use measured throughput and chemistry stability to select a longer coarse
   run. Test timestep growth separately. Do not infer allowable timestep solely
   from a small hydrodynamic Courant number in a stiff reacting calculation.
4. Obtain a developed flame, then check less than 1% temporal drift and less
   than 2% grid sensitivity using declared observables. Compare reference
   profiles only after those checks. Preserve the coarse and failed attempts.
5. For premixed flames, establish two developed fronts and a reproducible OH
   isosurface calculation, including gas-relative velocity and density weighting.
   Check domain, ignition, OH-surface, timestep and mesh sensitivity before the
   0.90–1.40 equivalence-ratio campaign. A startup temperature peak is not a
   laminar burning velocity.

A 100-core-hour cap is intended for correctness, scaling and initial convergence
work. A 1,000-core-hour cap can support a broader measured development batch;
neither cap is a promise that all paper-resolution flames will converge.
Stop new submissions before exhausting the chosen cap and reserve enough budget
to finish already-running jobs at their declared limits. Give every submission
an explicit wall-time limit and project-contained output paths.

## Scientific issues kept open

- Baseline enthalpy inversion fails the declared 1e-6 criterion. Preserve the
  measured baseline and create a separately reviewed source change if adjusting
  the Newton routine; do not silently substitute a patched solver.
- The current NIST snapshot and OF8 source differ from the paper-era inputs.
- Full reference arrays and premixed initialization/domain details remain gaps.
- Molecular-weight diffusion corrections and thermodynamic conventions must
  remain consistent when interpreting OH displacement speed.
