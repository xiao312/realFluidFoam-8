# Reacting flow with optional transported manifold coordinates

Advance pressure, momentum, species/composition and energy with OF8 PIMPLE.
Tabulated combustion models own their Z and optional progress fields. Direct
species/none models use the species equations and do not require a dummy Z field.
Only a tabulated model enters ZEqn; the existing tabulated equation order remains.

Inputs are an OF8 case and explicit runtime libraries. Standard dictionaries
select thermo, momentum transport, combustion and PIMPLE controls. Tabulated
absolute-Ha mode requires a hashed actual table and fresh initialized Ha. A
nonreacting H2/O2 contact can use sensible h because both formation references
are zero. No chemistry, table, coefficients or acceptance is inferred here.

Outputs are solver fields, sampled diagnostics and optional energy/continuity
budgets. Dependencies: matching realFluidFoam or explicitly qualified stock
thermo headers/libraries and the custom combustionModels registration. Cases,
evaluator and scheduler stay outside the solver. No network or credentials.

Minimal build: within Slurm set LIB_rfFoam8_SRC, FOAM_USER_LIBBIN and
FOAM_USER_APPBIN to isolated matching paths, then wmake. Record source, compiler,
exact linked libraries and executable hashes. Verification requires compile/link,
an actual none-model Schmitt contact with no Z, and a fresh tabulated G2 startup.
Normal exit establishes numerical execution only. Do not build into a live case.
