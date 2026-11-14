# Relaxed-species source control

This module prepares fresh one-cell inputs for the actual `relaxedTable` model's
source/property diagnostic. It does not run flow, advance physical time, submit
jobs or establish sealed-volume conservation or paper agreement.

Inputs: an absolute, full-ABI-qualified build directory, a full53 SRK thermo
directory, the unchanged strict table file, a new case path and Cr (1 or100).
`prepare.mjs BUILD THERMO TABLE NEW_CASE CR [--apply]` prints a read-only plan;
apply requires an admitted Slurm allocation. It invokes the build's existing
probe case factory, initializes unburned CH4/O2 at Z=0.2, p=5.6MPa and300K,
and configures absolute Ha and the new model. Actual Ha initialization and
`-relaxation-probe` execution belong to the caller and must use that same build.

Outputs: original-zero case fields/dictionaries and an explicit active-input
manifest. The factory manifest is retained separately; changing the closure,
initial state or inert bookkeeping is not hidden under its old identity.
No CFD fields from prior runs are read. Cr1 is an algebraic instantaneous limit;
Cr100 comes from Schmitt Eq12. Neither selects the paper equilibrium closure.

Dependencies: Node, the qualified source probe factory, OF8, strict table reader
and `reactingFoamSolveZ -relaxation-probe`. Dependents: bounded source diagnostics.
No credentials, network, scheduler API or agent runtime are used here.

Example: run the plan, then apply inside Slurm; run blockMesh, initialize Ha,
hash active time-zero inputs and execute the diagnostic. Verification is the
actual source recurrence, Qdot identity and caloric/unchanged-Ha CSV. Preserve
failed rows/exit codes; compilation or synthetic algebra alone is not physics.

`configure-flow.mjs NEW_CASE 1|100 [--apply]` is the companion adapter for a new
undecomposed G2 factory case. It preserves table, mesh, initial/inlet fields and
thermo coefficients, changes actual species ownership and inert bookkeeping,
and enables the already tested conservative-density/fixed-h pressure controls.
It records every changed dictionary hash in a separate active-input manifest.
The existing factory manifest is preserved. Cr1 is compared with the old
instantaneous model; Cr100 is a new physics/numerics diagnostic. Every flow run
starts from original zero and reports actual Cr*dt. No paper mean is inferred.
