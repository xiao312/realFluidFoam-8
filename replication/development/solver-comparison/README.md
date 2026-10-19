# Solver and chemistry comparison

This module investigates the low transient ideal-gas flame speed. It owns isolated
stock OF8 reactingFoam, DeepFlame OF7 dfLowMachFoam CPU/CVODE runs and native
chemistry probes. It does not change the production solver or accept a flame speed.

Inputs: the ideal-baseline phi110 seed, author GRI30/NASA7 inputs, verified Cantera
profile, pinned solver sources and environments. Outputs: separate cases, input
hashes, executable/link receipts, sampled profiles and chemistry CSV files.
Configuration: 100 atm, 298 K, phi=1.10, 4 mm / 8000 cells, central 0.2 mm HP
products slab, zero initial velocity, matching boundary conditions and 50 ns step
ceiling. End time 200 us is a comparison checkpoint, not a convergence criterion.

Dependencies: ideal-baseline and premixed-paper generators, OF8 pinned container,
SCNet OF7 installation, DeepFlame 7cb3294b275525cb8829ada3d3fbc067ab9323eb,
Cantera 2.6 native development library, Python and Slurm. Cantera 3.2 remains the
independent local reference. Downstream: flame comparison records and diagnosis.
All caches, HOME, builds and outputs stay inside the project. External OF7 is
read-only; credentials remain outside source. No DNN or GPU chemistry is enabled.

The stock case uses multiComponentMixture / sutherland / perfectGas / janaf,
standard chemistry and its native unity-Lewis transport. It is not a transport-
matched control. DeepFlame uses Cantera mixture-averaged transport. Neither full
flame comparison alone establishes a chemistry defect.

Chemistry checks compare instantaneous net molar rates and independent 50 ns
advances at identical flame states, then vary tolerances and interval. Report
OpenFOAM's concentration/temperature ODE, Cantera's physical CP reactor and
DeepFlame's isothermal CV reactor separately. Different reactor equations must
not be interpreted as an integrator error. Preserve failed build/run evidence.

Example: `python prepare.py plan stock CASE` is read-only; `apply` requires a new
case directory. `bash submit.sh plan ROOT RELEASE MODE` prints bounded Slurm
submission and placement; `apply` submits it. Modes select build/probe/flame jobs.
Verification: Python compilation without bytecode, bash syntax, git diff --check,
case input equality, scheduled startup, library dependency receipts and finite
fields. A chemistry discrepancy needs a reproducible state and tolerance study.
