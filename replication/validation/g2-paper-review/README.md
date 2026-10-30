# Preliminary G2 paper comparison

This offline renderer places actual sampled G2 fields beside the retained
Cavalieri Figure 6, Sharma Figure 4b/9 and Singla Figure 4(c,d) targets. It owns
presentation and provenance only. It does not run CFD, infer missing fields,
award acceptance, publish, or turn startup snapshots into LES statistics.

## Inputs and outputs

`--case` is a retained case snapshot with `direct-g2-input.json` and named sampled
CSVs. `--targets` is the hash-checked output of `../mascotte-review/prepare.py`.
`--sharma-reference` and `--sharma-pdf` are the pinned Figure 4b inputs.
`--run-record` identifies the job, executing products, case source and mesh.
`--x-origin-m` is mandatory: our plotted x is mesh x minus this value. For the
paper-exit companion it is zero; for the audited canonical legacy mesh it is
0.010 m. `--origin-note` must identify the evidence, not an assumed alignment.
Repeated `--time` selects actual saved times; the default selects the latest.
Default execution prints a read-only plan. `--apply` creates a new output directory.

Outputs are PNG/SVG plots, the original figures and captions, consumed CSVs,
an HTML review, and a receipt with input/source/output hashes. Missing RMS,
averages or fields are reported. No replacement zeros or interpolation across
missing grid cells are generated. Cavalieri's 60 ms temporal means remain
distinct from our instantaneous profiles. The 15/45/70 mm panels are produced
only when those exact transformed stations were sampled. Sharma's gray band
marks flame position, not a measured temperature curve.

Optional `--phase-metadata` runs the unchanged `../oh-lte-proxy/run.mjs` on
co-located instantaneous plane T/rho/OH. It uses Mueller Eq. 18 at 308 nm and
the phase's OH molecular weight. The result is an LTE population proxy, not
line-of-sight emission or calibrated OH*. No formula is applied to averaged
fields and no axial reflection, Abel inversion or radial integration is made.
Ground-state OH maps and LTE population maps are separately labelled.

## Boundaries and dependencies

Python, NumPy, Matplotlib and PyMuPDF are required. Node is needed only for the
optional LTE calculation. This module imports the named-sample reader and axial
plotter from `g2-review`; it consumes `mascotte-review`'s pinned extraction and
calls the `oh-lte-proxy` CLI. The solver and scheduler do not depend on it. There
are no network calls, credentials, remote writes, or publishing operations.
All paper images and raw data stay outside Git. A supplied runtime record is
declared operator evidence, not an independently authenticated scheduler query.

```sh
python replication/validation/g2-paper-review/review.py \
  --case /results/pilot --targets /references/g2-targets \
  --sharma-reference /references/sharma-fig4b.json --sharma-pdf /papers/sharma.pdf \
  --run-record /results/pilot-runtime.json --x-origin-m 0 \
  --origin-note 'Qualified paper-exit companion: x=0 at its co-planar exit' \
  --phase-metadata /results/phase-metadata.json --out /review/pilot --apply
```

Verification is a read-only plan followed by a render from retained actual
samples, inspection of every image, and comparison of receipt hashes. No
physical correctness is inferred from parser tests. A modified retained paper
asset must fail before output creation. Source modules are also syntax checked.

The first 100 microseconds are a numerical/startup diagnostic. Inlet speed
estimates imply about 6.4 mm methane and 0.19 mm oxygen convection in that time;
these are not developed downstream profiles. A longer transient, mesh/time
sensitivity and a justified averaging interval remain necessary for M4/M5.

If parallel sampling repeats exact processor-boundary coordinates, run
`normalize.py --case RAW --run-record RUN.json --out NEW_DERIVATION` first.
Its default is a read-only plan; `--apply` preserves all raw hashes and writes a
separate derived snapshot. Only rows identical in every named numeric field at
exactly identical coordinates can be deduplicated. Conflicting values fail;
there is no tolerance, averaging or interpolation. The first row/order is
retained. Use the derived `case/` and `run-record.json` for rendering. The shared
reader remains strict, and the derivation receipt exposes every removed row.
