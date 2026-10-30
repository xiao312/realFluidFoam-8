# Requested instantaneous sample interface

This document is an interface request, not a modification to the shared G2
generator. The existing `g2-review` consumer and its observation contract remain
unchanged. A future producer revision should add `rho` to the same instantaneous
sets and plane that already sample `T` and `OH`, at the same simulation times and
coordinates. Record that producer revision and its exact sampling dictionary.

The consumer needs:

| Column | Meaning | Units |
| --- | --- | --- |
| x,y,z | Mesh-coordinate sample position | m |
| T | Instantaneous local temperature | K |
| rho | Instantaneous executing EOS density | kg/m3 |
| OH | Instantaneous ground-state OH mass fraction | kg/kg |

Use the actual written density at the same pressure/temperature/composition state;
do not reconstruct it from an ideal-gas EOS. Split field CSV files are supported
only if the producer preserves identical positions and ordering. Missing fluid
points remain absent; no interpolation or mirroring is part of this consumer.
The original mesh x-origin is retained. A renderer must declare a separate paper
origin mapping rather than changing raw sample coordinates.

Save the phase metadata and source/job/environment identities beside the manifest.
The metadata must contain OH molecular weight in kg/kmol. Sampling a plane or
profile does not itself prove complete radial coverage for LOS integration.

For time averaging, retain instantaneous triples at every declared sampling time.
This module first transforms each triple and then integrates the sampled proxy.
If a future in-situ accumulator avoids retaining all snapshots, it must accumulate
the transformed population with physical timestep weights and export its window,
counts and gaps. Existing TMean/OHMean/rhoMean cannot reconstruct that result.

No change to solver dynamics, boundary conditions, tables or averaging acceptance
is requested by this interface.
