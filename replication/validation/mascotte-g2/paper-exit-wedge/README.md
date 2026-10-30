# Coarse G2 diagnostic with paper exit areas

This module owns the distinct `paper-exit-wedge-10000-v1` mesh recipe and its
qualification loader. It places the co-planar injector exit at x=0 with O2 radius
2.5 mm, separator lip 2.5-2.8 mm, and methane annulus 2.8-5.0 mm. These exit
dimensions follow Mueller (2015) and Cavalieri (2025, TF). It is a partial geometry
diagnostic, not their complete tapered injector, square chamber or LES mesh.

The existing `coarse-wedge-10000-v1` asset and registered 200622-cell mesh remain
unchanged. A new case must select `--mesh-mode paper-exit-wedge-10000-v1` explicitly.
The source/thermodynamic/initialization requirements of `direct-fgm` still apply.

## Recipe and measured origin

The fixed wedge covers x=0..0.2 m and r=0..0.025 m, with azimuth +/-2.5 degrees.
Four radial bands are `[0, 0.0025, 0.0028, 0.005, 0.025]` m and have
`[8, 6, 10, 26]` cells, with 200 axial cells and one azimuthal cell: 10,000 cells.
Uniform grading and cell counts preserve the earlier numerical companion's
topology while changing the O2 exit area and lip thickness. The external wall is
no-slip; the collapsed axis is an empty, zero-face patch. All patch names needed
by the case generator are preserved. The upstream ducts/taper, injector-rim
recess, inlet precursor turbulence and square chamber corners are omitted.

The registered legacy mesh's raw x=0 is an upstream inlet plane. A short indexed
binary read verified its O2 inlet radius 1.6 mm and methane inlet radii 2.8-5 mm.
Its no-slip injector surfaces reach raw x=0.01 m, where the O2 exit radius is
2.5 mm and the separator occupies 2.5-2.8 mm. Thus `x_plot=x_raw-0.01 m` is a
measured exit-origin interpretation for that legacy mesh, not a shift to apply
to this new x=0 exit recipe. The legacy upstream O2 diameter 3.2 mm differs from
the papers' 3.6 mm. See [reference-geometry.json](reference-geometry.json) and
[paper-conditions.md](paper-conditions.md); no legacy mesh is relabelled qualified.

At fixed mass flow and density the new O2 inlet velocity is
`(1.6/2.5)^2=0.4096` times the old co-planar pilot velocity. Methane area is
unchanged. Therefore the methane/O2 momentum-flux ratio increases by about 5.96;
this is a physical geometry change, not a cosmetic coordinate correction. Use
the existing mass-flow boundary with measured area and executing EOS density,
not one of the papers' inconsistent quoted velocity labels.

## Inputs, outputs and boundaries

`node generate.mjs` emits a read-only recipe/hash plan. Add `--out NEW_CASE` to
write a fresh blockMesh case. After allocated `blockMesh` and
`checkMesh -allTopology -allGeometry`, `node audit.mjs --case CASE` reads actual
mesh bytes, volumes, patch areas and logs. Add `--out NEW_ASSET` to preserve a new
qualified mesh asset. Existing outputs fail rather than being overwritten.
Only a passing mesh-tool receipt plus the fixed recipe and matching file hashes
can be consumed by `inspectPaperExitMesh`. This qualifies geometry construction,
not CFD physics. An old coarse or canonical manifest fails the new loader.

Dependencies: Node standard library, the unchanged ASCII mesh parser in
`../coarse-wedge/ascii-mesh.mjs`, and OF8 mesh utilities during allocated execution.
The module deliberately owns separate fixed recipe/qualification schemas so an
old asset cannot change meaning. `direct-fgm` is its dependent. No credentials,
network service, solver execution or scheduler admission is used here.

## Allocated phase

The admitting wrapper verifies its frozen source archive and supplies its commit:

```sh
bash replication/validation/mascotte-g2/paper-exit-wedge/qualify.sh \
  /workspace/build/SOURCE /workspace/results/paper-exit-mesh-r1 \
  /workspace/mesh-assets/paper-exit-wedge-10000-r1 SOURCE_COMMIT --plan
# Repeat with --apply only in the existing Slurm allocation.
```

The phase requires the already sourced qualified OF8 environment; it never sources
bashrc with inherited arguments. It runs strict Bash, validates fresh paths under
/workspace, records module/tool hashes and actual mesh-tool Build lines, and writes
a phase receipt even on failure. Its nonzero return must block dependent G2 CFD,
while the caller may preserve independent runtime/source checks. It submits no job.

## Verification

```sh
node --test replication/validation/mascotte-g2/paper-exit-wedge/recipe.test.mjs
node replication/validation/mascotte-g2/paper-exit-wedge/generate.mjs
bash -n replication/validation/mascotte-g2/paper-exit-wedge/qualify.sh
```

The focused local check verifies the new exit area, positive block orientation,
matched interfaces and complete patch partition. Actual blockMesh/checkMesh and
loading the retained asset must still pass in Slurm before any new geometry is
used for the 100 us pilot. Paper comparison requires additional turbulence,
geometry, transport, source and statistical qualification.
