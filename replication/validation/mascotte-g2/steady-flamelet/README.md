# Steady-flamelet case inputs

This module verifies a separately identified physical one-dimensional steady
flamelet export and supplies fresh initialization to the shared G2 geometry
generator. It does not generate chemistry, repair species or declare a profile
converged. The exact original residual and approximate-steady status are retained.

Inputs are `steady.tbl`, `manifest.json` from the physical exporter, exact NASA
phase metadata, a separately bound full-SRK thermo dictionary and a qualified
mesh. `input.mjs` validates file hashes, species, element coefficients, endpoints
and linear elemental balance. It returns one composition per Z; no progress
coordinate or source is accepted. Output c is derived Y_CO2+Y_CO only.

Use `direct-fgm/prepare.mjs --closure steady-flamelet` with cold-real-fluid thermo,
strict bounds, explicit source mode and unused-diffusion suppression disabled.
The default initialization is `{ "mode": "uniform-steady", "mixtureFraction": 0 }`:
pure cold oxygen throughout the chamber at time zero, with actual pure inlet
states. Any mixture begins reacting through the prescribed steady composition
as Z is transported. There is no fabricated ignition kernel or evolved CFD.
Ha is initialized from generated Y/T/p by the same executing full-SRK runtime.

Dependencies: Node built-ins and shared hashing/thermo/mesh/observation helpers.
The solver uses the independent C++ reader/model in `src/combustionModels/steadyFlamelet`.
No secrets, network or scheduler calls occur in input loading. New case outputs
must stay within the authorized project. Run without `--out` for a read-only plan.

Verification uses the actual retained table: exact pure endpoints, an interior
linear lookup, species/element sums and an out-of-range refusal. The allocated
solver qualification must prove Z-before-Y-before-E order, no c equation/source,
full-SRK enthalpy inversion, no double heat release and time-zero provenance.
No standalone parser result establishes a flame or paper match.

`prepare-periodic.mjs INPUT.json --plan` prepares the bounded qualification plan.
The input has `table`, `metadata`, `thermo` and new `out` paths. `--apply` requires
an allocation and creates 48 periodic cells, Z=0.2+0.005*sin(...), twenty25ns
steps, the actual mapped composition and an explicit zero Ha placeholder.
Run blockMesh/checkMesh, then the exact full-runtime probe with `-initialize-Ha`,
then the rebuilt solver; `check-periodic.mjs CASE` audits lifecycle, diagnostic
c, caloric closure and measured energy/mass change. No evolved field is read.
It reuses the existing periodic geometry generator and replaces its analytic
table/species/thermo inputs completely before execution. Only the new physical
steady model is selected. An exact-source build and runtime receipt are still
required; this case does not bypass that qualification.
