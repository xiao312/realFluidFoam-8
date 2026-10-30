# Coarse co-planar G2 diagnostic wedge

This module prepares a separate 10000-cell diagnostic companion for faster
millisecond development. It is not a coarsening of the retained 200622-cell mesh
and does not reproduce the paper injector geometry. The original mesh and its
immutable identity checks are unchanged.

The fixed recipe is 200 axial cells over x=0..0.2 m, one azimuthal cell across
-2.5..+2.5 degrees, and radial bands 0/1.6/2.8/5/25 mm with 8/6/10/26 cells.
At x=0 the bands are oxygen inlet, a solid injector-face annulus (`geom`),
methane inlet, and outer wall. The outer cylindrical boundary is no-slip.
This omits upstream ducts and unresolved injector-lip details. x=0 is a known
co-planar diagnostic inlet, not a verified transform of the original mesh.

Inputs: the fixed recipe in `recipe.mjs`; generated mesh bytes and actual
`log.blockMesh`/`log.checkMesh` for qualification. Outputs: a new blockMesh case,
then a separate hashed mesh asset with measured inlet geometry. No credentials,
network, solver, or scheduler operations occur here. Node.js built-ins are the
only dependencies. `../direct-fgm/prepare.mjs` is the sole consumer and requires
`--mesh-mode coarse-wedge-10000-v1` to use this asset; canonical remains default.

```sh
node generate.mjs                         # read-only recipe/dictionary plan
node generate.mjs --out NEW_MESH_CASE      # new directory, no mesh execution
# Execute these two commands only inside an admitted Slurm allocation:
blockMesh -case NEW_MESH_CASE > NEW_MESH_CASE/log.blockMesh 2>&1
checkMesh -case NEW_MESH_CASE -allTopology -allGeometry > NEW_MESH_CASE/log.checkMesh 2>&1
node audit.mjs --case NEW_MESH_CASE        # read-only measured audit
node audit.mjs --case NEW_MESH_CASE --out NEW_MESH_ASSET
node ../direct-fgm/prepare.mjs --mesh-mode coarse-wedge-10000-v1 \
  --mesh-dir NEW_MESH_ASSET --table-dir TABLE --metadata PHASE
```

`audit.mjs` refuses missing/failed mesh-tool logs, changed recipe dictionaries,
unexpected patch types/counts, wrong cell counts, invalid ownership, nonfinite
points, mismatched areas or geometry. It reads ASCII mesh files only and records
actual SHA256/byte sizes. A future recipe needs a new version rather than editing
a manifest to bypass checks. The opt-in loader repeats hash and geometry checks.
This is a trusted project provenance boundary, not a hostile-input sandbox.

All original patch names are retained. The collapsed axis has zero faces and
type `empty`, following the [OF8 collapsed-block guidance](https://doc.cfd.direct/openfoam/user-guide-v8/blockmesh#x25-2030005.3.5).
The case generator selects `empty` on that axis only in this explicit mode;
canonical fields keep their existing `symmetry` condition. `slipwalls` is an
empty wall patch; `noslipwalls` includes the outer radial wall and x=0 outer band.
Straight wedge edges give face area fraction sin(5 degrees)/(2*pi), which is
recorded separately from the nominal angular fraction 5/360.

Verification: `node --test recipe.test.mjs`, plus `node --check` for all module
files and the modified case preparer. Local tests check the actual dictionary's
block orientation, shared faces, patch assignment, cell counts and analytical
areas. They do not qualify an executed mesh. The first actual allocation must
run both mesh tools and retain their full logs before preparing CFD. No CFD
state is imported; every resulting case starts from its own original time zero.
