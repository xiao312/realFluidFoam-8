# Liang Figure 8(a): ideal-gas comparison

The owner limited Cantera calculations to the ideal-gas curve on 19 October
2026. The other four curves remain original Liang results. No real-gas Cantera
calculations or changes to the active OpenFOAM cases are part of this update.

The comparison copies the original panel and caption from the supplied PDF.
Both panels retain the original 204 x 175 pt dimensions and source graphics.
The right panel adds computed ideal-gas values as green open circles joined
by a dashed line. A separate legend identifies the new data. The black, red
and blue curves are explicitly identified as paper results. The connecting
segments are visual guides, not additional solved operating points.

The published overlay uses the completed 11-point Cantera sweep from phi=0.90
to 1.40, in steps of 0.05; ten points fall inside the source panel. Conditions
are 100 atm, 298 K, author GRI30 reaction/NASA7 inputs, Cantera species transport,
mixture-averaged diffusion and no Soret effect. At phi=1.10 the speed is
7.4670 cm/s. The existing raster digitization gives a maximum difference of
0.0162 cm/s across ten resolved Case-1 points, below its estimated image-reading
uncertainty of 0.03 cm/s. The last mesh refinement changed speeds by
0.208–0.288%. This is agreement with a paper image, not a mesh-independent
accuracy bound. Liang's main PDF does not state a numeric unburnt temperature;
298 K remains an explicit assumption.

An additional ideal-only sweep is running locally: phi=0.92–1.44 at 0.02
spacing plus the existing 0.05-spaced points, 32 conditions in total. It uses
two refinement levels, slope/curve 0.0075/0.0125 and 0.00375/0.00625. Completed
conditions are saved incrementally. These partial results are not mixed into
the published 11-point curve. No Cases 2–5 Cantera jobs were launched.

The [artifact manifest](liang-panel-a-20261019.json) records the source PDF,
plotter and numerical data hashes, every plotted value and output hashes.
Existing mechanism and CFD identities remain in the
[ideal baseline record](ideal-baseline-20261019.md). A plotting revision does
not change a running case's source or binary.

Reproduce with the module's read-only plan, then apply, supplying the local
paper and completed `cantera-fine/results.json` to
`replication/development/liang-panel-a/plot.py`. Source PDFs and rendered
figures remain local artifacts; they are not committed to the public fork.

Verification: Python compilation and `git diff --check` passed. The PDF was
rendered and visually checked for identical panel dimensions, intact original
caption, aligned overlay, readable data legend and no clipped text. The first
render attempt failed its text-box fit check before creating a PDF; the final
layout passed. Numerical values are unchanged from the prior completed sweep.
The existing Lark comparison images and PDF are replaced in place.
