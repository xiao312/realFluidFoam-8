# Reviewed legacy injector mesh

Preserve the owner-reviewed r222/200622 geometry while reducing cell count for physical diagnostics. The measured upstream oxygen bore is3.2mm, taper starts atx5mm and reaches5mm diameter atx10mm. Methane diameters5.6/10mm, outer casing13mm, chamber50mm diameter and rawx0..200mm. The outer fluid pocket upstream of the injector exit is retained. Opening5degrees; paper axial distance is rawx minus10mm. These are legacy dimensions, not a claim of exact experimental geometry.

Inputs: fixed measured recipe, retained reference boundary edges and their SHA256. Outputs: fresh blockMesh case, executed mesh evidence and hash-bound asset. No CFD, evolved initialization, solver closure or scheduler admission is owned here. Node standard library and the existing ASCII parser are dependencies; direct-fgm is the consumer. No secrets/network. All allocated tools run through FlamePilot Slurm adapters.

`node generate.mjs` prints the plan; `--out NEW_CASE` refuses existing output. Run blockMesh and checkMesh in an allocation, then `node audit.mjs --case CASE --out NEW_ASSET`. The audit checks actual reference boundary distances, inlet areas, volume, mesh-tool completion and source dictionary identity. Geometry serialization tolerance10nm covers measured legacy CAD jitter; it is not a solution acceptance tolerance. Cell distribution may change only through a new recipe identity.

Verification: read-only generation and an allocated blockMesh/checkMesh/audit; all reference edges must match the generated boundary and vice versa. The old geometry is a negative comparison, not silently accepted.

`verify-priming.mjs FRESH_CASE` checks all640 oxygen and800 methane duct cells against their pure-stream time-zero T/Z/C/O2/CH4, verifies the actual copied mesh and rejects evolved/decomposed cases. It changes no fields.

`initialize-duct-velocity.mjs FRESH_CASE [--apply]` is an optional analytic initial condition. It uses executing densities and actual mass-flow areas, sets plug velocity in the straight ducts and continuity/tangent-wall velocity through the measured taper. Chamber and pocket remain at rest. It changes only original-zero internal U, records added kinetic energy, and claims neither a developed boundary layer nor a discrete divergence projection. Compare against the separate stationary/ramped control.

Resolution profiles change cell counts only. `generate.mjs --resolution debug-coarse`
plans4460cells, versus the unchanged default `standard`17840cells. Both retain
identical block vertices, patches, grading and approved boundary geometry.
`--out NEW_CASE` creates a fresh case; arbitrary geometry/profile overrides are
not accepted. A profile is included in the recipe identity and must pass its own
allocated blockMesh/checkMesh/reference-edge audit before use. Coarse-grid runs
are physical debugging controls, not replacements for resolution-qualified paper
comparisons. No running mesh or case is modified.

`node verify-resolution.mjs` checks unchanged default dictionary/recipe hashes,
identical geometric block/patch definitions and distinct resolution identities.
The command also rejects an unknown profile. These local checks do not qualify
an executed mesh. Duct priming counts follow the selected profile while retaining
the original pure-stream checks for every classified cell.
