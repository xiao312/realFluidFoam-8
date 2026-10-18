# Paper figure comparisons

For new comparisons, use [the manifest-driven suite](../../suite/README.md).
It reuses this module's field readers and curve extractors with explicit input
paths, measured panel coordinates and current run identities. The dated scripts
below remain historical entrypoints; do not treat their hardcoded jobs or status
strings as the current campaign. Their files are retained to reproduce old evidence.

`extract_inlet_profiles.py ROOT JOB...` reads stable saved 1-D development
checkpoints and emits JSON on stdout; it never writes remotely. It reconstructs
global ordering through cellProcAddressing, validates the declared uniform mesh,
hashes each source field, and omits the newest common time to avoid active writes.
Run over SSH stdin and save stdout under the local project state directory.
`plot_inlet_profiles.py PROJECT SNAPSHOT OUTPUT` produces diagnostic profiles,
fixed-OH-isoline displacement estimates, a Figure 12 comparison and a PDF.
These use the existing analysis dependencies. The paper has no corresponding
premixed spatial profiles; only its Figure 12 speed at phi=1.10 is compared.
The speed estimate is rho/rho_u times (U - dx_front/dt), on the rising OH edge.
It is a finite-time kinematic diagnostic, not an evaluation of the paper's
discrete chemical/diffusive source expression or a converged flame speed.
Verification checks addressing coverage, field finiteness, stable file hashes,
marker uniqueness, timestep sensitivity and PDF rendering. No solver is changed.
`temperature_speed.py SNAPSHOT OUTPUT_JSON` independently tracks the maximum
positive temperature gradient using a three-point subcell fit, actual saved
times and measured cold-stream velocity. It adapts DeepFlame's concept rather
than its hardcoded sampling interval. Compare its 50/100-us fits with the OH
estimate; do not assume agreement during thermal relaxation.

`collect_counterflow.py ROOT oxy-1:JOB oxy-200:JOB air-100:JOB` streams a tar.gz
of stable decomposed checkpoints, global mesh and source hashes to stdout without
remote writes. Preserve that archive locally. `plot_paper2022.py` also accepts
manifest case entries `{path, time, ranks}` for these decomposed snapshots and
an optional output directory, plus per-case `case_status` labels. Real mesh
edges are used in contours; only displayed streamlines are interpolated onto a
regular grid. A failed case's earlier smoke must be explicitly identified.
After rendering, run `counterflow_report.py PROJECT SNAPSHOT_DIR OUTPUT_DIR`
to compare the same fields with the existing temperature digitization, export
near-axis CSVs and create the five-page original/replication PDF. Inspect all
pages and check `data/summary.json` for sample times, radii and qualifications.

This module inventories all numbered figures in the two supplied papers and
renders comparable plots from verified results. It does not fabricate absent
LES statistics, steady flames, or burning velocities. Original figures and
digitized curves remain local review artifacts, outside the public repository.

Inputs: the owner-supplied 2022/2025 PDFs, archived property/pilot results, and
hash-verified NIST tables. Outputs: a local HTML/PDF atlas, original-figure crops,
PNG/SVG result plots, extracted vector reference curves and comparison metrics.
The atlas distinguishes quantitative property comparisons, non-converged startup
diagnostics, reference-only figures, and non-numerical diagrams.

Dependencies: the pinned analysis environment (numpy, matplotlib, PyMuPDF,
reportlab), the property module, and the flame pilot artifacts. No credentials
are consumed; no simulation is submitted by these plotting scripts. All output
and matplotlib caches stay inside the explicit project root. Lark is a downstream
record, not a dependency of the analysis.

Figure 6 of the 2022 paper has vector curves. Extract them using the inspected
axis ticks and dash patterns; retain separate clipped curve segments rather
than interpolating across the hidden Cp peak. Digitization is approximate and
does not recover the original tabulated data. Numerical comparison with those
curves must state that qualification.

The 2025 nitrogen probe uses a separate bounded property job, not an LES run.
NIST silently limits long queries to 601 points, so the reference fetch splits
the desired 901-state grid and verifies exact temperatures before merging.

Minimal workflow: run `fetch_nitrogen.py PROJECT_ROOT`, then `render_sources.py`
with the two PDFs and output directory; run the plotting and report scripts
against those same paths. Scripts describe positional arguments in their CLI
help or module entrypoint. Verify every original crop in a contact sheet, render
the final PDF, inspect representative pages, and verify all 27 figure IDs exist.
An unavailable result must remain explicitly unavailable in the final report.

## Reproduction commands

From this checkout, with PROJECT_ROOT pointing to its parent workspace:

```text
python -B replication/validation/figures/fetch_nitrogen.py PROJECT_ROOT
python -B replication/validation/figures/render_sources.py PROJECT_ROOT PDF_2022 PDF_2025
python -B replication/validation/figures/paper_curves.py PDF_2022 PROJECT_ROOT/output/figure-comparison-20261017/data
python -B replication/validation/figures/plot_properties.py PROJECT_ROOT
python -B replication/validation/figures/plot_flames.py PROJECT_ROOT
python -B replication/validation/figures/build_atlas.py PROJECT_ROOT
```

Install `requirements.txt` into a project-local uv environment. The result archives
must already be extracted into the documented state directories. These are fixed
2026-10-17 evidence scripts, not a generic data-discovery interface. The PDF-authoring
skill's operation marker, when applicable, is run before the final command.
Expected result: 27 source crops, six computed PNG/SVG plots, 28 PDF pages, and an
HTML entry for every figure. The PDF and HTML must state unavailable results.

The 1-atm methane density series is not numerically scored against the digitized
paper because the drawing scale cannot resolve it reliably. Use the independent
numerical NIST comparison for that series. Source data and report assets remain
private local artifacts; only small computed summaries belong in Git.

Original captions are cropped separately at 4x PDF resolution to preserve math
and symbols. `render_sources.py` requires exactly one matching figure-caption
start and handles the inspected multi-block 2022 Figure 12 caption explicitly.
The atlas displays source captions beneath the original images, opposite our
plots and qualifications. Inspect all 27 captions when source PDFs change.

## Paper-scale 2022 rendering

`plot_paper2022.py PROJECT_ROOT [CASE_MANIFEST]` renders Figures 8-11 at the
inspected source crop dimensions in PDF points, with Times-family typography,
paper panel placement, axial windows, colour conventions and limits. It defaults
to the archived startup runs; a JSON manifest can supply new case paths under
the project root and an explicit status label. Numerical status is always printed
inside the figure. Values outside paper axes are counted, not silently hidden;
the wider-range diagnostic plots remain available from `plot_flames.py`.
This renderer does not generate missing flame-speed results. A manifest can supply
`paper_curves`, a project-relative JSON produced by `counterflow_paper_curves.py`.

`plot_interim.py PROJECT_ROOT SNAPSHOT_ROOT OUTPUT_DIR` reads the saved 10/20 ms
processor fields for jobs 124672685, 124674723 and 124674728 using global cell
addressing and polyhedral mesh centroids. It creates a dated six-page PDF addendum
and PNG/SVG plots, preserving the earlier atlas. Counterflow Figures 8–11 are
explicitly one-step initialization, not GRI30 validation. OH is absent from that
mechanism and is omitted, never replaced by zero. Nonuniform axial mesh geometry
is retained in contours; streamlines are interpolated onto a regular display grid.
The premixed page uses the inspected phi=1.10, 10-microsecond CSV as a diagnostic
beside Figure 12; it does not fabricate a flame-speed curve. Inputs and source
figure crops remain private. Verify addressing coverage, finite fields, page
count, actual figure dimensions and rendered layout. This script uses the same
local analysis dependencies and requires no HPC executable or new allocation.
Each contour panel states its own time. Plot provenance records case paths,
times, cell counts and nearest-axis radii. The atlas reads this record to update
its counterflow captions and summary, avoiding stale one-microsecond descriptions
when a new case manifest is rendered. Such updates retain a developing-flow
qualification until temporal and grid convergence are separately established.

## Both published counterflow series

Run `python -B counterflow_paper_curves.py PDF OUTPUT_JSON` before rendering
Figures 9–11. The extractor checks the supplied PDF SHA-256, uses inspected
vector paths and separate axis calibrations, and records every path/group.
Expected result: 50 curves, two series for each of 25 published quantities.
OH values are stored as actual mass fractions; display scaling is applied once.
The plot manifest selects this JSON with `paper_curves`. Dash-dot denotes the
published benchmark, dashed denotes Nguyen, and solid denotes our saved fields.
Species colours identify species; other panels use black/red/blue by dataset.
Partial reference ranges remain partial, and no curve alignment is applied.
Figure 11 has three published species; no H2O reference is invented.

Verify both series against the original crops, including the separate viscosity
and conductivity axes. Render and inspect all five comparison PDF pages. These
are approximate digitizations, not original author tables. Quantitative summary
metrics still use Nguyen's temperature curve only. No dependency has changed.
