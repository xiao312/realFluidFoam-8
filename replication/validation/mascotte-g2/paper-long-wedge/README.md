# Schmitt-length G2 wedge

Own `paper-exit-wedge-20000-long-v1`: x0..0.4m,400axial cells,50radial cells and
one azimuthal cell. Retain1mm axial spacing,5mm O2 exit diameter,0.3mm lip and
5.6/10mm methane annulus. This extends the paper-exit10000-cell recipe for the
400mm Schmitt domain. Old assets remain unchanged. Both omit upstream taper,
square corners and three-dimensional LES.

The generator and evidence audit reuse the sibling paper-exit implementation
with separate mode, recipe hash, counts, wall-face count and expected volume.
The coarse-wedge ASCII parser is the only source dependency. The direct-G2 case
generator consumes the qualified manifest and mesh hashes. No network or secrets.

`node generate.mjs` prints a read-only plan. Add `--out NEW_MESH_CASE`, then run
blockMesh/checkMesh inside Slurm. `node audit.mjs --case CASE` inspects geometry;
add `--out NEW_ASSET` to retain its qualified bytes and logs. Verify20000cells,
40501points,80050faces, domain volume and inlet areas. Sampling must select0.4m.
Mesh qualification does not establish paper-matched turbulence or combustion.

The 400x50 collapsed-axis wedge has 39550 internal faces: 399x50 axial
plus400x49 radial. BlockMesh/checkMesh confirmed the count on14November2026;
the earlier39750 expectation was an arithmetic error, not a mesh defect.
