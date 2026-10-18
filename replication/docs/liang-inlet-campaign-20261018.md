# Liang-inlet campaign, 18 October 2026

Eleven replacement premixed cases were running at 21:31 Asia/Shanghai.
They cover phi=0.90–1.40 in 0.05 steps at 100 atm and 298 K. Each startup
check passed: 676 field bodies matched the upstream executable at 2 microseconds.
The full runs start fresh and target 1 ms; no flame speed is accepted.

The source is `b54a8bf3297036e37e6c95732d25b7f8ab94b620` on
`draft/premixed-inlet`. Archive SHA-256:
`d83b1e2dc6bb0efe4cbdc7e20e7c91e43c4e24062f800ec0217ba28e2fbd5507`.
The [job register](liang-inlet-jobs-20261018.json) records all 22 smoke/full jobs,
checks, scheduler states and resource limits. Total maximum reservation is
2156 core-hours, not measured consumption. Each full job uses four cores for
at most 48 hours. The owner authorized additional computation.

Inlets use approximate Liang black-curve values in Nguyen Figure 12:
0.0534, 0.0594, 0.0647, 0.0689, 0.0701, 0.0687, 0.0666, 0.0642,
0.0615, 0.0589 and 0.0564 m/s, in ascending phi order. The phi=0.90
value is a short extrapolation because the displayed curve starts near 0.920.
These are imposed guesses, not measured flame speeds.

The 2-mm domain has 4000 cells. Half contains unburned mixture and half contains
condition-specific ideal-gas HP equilibrium products. Cantera supplies seed
composition only. The solver retains the real-fluid library and upstream equations.
Controls are maxCo=0.1, maxDeltaT=1e-7 s and writeInterval=1e-5 s.

The old 0.10/0.20 m/s jobs 124780751 and 124780755 were cancelled at the owner's
request. Their checkpoints and interim comparisons remain available. Use the
[method comparison](flame-speed-definitions-20261018.md) to distinguish Nguyen's
OH displacement estimator, adapted DeepFlame tracking and Cantera FreeFlame.
Current OH and temperature-tracking estimates do not yet agree within a declared
tolerance. A completed job or imposed inlet value does not establish agreement.
