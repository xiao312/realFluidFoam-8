# Unused diffusivity calculation qualification

This module compares the exact full-fork SRK thermodynamics with and without
`fgmSkipUnusedDimix`. It does not approximate composition, change diffusion or
accept a paper comparison. The default library path remains unchanged.

Source audit at full-build revision `282aa996a78939cbdaf591520231fb2c0476567d`:
`hePsiThermo::calculate` evaluates 53 Dimix fields at every internal cell and
boundary face. Each evaluation loops 52 partners. For the retained serial mesh,
200622 cells and 402881 boundary faces imply 1,663,254,268 binary evaluations per
correction, before processor-patch overhead. Most boundary faces are wedge
planes. This is an operation count, not a measured timing. The selected Fourier
transport uses alpha for divj/divq and does not consume these Dimix fields.
Mixture construction separately rebuilds 53-square coefficient arrays and copies
four such matrices per query. This optimization leaves that cost unchanged.

Inputs: an immutable full-build runtime, a candidate rebuild of the affected
thermo registration libraries, a cold physical v2 table with matching phase
metadata, and its SRK export directory. No credentials or external network are
used. `prepare.mjs` writes only new cases; its default is a read-only plan.
The probe remains in the sibling `probe` module; heavy build/run work requires
a FlamePilot Slurm admission. No scheduler submission is implemented here.

```
node prepare.mjs --table-dir TABLE --metadata PHASE --thermo-dir SRK
node prepare.mjs --table-dir TABLE --metadata PHASE --thermo-dir SRK --out NEW_DIR
bash run.sh NEW_DIR /qualified/bin/realFluidG2ThermoProbe --plan
bash run.sh NEW_DIR /qualified/bin/realFluidG2ThermoProbe --apply
```

The preparation creates paired baseline/optimized cases from identical actual
table compositions: pure O2 and CH4, an unburnt mixed state, and a reacted mixed
state. Pressure variants retain the same prescribed p/T/Y without claiming
additional physical flamelet coverage. Each pair has identical initial fields,
thermo dictionary and probe settings. Only the explicit optimization switch
differs. Model-selection negative controls and forbidden-access controls must
fail under the optimized library. A baseline-binary opt-in run is not proof
that a new switch was implemented: require the candidate suppression log and
the accessor refusal.

The transport and combustion negative controls require the exact supported-
policy guard message emitted by the current library: explicit laminar/Fourier
or declared RAS kEpsilon/unity-Le, hePsiThermo and a supported tabulated model.
They still require a nonzero process status or SIGABRT, no spawn/timeout error,
and that specific reason. The runtime-edit and two forbidden-Dimix checks keep
their separate reasons. This checker wording follows the RAS guard contract;
it does not permit a generic failure, change any solver policy, or reinterpret
older failed checker receipts as passes.

Run blockMesh and `realFluidG2ThermoProbe -case CASE` on each case, preserving
logs and executable/library hashes. The probe reports rho, Cp, Cv, Hs, Ha, mu,
kappa, alpha, recovered T, inversion results and repeated-correction wall time.
`node compare.mjs PAIRS_DIR` requires finite property/inversion equality within
1e-12 relative (scale max(1,abs(reference))), inversion error <=1e-5 K and exact
input identity. It reports measured speedup but imposes no invented speedup
threshold. The source has not been runtime-qualified until those receipts exist.

After numerical parity, run the same short cold fresh CFD case with both
settings and compare written T, rho, Ha, Z, C, integrated mass/energy and
reported clipping counts. Use the same decomposition, number of steps and table;
report both startup and advancing-step times. A faster probe alone does not
qualify a different cold CFD trajectory. All CFD starts from time zero.

Build context: hePsiThermo's class layout and virtual signatures are unchanged.
Rebuild `src/thermophysicalModels/basic` and
`src/thermophysicalModels/reactionThermo` in a separate copy of the full runtime,
then rebuild the probe/solver against those headers. Retain/hash the other
qualified libraries. Never replace libraries beneath a running process.
No source cache, species cutoff or Takahashi coefficient change is included.

Local verification: `node --check prepare.mjs`, `node --check compare.mjs`, and
`git diff --check`. Actual parity and negative controls require the full build.

The allocation package is separate from the fixed candidate source archive.
`freeze.mjs --out NEW_DIR` writes the complete library src/ plus solver/probe Git
archive and every selected Git blob identity, excluding historical case meshes,
for candidate `ce76de25f24cfd8572b04324b192ae9544a5dbc9` (04baa plus one-time
policy validation). Without `--out` it prints a read-only plan. The package's own
Git revision must also be pinned by its caller. `package.mjs` verifies archive
SHA256, extracted regular/symlink blob bytes and all retained runtime products
before compiler-option adjustments. `build.sh MANIFEST --apply` rebuilds only
basic/reactionThermo and solver/probe, retaining the other thirteen libraries.
Its result identifies all fifteen library hashes/byte counts, source and build
adjustments; chemistry is not rebuilt. The manifest schema is illustrated by
`package.example.json`; runtime paths are supplied explicitly and no secrets
belong in it. Default `--plan` does not mutate the build.

`allocation.sh MANIFEST --apply` performs that build, properties and negative
controls, then a paired 48-cell periodic source-disabled CFD diagnostic with
actual table p/T/Y, small spatial composition variation and full-SRK Ha
initialization. Both cases start at zero, run 20 identical 1 ns steps, and write
every fifth step. The actual initializer/solver log is retained. `compare-cfd.mjs`
checks all written scalar/U fields and all integrated energy-state records at
1e-12 relative, finite positive thermo, zero clipping, source-disabled status
and normal completion. Actual conservation drift is reported separately: this
is equivalence qualification, not acceptance of a new flame/table model.

An optional manifest `cfdParity` object selects `chemistry` (`disabled` default,
or `table`), `sourceIntegration` (`explicit` default or `strangFixedState`),
`deltaT_s` (default 1e-9, positive through 5e-8), and `initialEta` (default .8,
inside .03 to .97). The source-on qualification uses `.5`, 25e-9 and
`strangFixedState` for twenty steps. Source-on requires the literal executing
caloric audit at 1e-8; the comparator also verifies nonzero progress, source
stage/history records and the unchanged 1e-12 field/history parity limit.
Both modes retain fresh zero-time initialization and the exact table. No
synthetic chemistry reference or scientific acceptance is substituted.
