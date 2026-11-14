# Cold real-fluid execution

Runtime linkage accepts both ldd forms: `name => /path` and direct absolute
dependencies. Each required custom library must still resolve to the exact
registered file. Real paths permit explicit aliases to the same immutable bytes;
hash checks remain mandatory. Missing libraries or a different real file fail.
`runtime-linkage.mjs` preserves all entries for this audit; it grants no approval.

The generator's `cold-real-fluid` mode is preparation, not a qualified runtime.
It requires an actual cold physical table (85 K oxygen,288 K methane,5.61 MPa;
or Schmitt's83K oxygen,300K methane,5.6MPa)
and exact PR/SRK export. A warm table is rejected. SRK and PR remain named
choices; neither is the paper's volume-translated PRVTA model. The fixed-pressure
table has no independent enthalpy dimension, so measured `T - fgmTdiag` and
pressure departure remain necessary coupling diagnostics.

Use the completed isolated full-fork build as a read-only library dependency.
Rebuild only the solver and runtime probe from their frozen source against that
build's headers and libraries. Do not use the stock-thermo shim executable with
the full fork. The admission owns the source/archive/environment identities;
`initialize-cold.mjs` records actual executable and library hashes and checks
their dynamic bindings against the original full-build receipt.

```sh
node initialize-cold.mjs --case NEW_CASE --runtime FULL_BUILD \
  --probe NEW_BIN/realFluidG2ThermoProbe --solver NEW_BIN/reactingFoamSolveZ
# Inside the existing Slurm allocation, after inspecting that read-only plan:
node initialize-cold.mjs --case NEW_CASE --runtime FULL_BUILD \
  --probe NEW_BIN/realFluidG2ThermoProbe --solver NEW_BIN/reactingFoamSolveZ --apply
```

The case must contain only time zero and no decomposed/evolved state. The
initializer optionally runs its explicit localized ignition `setFields`, then
the actual runtime probe. The probe writes Ha from Hs(p,T,Y) plus formation
enthalpy, retaining EOS departure exactly once and the case-owned boundary
types. It then writes the opt-in solver marker. The wrapper records before/after
field hashes and does not submit jobs, run CFD, or change model coefficients.
Only then decompose and execute the admitted solver. Initialization errors
retain their start receipt and log; do not reuse that directory for a new run.
Child stdout/stderr stream directly into the retained log from process start;
the wrapper does not buffer a long thermodynamic initialization in memory.
Timestamped wrapper boundaries and probe phase markers distinguish thermodynamic
construction, Ha evaluation and output. The full-mesh serial initialization has
a 900-second stage limit; observed timings should determine a later qualified
parallel implementation, not repeated unobserved 300-second retries.

`initialize-cold.mjs --parallel-ranks N` is opt-in and must match the admitted
single-node task count. It applies any fresh ignition recipe serially, then
decomposes, runs the same full-runtime probe on all ranks, verifies every rank's
Ha and marker, and reconstructs only Ha at time zero. It does not run CFD or
import an evolved field. The caller must not decompose again. Boundary audits
are rank-local files; summing by physical patch name is an explicit analysis
step, avoiding unmatched collectives across differing processor-patch lists.
The batch first runs `qualify-parallel.sh` on fresh small pure-O2 and pure-CH4
cases, comparing serial and reconstructed parallel Ha and all rank markers.
Reconstruction explicitly selects `-withZero -time 0`; OF8 otherwise excludes
the initial time even when `-time 0` is supplied. A missing time is a preparation
failure, never permission to reuse an evolved field.
This is initialization parity, not a flame or G2 validation result.

The guard is enabled only for these cold cases and requires time zero with a
matching thermoType marker. It prevents accidental execution of zero Ha
placeholders; it does not confer science approval. Hash receipts and the
immutable admission still bind all inputs. Read-only inspection needs the
selected full runtime; mutation additionally requires `SLURM_JOB_ID`.

Verification: `node --check initialize-cold.mjs` and the read-only generator
must pass. The actual physical table, full-runtime initializer, inlet boundary
pressure check and clean-start cold transport/reacting execution must then run
in Slurm. Missing physical cold data is a refusal, never a synthetic success.
The measured density/enthalpy and source consistency determine the next change.

The first cold runs remain laminar engineering diagnostics on the retained
wedge. A later RANS baseline needs a declared turbulence model and inlet
turbulence conditions; LES also needs a mesh/time-resolution assessment and
statistical sampling interval. Neither is inferred from a short startup run.

## Thin full-library batch

`bash batch/cold-run.sh MANIFEST --plan` inspects a
`forge-cold-g2-batch-v1` manifest. `--apply` executes only inside its admitted
single-node Slurm allocation. Fields are the warm batch's source/archive/output
paths and table hashes, plus `runtimeDirectory`, `runtimeReceiptSha256`, and
`thermo` containing `directory`, `dictionarySha256`, `manifestSha256`.
`ranks` defaults to 16 and `memoryGiB` to 16; both must match the admission.
`g2` supplies `endTime_s`, `observations`, `decomposition`, and
`reactingInitialization` using the initialization schema above. A missing
reacting initialization is refused, rather than silently choosing an ignition
region. Nonreacting transport always starts from actual Cmin at the same Z.
Optional `g2.transport` and `g2.reacting` override `endTime_s`, `initialDt_s`,
`maxDt_s` and `observations` independently. Positive initial <= maximum <= end
time is required. For example, source-off transport may run 2 us with a 100 ns
ceiling while the first stiff reacting diagnostic runs 0.1 us with a 0.5 ns
ceiling. Those are declared run choices, not an automatic chemistry stability
proof; the physical source and table coverage still determine acceptable steps.

The batch reuses, verifies, and never changes the complete library build. It
rebuilds only the frozen solver and probe, runs an actual admitted-rank MPI
allreduce, then fresh cold transport and fresh reacting cases. Each has its own
full-runtime Ha preparation, mesh check, decomposition, logs, profiles and
reconstruction. A failed physical stage retains evidence and stops this batch;
it cannot be relabelled as completed CFD. This wrapper has no scheduler client
or retry loop. Cold physical data and its exact metadata-derived thermo export
must already exist. Verify scripts with `bash -n` and `node --check`; actual
qualification remains the Slurm execution, not these syntax checks.
