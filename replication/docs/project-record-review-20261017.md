# Project record review, 17 October 2026

The [Lark project record](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf)
now leads with the active original-OF6-input counterflow run, its source/build/case
identity, the relevant algorithm differences, and the paper comparison status.
The original figure gallery precedes the dated historical work log. No new
scientific result was accepted during this editorial revision.

## Current run identity

| Component | Immutable identity |
| --- | --- |
| Fork and development branch | `xiao312/realFluidFoam-8`, `work/2022-replication` |
| Solver source | `48506de20ce67f35279c5347b09dcd86865a4c39`; no fork changes in `src/` or `applications/` |
| Qualified build | Job `124657926`, source `b1153ea9c64b9abf55f7be6c488549024c081279` |
| Active run | Job `124672685`, case/runner release `59b99e85dd6908fa6ecb89615885ba2eb4a3e936` |
| Case archive SHA-256 | `39d20d32f4efbcab2838b15b7a466d44b1ac17e3fabb09771f043c0c771fa2dc` |
| Original OF6 thermophysical-library input source | `61f86014ef3f4277d04a348c83777d6a20d24cf3` |
| Container image manifest | `sha256:b307565bb6a8f65be82caa9c552e708eb2888e5e35f90f0b620e6f48b8bfa507` |
| SIF SHA-256 | `7d4e96e0b1a97a0b361cbaf808b6242fa0c576e5ee2a27cd6a9a514c59cb529e` |

The [reset record](author-counterflow-reset-20261017.md) documents the original
11,200-cell case, compatibility edits, smoke failures and passed two-stage smoke
test. The [environment lock](../environment/lock.json) and
[build record](build-qualification-20261017.md) identify the runtime and products.
This documentation revision does not rebuild the solver or alter a running job.

## Monitoring

Read-only scheduler and solver-log samples on 17 October 2026, Asia/Shanghai:

| Timestamp | State and cores | One-step physical time | Maximum Courant number | Logged temperature range |
| --- | --- | --- | --- | --- |
| 17:43:07 | RUNNING, 8 | 0.001910 s | about 0.005535 | 300–2000.108 K |
| 17:45:46 | RUNNING, 8 | 0.002493 s | about 0.005418 | 300–2000.108 K |
| 17:49:58 | RUNNING, 8 | 0.003369 s | about 0.005333 | 300–2000.091 K |
| 17:52:21 | RUNNING, 8 | 0.003898 s | about 0.005290 | 300–2000.091 K |

At the final sample the job had run for 18 minutes 46 seconds. The sampled step's
final local continuity error was 6.00e-12 and global error 4.39e-13.
These samples show advancing time and bounded logged fields, not a steady flame.
The target is 0.13 s of one-step initialization followed by 0.07 s of GRI30 after
resetting time. GRI30 had not started. The 12-hour allocation does not guarantee
completion of both stages. No continuation or additional compute was submitted.

The shared ledger reserves 288.67 of the authorized 1,000 core-hours, including
unreclaimed reservations for failed/cancelled jobs. The current job reserves
96 core-hours (8 cores × 12 hours). Reservation is not measured consumption.

## Editorial changes and evidence limits

The earlier document buried the gallery below setup history and accumulated several
statements of what was “current.” Generic “Our result” labels also obscured the
difference between computed properties, old developing flames and missing results.
The revision puts the current decision and supporting identities first, labels all
27 figure panels by evidence type, and amends superseded campaign statements.

The active reacting executable uses the 2022-style flow sequence and a newer
temperature-inversion library. It does not test the modified pressure algorithm
in the separate 2025 `realFluidFoam` executable. The
[solver audit](solver-paper-audit-20261017.md),
[library audit](thermo-architecture-audit-20261017.md) and
[OF6 audit](of6-architecture-audit-20261017.md) supply source-level evidence.
Strict property inversion failures remain visible; the prose does not convert
startup checks or small property-curve errors into acceptance.

The gallery contains two computed property figures, four superseded counterflow
development figures, eight missing numerical comparisons, twelve diagrams and one
reference property map. The four counterflow figures still show the original
0.1 ms development outputs, not job `124672685`. Existing PDF atlases remain dated
snapshots; no PDF or plot was regenerated in this documentation-only revision.

Reviewed guidance:

- [anti-slop-writing, pinned revision](https://github.com/adewale/anti-slop-writing/tree/00b0809cdd5335d54ae61ee1459d78c95db4c61b):
  replace generic claims with named evidence and limits; remove repeated summaries;
  keep the relationship between observations and conclusions explicit.
- [Impeccable, pinned revision](https://github.com/pbakaus/impeccable/tree/6af45ac9a5eb8792f033d3242f52e99812fd91fa):
  reviewed its reading hierarchy, clarify and distill guidance. Its primary scope
  is interface design; no frontend tooling or global plugin was installed.
- The computational-notebook and reproducible-research practices already recorded
  in [writing.md](writing.md): dated amendments, immutable inputs and reproducible
  analysis provenance.

The bounded editorial review checked specificity, evidence fit, sentence relations
and repetition. The weakest area was competing historical status statements; these
now sit under a dated work-log heading and explicit superseded-campaign headings.
Future entries should maintain the top baseline rather than append another
undated “current status” section.

## Verification

Before/after full document snapshots and edit receipts are retained in the local
project state directory `state/doc-revision-20261017/`, outside Git. Verification
compares image and attachment token multisets and checks all 27 comparison grids.
This checks content preservation and structure, not browser-rendered typography.
The original figures and captions remain adjacent to the result or stated gap.

Verification passed for Lark revisions 78 to 120: all 62 image tokens, all four
attachment tokens, and all 27 comparison grids were preserved. All 27 result-side
labels were updated. The fetched document places the complete gallery before the
historical work log. `git diff --check` passed for the documentation changes.
