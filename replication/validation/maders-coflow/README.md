# Maders reference extraction

Extract filled-square Detailed–Verhoeven reference markers from the four original
embedded raster panels in Maders2017 Figure4. This module does not compute flames,
fit physics or identify the overlapping hollow FGM markers as detailed data.
Inputs: four original PNG panels, separate output directory. Output: calibrated
numeric CSV/JSON, raw pixel centres, hashes, uncertainty and QA overlays.
Dependency: NumPy/Pillow in the local analysis environment; no network or secrets.
The physical CFD evaluator consumes these data; raw images stay outside Git.
Example: `python digitize.py --images PRIVATE_PANEL_DIR --out NEW_DIR --plan`.
Remove `--plan` to extract. Verify each QA overlay against original marker identity.
Some overlapping/cropped markers are omitted, never invented. No extrapolation.
The2pixel coordinate uncertainty is an extraction estimate, not experimental error.

`plot.py` renders Figure4 from digitized paper markers and actual sampled radial
profiles. It uses paper lines and our markers, original limits and four-panel
layout, with matched run time/source in its receipt. Metrics compare CFD values
at the original digitized coordinates; dense display interpolation never adds
metric weight. `--plan` inspects paths without writing. No CFD or scheduler work.
PCHIP is used only for the displayed paper line. Original numeric references and
failed/partial CFD values remain available. Matplotlib/NumPy are local dependencies.

`import-preview.mjs --site LOCAL_PREVIEW --catalog CENTRAL_JSON --comparison PLOT_DIR`
plans importing the actual comparison into the existing Maders4 target; `--apply`
updates local files only. Node built-ins; no network, credentials, scheduler or
publication. It verifies image hashes, preserves all other targets and original
captions, archives the previous payload, and regenerates content-addressed data/
bundle and manifests. Numerical/reviewer/human acceptance remain pending. Example:
`node import-preview.mjs --site preview --catalog catalog.json --comparison out`.
Verify plan first, then browser-load the exact target and inspect the retained
receipt and plotted sample time. This importer cannot approve or publish results.
When the JobID changes, the previous comparison remains available as a separate
view. Subsequent updates retain that prior-run view without adding duplicates.

`history.py --samples RADIAL_DIRECTORY --reference curves.json --out NEW_DIRECTORY`
computes per-time paper errors, peak positions and changes between saved profiles.
It writes raw JSON/CSV and time-history plots. Differences use actual saved-time
intervals; completion does not imply a steady solution. This local analysis needs
NumPy and Matplotlib. Inspect the latest paper-style plot and the temporal changes
together before judging agreement. No threshold or acceptance is inferred.

An optional measured `temporal_screen.provisionally_steady` flag labels profiles
as time-settled at measurement planes and retains the screen in the evidence
binding. It never grants numerical, reviewer or human scientific acceptance.

When several cases run concurrently, each JobID retains one latest comparison
and history view. Refreshing one case does not hide another case or the previous
completed baseline. An explicit `physical_outcome` (for example extinguished)
stays visible separately from scheduler state and temporal settling.
