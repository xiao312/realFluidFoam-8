# Project writing and evidence

Write for the owner and the next contributor who must repeat the work.
State the decision or observed result first. Use plain verbs, consistent terms,
and units. Explain each important assumption near the result it affects.

Remove generic introductions, inflated adjectives, repeated slogans, and claims
without evidence. Use tables for comparisons. Do not create decorative headings
or replace a missing measurement with confident prose. Preserve technical identifiers.

Use these states consistently: planned, implemented, tested, accepted.
Only call a scientific result accepted after its declared comparison criteria pass
and the owner reviews it. A successful process exit proves only the stated check.

Each log entry records:

- Date, time, timezone, question, and reason for the change.
- Source SHA, image digest/hash, input hashes, and exact command.
- Scheduler job ID, resource limits, raw evidence location, and exit status.
- Measurements with units, comparison criteria, failures, and limitations.
- Interpretation, next action, and any decision that changes the baseline.

Keep failed attempts. Correct prior entries through dated amendments. Agree numerical
tolerances before accepting results. Never infer scientific accuracy from compilation.

## References reviewed on 2026-10-16

- [Computational laboratory notebook rules](https://doi.org/10.1371/journal.pcbi.1004385):
  dated records, code versions, and enough context to repeat analysis.
- [Reproducible computational research](https://doi.org/10.1371/journal.pcbi.1003285):
  preserve inputs and version custom scripts.
- [anti-slop-writing](https://github.com/adewale/anti-slop-writing/tree/00b0809cdd5335d54ae61ee1459d78c95db4c61b):
  concrete mechanisms, evidence, and clear relationships between sentences.
- [Impeccable](https://github.com/pbakaus/impeccable/tree/6af45ac9a5eb8792f033d3242f52e99812fd91fa):
  reviewed for hierarchy and restraint. Its main scope is interface design.

No global writing plugin installation is required by this project.

## Project record layout

Keep one current baseline at the top of the Lark record. Identify the solver source,
compiled build, case release and original input source separately: these revisions
need not be the same. Link immutable commits and the environment lock. A newer
documentation commit does not change a running job's identity.

Place the figure comparison register and side-by-side gallery before the dated
work log. Keep original crops, captions and attachments intact. Maintain one current
comparison per paper figure: replace previous simulation images and update their
job, mesh, sampled time and qualification notes in place. Do not add a duplicate
comparison section for each checkpoint. Preserve earlier results in dated PDF
attachments and versioned evidence records. This follows the owner's 17 October
2026 layout preference. A diagram is
implementation context, not a numerical result. Distinguish errors against current
reference data from errors against digitized paper curves.

Each figure must trace to plotting code and data hashes, then to the job and case
inputs, the executable/library hashes and build revision, and the source and
environment pins. A visually matching layout is not an acceptance criterion.

Historical entries remain dated evidence. Correct obsolete decisions through
explicit amendments; do not leave several competing descriptions of the current
baseline. Report monitoring with a timestamp, stage and measured progress, and
keep log health separate from steady-state or mesh convergence.
