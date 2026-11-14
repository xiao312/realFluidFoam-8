# Audited author-loop control

Responsibility: copy the upstream realFluidFoam application on a case-sensitive
Linux filesystem and add observational witnesses plus the existing enforcing
caloric audit. It distinguishes original-loop behavior from partial ports into
reactingFoamSolveZ. It does not implement FGM, modify upstream source in place,
change equations, repair inversion or establish scientific acceptance.

Input: frozen source root containing applications/solvers/realFluidFoam and the
existing reactingFoamSolveZ/fgmThermoClosure.H. prepare-module.mjs prints a read-only
patch plan; --apply requires SLURM_JOB_ID and a new destination. The output is an
independent realFluidFoamAudited application, patch receipts and standard fields.
No network, secrets or restart data are consumed. Dependencies are the exact
parent15-library runtime and existing contact initializer. The operator owns
immutable staging, compiler options, scheduler submission and field collection.

Example: node prepare-module.mjs SOURCE_ROOT NEW_MODULE [--apply]

Verify with node --check, inspect before/after hashes, then wmake in Slurm with
qualified GCC11/custom-library flags. Compare independent fresh O2/mixture cases.
The original one-pass thermo inversion remains one pass; the added audit uses
exactly the existing1e-8 scale and must not be treated as a new solver equation.
A failure before the requested end time remains a failed control. Report the
pressure/temperature/total-energy histories and original solver/library identities.
No normal exit alone or retained transient is a developed paper comparison.
