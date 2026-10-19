# Reacting solver development

`develop/reacting` is the sole integration branch for our reacting solver.
Start independent `draft/<experiment>` branches from an explicit integration SHA;
use worktrees under the project workspace for concurrent edits.
`work/2022-replication` and its jobs retain the upstream replication baseline.
Upstream `master` is not a second solver-development integration line.

This module owns experiment identities, promotion rules and our named solver.
It does not silently change upstream source or original author inputs.
Inputs: immutable solver/case revisions, qualified library products, environment
lock and benchmark configuration. Outputs: isolated builds, input manifests,
scheduler records and comparison evidence. No secrets in tracked configuration.
Dependencies: Git, OF8, realFluidFoam libraries, Slurm and the environment runner.
Dependents: the 1-D and 2-D benchmark comparisons.

Each draft records its question, parent integration SHA, solver/library/case
revisions, build/job IDs, product hashes, environment digest, input hashes,
controls, allocated core-hours, baseline, measurements and unresolved limits.
Branch/executable names alone never identify a numerical result. Use independent
build/job directories so multiple draft versions can run without replacing files.

Keep case redesign, library corrections and coupling-loop changes separate.
First test the inlet–outlet case with unchanged equations. Temperature inversion,
restart consistency, species-enthalpy cache refresh and chemistry robustness need
separate subsequent drafts. PIMPLE changes must state their equations and placement.

## Promotion to the integration branch

1. Verify the build, dependency links and immutable product/input hashes.
2. Check finite fields, species normalization and mass/element/energy balances.
3. Compare against the baseline on identical cases, including serial/MPI and
   restart checks where the change can affect them.
4. Evaluate mesh/time/domain sensitivity and relevant property/flame regressions.
5. Merge a reviewed cohesive draft with its evidence into `develop/reacting`.
   Incomplete/rejected drafts remain labelled; startup success is not acceptance.

As of 19 October 2026, central ignition is the owner-selected primary premixed
replication experiment; the inlet–outlet case remains a comparison adaptation.
See `premixed-paper/README.md` for the isolated draft and in-situ Eq.(40) checks.
Do not tune physical
models solely to fit a curve. The fork's source remains the authority for code;
the Lark document records current decisions and comparisons.

Example: `git switch -c draft/premixed-inlet develop/reacting`.
Verification: `git diff --check`, module-specific checks and scheduled smoke
evidence. Expected result is a traceable draft, not implied scientific acceptance.

`python3 status.py ROOT` is a read-only monitor. It reads the development ledger,
queries Slurm and emits JSON with pinned sources, limits, binary hashes and
available test receipts. Dependencies: Python 3.8+ and sacct; no credentials or
filesystem writes. Missing ledger fails with its path. Verify against recorded
job IDs and keep each snapshot timestamp; a RUNNING state is not convergence.

