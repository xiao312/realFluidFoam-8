# Replication suite

Use this module to regenerate paper comparisons after a solver or library revision.
It joins the existing probes, flame cases, saved evidence and plotting tools.
It does not submit jobs, change live cases, merge solver drafts or declare scientific acceptance.

## Inputs and outputs

`catalog.json` lists the case families, preparation commands, reference figures and outstanding checks.
`campaign.example.json` describes a local evidence bundle. Copy it to an ignored `*.local.json` file.
Paths are relative to an explicit project root, except the two read-only source PDFs.
Each dataset records its source revision, build, scheduler jobs and scientific status separately.
Do not substitute the plotting revision for the revision that produced the data.
`source_revision` identifies the run/case release. `builds` identifies the compiled
library source, preserved build evidence hash, product hashes and runtime SIF hash.
`executable` distinguishes upstream and renamed development solvers. Premixed
snapshots also retain the actual development executable hash for each job.
Use a new isolated build identity when changing the library; do not reuse an old build label.

The runner validates inputs before writing. It creates a new output directory and refuses replacement.
It writes source hashes, numerical checks, extracted profiles, original crops, transparent data layers,
paper-frame overlays, standalone plots, a comparison gallery and a PDF review.
All 27 paper figures remain in the register. Missing simulations and diagrams remain explicit.
Raw PDFs, extracted paper curves, bulk fields and rendered images stay outside Git.

## Use

```sh
python -B replication/suite/run.py plan PROJECT campaign.local.json OUTPUT
python -B replication/suite/run.py render PROJECT campaign.local.json OUTPUT
python -B replication/suite/test_suite.py
```

Install the pinned `../validation/figures/requirements.txt` in a project-local environment first.
Use the existing environment lock and case modules in `catalog.json` for new computations.
After collecting stable checkpoints, replace the manifest's input paths and run identities.
Run `plan`, then `render`. No scheduler submission occurs in either command.

## Plot contract

`styles.json` records page coordinates in PDF points, axis calibrations and measured stroke sizes.
The original PDF supplies the exact figure frame, labels, fonts, ticks, annotations and reference data.
New data are mapped through physical axis limits; no fitted coordinate shifts or value scaling are allowed.
The renderer uses the original crop dimensions, without tight-layout or automatic bounding-box changes.
Transparent PNG/SVG layers contain computed data and an explicit in-image legend. Overlays retain the original published curves.
Standalone plots use the same panel geometry and physical size, with explicit computed-data labels.

Original legend labels describe original data only. Every computed image includes a separate
legend for our markers, lines or fields. The gallery also supplies run status.
Legend positions are recorded in PDF points in `styles.json`; measured legend bounds
are excluded from the original-frame pixel comparison, alongside data panels.
The renderer checks that each legend remains inside the unchanged figure canvas.
Counterflow additions use solid lines, keeping species colours. Property additions use open blue markers.
Figure 8 replaces only the field interiors, with the original axes and colour bars retained.
Streamlines are interpolated for display; temperature uses the actual nonuniform mesh edges.
The 2022 vector geometry is measured from drawing paths. The 2025 raster calibration has pixel uncertainty.
Temperature insets in Figures 9 and 10 retain the original reference only; no invented inset calibration is used.

## Boundaries and verification

Dependencies: pinned NumPy, Matplotlib, PyMuPDF, Pillow and ReportLab; existing property comparison,
OpenFOAM field reader and PDF curve extractors. No network or credentials are required.
Dependents: local review, later manual campaign execution and future regression automation.
The environment and solver modules do not depend on this analysis module.

Tests check affine calibration, output containment, missing/nonfinite data and variable-time flame tracking.
Rendering validates input hashes, figure dimensions, dataset coverage and explicit scientific status.
Review the generated contact sheet and PDF before publishing results.
Passing these checks establishes reproducible analysis, not convergence or agreement with the papers.

For Lark publication, replace the corresponding images in the existing inline
comparison section. Copy each figure's status and added-data key with it.
Publication remains manual; this runner does not create new document sections.
