# Tapered injector diagnostic

Reconstruct the G2 oxygen taper and methane annulus as a distinct axisymmetric
mesh. This is a geometry sensitivity, not the full square-chamber LES geometry.
The existing exit-only meshes and their qualifications remain unchanged.

Inputs are the fixed recipe in `recipe.mjs`: oxygen diameter 3.6 to 5 mm,
10-degree half-angle (Sharma Figure 3), lip thickness 0.3 mm and methane
diameters 5.6/10 mm. The upstream boundary is exactly at the beginning of the
taper, whose length follows from these dimensions. No unreported straight-duct
length is invented. The methane annulus extends to that same upstream plane.
Chamber length is 200 mm, radius 25 mm and wedge opening 5 degrees. No turbulence,
square corners, nozzle, lip heat conduction or upstream precursor is included.
The paper's angle convention must remain visible; this is not a measurement of
the experimental injector. See `../paper-exit-wedge/paper-conditions.md`.

`node generate.mjs` prints a read-only plan. `--out NEW_CASE` writes a fresh
blockMesh dictionary, mesh-tool dictionaries and recipe receipt. Existing output
is refused. Run blockMesh/checkMesh through FlamePilot Slurm; a generated
dictionary or local topology test is not an executed-mesh qualification. This
module does not select a CFD closure, import states or submit jobs. Its mesh is
accepted only by the explicit `g2-tapered-injector-wedge-v1` direct-fgm mode
after `audit.mjs` has created a measured asset. The audit reads original mesh
bytes, counts, inlet and exit areas, volume and actual mesh-tool receipts; the
loader checks these again. It never relabels an exit-only or registered asset.

`node audit.mjs --case EXECUTED_CASE --logs TOOL_LOG_DIRECTORY` prints the
read-only measurement. Add `--out NEW_ASSET` to preserve immutable input bytes,
logs and the measured manifest. Run measurement in the admitted qualification
or CFD allocation, then consume that asset with the case generator. The oxygen
boundary area is the3.6mm upstream section; its5mm exit area is measured on the
internal x=0 interface. Sampling uses x=0 at the exit, not the upstream boundary.

`priming.mjs` emits the two time-zero pure-stream field regions for the case
generator. It sets composition, Z, C and temperature; real-fluid Ha remains a
placeholder until the executing runtime initializer runs. It neither supplies a
velocity precursor nor ignites the chamber. Its input states come from the exact
table endpoints; no evolved field is read.

`node verify-priming.mjs CASE` checks actual undecomposed time-zero Z/C/T and
pure-stream species against cells classified from their mesh vertices. It
requires320 oxygen-duct and400 methane-duct cells, independently of cell order,
and fails if setFields was omitted. It does not advance or modify a field.

Dependencies: Node standard library. Verification additionally uses the existing
ASCII mesh parser and allocated OpenFOAM 8 utilities. The direct-fgm case
generator consumes the qualified asset. No secrets or network
access. Outputs and logs belong under the selected project root.

```sh
node --test replication/validation/mascotte-g2/paper-injector-wedge/recipe.test.mjs
node replication/validation/mascotte-g2/paper-injector-wedge/generate.mjs
```

Expected: positive oriented blocks, matched internal faces, complete external
patch partition and independently calculated inlet areas. Allocated mesh checks
must also report `Mesh OK.` before this asset is considered for CFD.
