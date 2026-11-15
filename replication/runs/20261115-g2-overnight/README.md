# G2 overnight coupling controls

Responsibility: reproducible original-zero pressure/coupling and property diagnostics for the owner window ending2026-11-16 09:20Asia/Shanghai. Not production qualification or a replacement for the fixed paper ladder. Inputs: exact prior qualified binary/library receipts, registered case/table/thermo and frozen per-run scripts. Outputs: new cases, raw physical profiles, audits, terminal receipts and later paper comparisons. All failed runs remain evidence.

Dependencies: source-clock-S13 qualified solver80fa810, R54 thermo51075d5, the direct-G2 factory and shared one-cell property probe. HPC execution is external through pinned FlamePilot Slurm adapters; no scheduler/model-provider dependency in the solver. Dependents: existing g2-paper-review/Forge figure import. No credentials in inputs; all writes/caches/logs remain inside the configured project root.

Each case script performs a read-only plan before mutation and refuses evolved/decomposed output. Minimal example: plan the ignored request with the FlamePilot adapter, then submit its exact frozen key. Inside the allocation main.sh verifies input and runtime hashes before preparing a fresh case.

Verify node --check for helpers, bash -n for wrappers, input manifests and actual executing pressure/source/energy controls. Check source/binary/case identities independently. Read physical profiles, continuity, EOS density, caloric and energy/source diagnostics; normal exit is not paper agreement. Compare matched physical times and preserve the current best view when a new diagnostic is worse.
