# Paper figure comparisons

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
