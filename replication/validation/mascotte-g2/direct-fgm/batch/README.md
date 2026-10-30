# Bounded warm-G2 execution batch

This module rebuilds the solver against the retained, hash-qualified custom
combustion library and stock OF8 thermodynamics. It then runs fresh heating,
contact, formation-energy conversion, and physical-table closed-state cases.
Only after those numerical checks pass does it qualify an admitted-rank MPI contact
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

Optional `ranks` defaults to 4 and accepts 1..32 on one admitted node;
`memoryGiB` records the requested total memory (default 4). Optional `g2`
contains `endTime_s` (default 0.00002), `observations` and `decomposition`, using
the parent generator's configuration schemas. At 16 ranks the default geometric
split is hierarchical [8,2,1]; at 32 it is [8,4,1]. Other counts use [N,1,1].
The serial and parallel contact cases use the same max(80,4*N) fresh cells.
MPI tests require the actual N-rank sum N*(N-1)/2. Admission resources remain
the coordinator's responsibility; this wrapper verifies the actual task and
node counts and records the configuration rather than inventing an allocation.

Example additional manifest fields for the first 16-rank startup:

```json
{
  "ranks": 16,
  "memoryGiB": 16,
  "g2": {
    "endTime_s": 0.00002,
    "observations": {
      "profileInterval_s": 0.000001,
      "fieldInterval_s": 0.000005,
      "imageGrid": { "axialPoints": 401, "radialPoints": 81 }
    },
    "decomposition": { "method": "hierarchical", "n": [8,2,1], "order": "xyz" }
  }
}
```

Run `bash run.sh MANIFEST --plan` to inspect the plan without mutation.
`--apply` requires an admitted f46 OF8 environment, the exact requested Slurm
task count, a single node, and new output/case paths. This script never submits
or cancels scheduler jobs. The coordinator owns
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
single-host launching and no scheduler/rsh spawning. Its actual requested-rank
allreduce and serial/MPI contact agreement are required. A successful launcher
version/help check alone is insufficient. Per-stage timeouts preserve failures;
the overall scheduler wall allowance remains authoritative. The G2 stage is
strict-bounds and fresh time zero. No clipped fallback or
restart is attempted. Local verification is `bash -n run.sh build.sh` and
`node --check preflight.mjs compare-contact.mjs`; actual qualification requires
the admitted batch and retained results. Dependencies are the sibling case and
check modules, Node24, GCC11, wmake, stock OF8 mesh tools and matching OpenMPI.

No secrets are consumed. The module emits stage exit receipts and actual solver
logs/fields. It neither grants independent code/science approval nor publishes.

`node bind-table.mjs NEW_CASE --plan` reads and hashes its case-owned table;
`--apply` additionally requires Slurm and a fresh undecomposed time-zero case.
It binds the absolute table path in combustionProperties before decomposition,
recording original/final dictionary and table hashes. This avoids the older
library's processor-local relative-path bug without changing the table, copying
it per rank, or rebuilding libraries. An external table or prior binding is
refused. Both warm and cold batches use this preparation step. The separately
corrected library resolver must still receive its own compiled qualification.

A bounded diagnostic exception exists only for the physical closed case when
its failed criteria are exactly the assembled residual and legacy-identity
checks, while all conservation, pressure, endpoint and clipping checks pass.
The fresh executable must record the actual absolute matrix summands and
operation counts. `allow-physical-diagnostic.mjs` independently checks the
standard gamma_n floating-point bound for evaluating those stored coefficients;
every residual must be within that bound and every legacy identity error within
three such bounds. This addresses cancellation at a tiny physical time step,
not a physical model discrepancy. The original failed verdict and thresholds
remain untouched. A hash-bound exception receipt permits only the subsequent
bounded diagnostic; it confers no code/science approval. Missing evidence or
any other failure stops the batch. Older logs without measured summands cannot
be used for this exception.

The separate `cold-run.sh` path is specified in `../cold-runtime.md`. It reuses
the verified complete fork library build and rebuilds only solver/probe; it
does not replace the warm batch's stock-thermodynamics baseline or silently
change the chosen physical table.
