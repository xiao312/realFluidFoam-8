# Three in-situ speed measures, 19 October 2026

All eleven ideal-gas conditions, phi=0.90–1.40 in increments of 0.05, now run
the qualified `rfTrackedReactingFoam` executable. The
[job and evidence record](flame-tracking-20261019.json) identifies every
replacement and donor. Original donors were cancelled only after every
replacement copied hashed inputs and advanced its own checkpoint.

Source **02de163e8e97a2e761d36e60c59e50e7942a4d07**, build **124883260**:
manufactured sign/weight/window checks passed; 1,360 common field bodies were
identical to both the previous executable and the tracking-disabled replay.
This merge changes diagnostics only. The three measures are:

1. Fixed temperature contour, using the corresponding saved Cantera anchor.
2. Fixed OH mass-fraction contour, primary threshold 2e-5.
3. Timestep-averaged source plus diffusion used in the OH species equation.

Both front trackers use a trailing 5-microsecond position fit and the local
gas velocity/density with fresh-gas density. They report both fronts and fixed
secondary contours. Invalid/multiple crossings reset the fit. The executable
does not recalculate the discarded instantaneous source estimate.

At the **14:56 Asia/Shanghai snapshot**, all eleven jobs are RUNNING. Ten have
completed their first tracking window, at about 53–66 microseconds physical
time. Phi=0.90 is advancing much more slowly, at about 40.95 microseconds and
still warming its tracker. All target 200 microseconds with maxCo=0.1 and a
50 ns maximum step; a target time does not itself establish convergence.

At phi=1.10 and 65.92 microseconds, left-front temperature tracking gives
6.436 cm/s and OH tracking 6.310 cm/s; the steady Cantera reference is
7.467 cm/s. The source measure remains a cross-check with visible step-scale
variation. These are transient estimates, not accepted steady flame speeds.

The existing Lark history image is replaced in place with all three measures,
their legend, both fronts and the steady ideal-gas reference. Property-model
development does not change these running ideal-gas inputs or libraries.
