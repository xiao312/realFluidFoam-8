# Bounded warm-G2 execution batch

This module rebuilds the solver against the retained, hash-qualified custom
combustion library and stock OF8 thermodynamics. It then runs fresh heating,
contact, formation-energy conversion, and physical-table closed-state cases.
Only after those numerical checks pass does it qualify a four-rank MPI contact
case against serial and execute the warm G2-mesh startup diagnostic. A failed
or absent prerequisite produces a retained refusal, not a fabricated pass.
These are coupled-solver diagnostics, not cryogenic G2 or paper acceptance.

Input is one JSON manifest with schema `forge-warm-g2-batch-v1`, `sourceCommit`,
`sourceArchive`, `sourceArchiveSha256`, `buildDirectory`, `resultDirectory`,
`casePrefix`, and `table` containing `directory`, `metadata`, `sha256`,
`receiptSha256`, `metadataSha256`. All paths must be absolute under /workspace.
The table is explicit and immutable; do not silently select the previous
Spitfire table if its energy formulation is known to be flawed. The generator's
own input receipts still validate all scientific identities.

Run `bash run.sh MANIFEST --plan` to inspect the plan without mutation.
`--apply` requires an admitted f46 OF8 environment, four Slurm tasks, a single
node, and new output/case paths. The existing adapter caps this request at 4 GiB
total. This script never submits or cancels scheduler jobs. The coordinator owns
admission, source staging, deadlines and accounting. All generated state remains
under the trial workspace, including HOME, TMPDIR and MPI session files.

The source archive must include the solver, src/combustionModels, fgm-of8 direct
verification/fixtures, and this entire direct-fgm module. Produce it with Git
core.autocrlf=false/core.eol=lf and verify archive members against raw Git blobs.
The retained library is fixed to SHA256 3b0f1926a977f48701587cd323093d592dcb2a4020efd198e81ea72889d3d16d.
The immutable source identifies every executable change; the binary hash and
linked library paths are recorded after the rebuild. Full realFluidFoam EOS
libraries are deliberately outside this warm ideal-gas batch.

MPI uses the allocation's OF8/OpenMPI launcher and libraries, with isolated
single-host launching and no scheduler/rsh spawning. Its actual four-rank
allreduce and serial/MPI contact agreement are required. A successful launcher
version/help check alone is insufficient. Per-stage timeouts preserve failures;
the overall scheduler wall allowance remains authoritative. The G2 stage is
strict-bounds, fresh time zero, four ranks and 20 us. No clipped fallback or
restart is attempted. Local verification is `bash -n run.sh build.sh` and
`node --check preflight.mjs compare-contact.mjs`; actual qualification requires
the admitted batch and retained results. Dependencies are the sibling case and
check modules, Node24, GCC11, wmake, stock OF8 mesh tools and matching OpenMPI.

No secrets are consumed. The module emits stage exit receipts and actual solver
logs/fields. It neither grants independent code/science approval nor publishes.
