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
