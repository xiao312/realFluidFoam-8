# MASCOTTE profile comparison inputs

This module prepares measured paper curves for the reacting-flow ladder. It
does not simulate a flame or assign acceptance. Inputs are the owner's original
PDF and explicitly identified CFD profiles; outputs stay outside Git.

`sharma_centerline.py --pdf PAPER --out FILE` extracts Figure 4b from the exact
Sharma preprint and digitizes its fine/finer-grid temperature curves. The image
is raster data, so the output retains pixel-scale reading uncertainty. It masks
the legend, keeps the red dashed-line gaps, and does not fit or smooth data.
PyMuPDF, Pillow and NumPy are required; no credentials or network are used.

Figure 4b is time-averaged centerline temperature, not a local temperature
maximum. The gray band marks the experimental flame-location region; it is not
an experimental temperature curve. CFD comparison must identify whether the
profile is instantaneous or time averaged, with sampling interval and duration.
A short axisymmetric diagnostic is not the paper's three-dimensional LES.

Verification uses the source hash, the original image, extracted curve overlay,
and axis bounds. Run the command on the fixed PDF, then inspect the written
overlay. The expected peak is around 1900 K at approximately 0.055 m. These
checks qualify extraction only, not scientific agreement.
