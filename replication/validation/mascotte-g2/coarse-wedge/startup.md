# Fresh coarse startup choices and linear solver control

The first proposed coarse reacting diagnostic uses the explicit
`initialization-rich-covered.json` and `--transport-tolerance 1e-8`. These are
development settings for a fresh original time-zero case, not a claim about the
paper's initialization or a relaxation of physical acceptance. Do not edit or
continue an existing CFD case to select them.

## Actual transport baseline

The retained r8 source-disabled run used solver source
`d1b753347794fe419c7231469597e45c6ed055c0`. Its transport log SHA256 is
`7f28d69dc77fbf539caffa231606f2aef204267a265ff83bb0fc3559ecc38cc0`
(39299 bytes). At t=1.19904076739e-9 s, the second outer iteration ended with
Z residual 4.66075764422307e-9 and Ha residual 7.71866399817195e-9, both after
1000 iterations. At t=2.63616444974e-9 s these were 2.07728905148342e-9 and
3.87358069976219e-9, again after 1000 iterations. Clock times were 128, 181 and
233 seconds after the first three timesteps. The baseline was cancelled by the
operator after collecting this timing evidence; it did not reach reacting CFD.

Those observations establish repeated iteration-limit exits above the requested
1e-10 tolerance. They do not distinguish finite-precision residual conditioning
from genuinely slow convergence without an iteration history or a better
conditioned solve. Setting 1e-8 is therefore a testable development choice, not
a proven numerical repair. The case generator defaults to 1e-10 and accepts an
explicit finite value in [1e-12,1e-6] for U/h/Ha/Z/c/Yi only. Pressure remains
1e-9, rho remains 1e-10 and every relative tolerance remains zero.

For the first short coarse run, record actual iterations and achieved residuals
alongside mass, total-energy/enthalpy budgets, pressure, T/Z/C/species bounds and
source integration events. Compare a second fresh start at a tighter transport
tolerance (e.g. 1e-9), with all other settings fixed. Compare profiles and
integrated budgets at identical times. Retain any iteration ceiling or failed
conservation check; normal termination is not physical acceptance. Only after
that bounded check should the longer millisecond companion be interpreted.

## Actual cold-table states

These values come from the existing loader's lookup of the frozen physical table
`a2ba27d3b8ae15085fead9480e0da4045f1415c1492cdfd9376d0d9ba700cf57`.
The exact phase metadata is
`8bd5a769976354b5d59ea4589c2ec7dc4c1e7584255e4e1127d5b33e3c4c303e`.
No new flame solve, equilibrium calculation, coefficient fit or clipping was
used to select these states. Eta is this table's mapped progress coordinate,
not an assertion of Sharma's equilibrium normalization.

| Initial fill | Z | Eta | T, K | Raw C | Sc, kg/m3/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cold Cmin baseline | 0.2 | 0 | 159.5807 | 0 | 1.41e-26 |
| Rich covered candidate | 0.6 | 0.9 | 1289.5596 | 0.4635669 | 5623.9253 |
| Hot source-control candidate | 0.2 | 0.8 | 2964.7550 | 0.3601870 | 22208606.4079 |

The rich fill has CH4/O2/CO/CO2/H2/H2O mass fractions approximately
0.35407/0.002591/0.358253/0.105314/0.046727/0.130708. It supplies a hot,
partly reacted, table-covered chamber inventory while retaining some reactive
oxygen; it is not a claimed equilibrium state. Its progress source is about
3950 times smaller than the hotter comparison state. This reduces initial
progress stiffness without selecting a state to fit a paper curve. It still
requires the actual source integration, thermo inversion and conservation checks.

For scale only, NASA/ideal density estimates are 7.7040 and 5.1485 kg/m3 for
the rich and hotter states. With coarse volume 5.44723392173e-6 m3 and total
wedge inlet flow 0.00260086261446 kg/s, their estimated initial mass/throughflow
times are 16.14 and 10.78 ms. These are not full-SRK results or measured residence
times. The executing full EOS must initialize and report actual Ha, density,
mass and boundary velocities before those estimates are used operationally.

By contrast, the r8 full-SRK cold fill actually had mass 0.00283454353114 kg,
volume 5.43778817924e-6 m3 and mean T=159.580736948 K: density 521.2677 kg/m3.
Its initial mass divided by total inlet mass flow is about **1.08985 seconds**.
Thus a cold Cmin fill is useful for the source-disabled transport test but is
an inefficient chamber inventory for a millisecond reacting startup. No choice
here changes the actual cold O2/CH4 inlet temperatures, flow rates or pressure.

The hotter `initialization-hot-source-control.json` is retained as a separate
fresh-start sensitivity case after source integration qualifies. Compare its
late profiles with the rich-fill case rather than treating either early hot
inventory as an established physical flame. Both initializations are uniform
covered states; neither imports an evolved CFD field or makes a localized
ignition/morphology claim.

## What the papers actually specify

- Cavalieri 2025, PDF page 8, states that the initialization is flushed and the
  flow developed before collecting 60 ms statistics. The inspected text does
  not specify either of the proposed uniform hot table states.
- Schmitt 2020, PDF page 13, requires one convective time based on oxygen inlet
  speed and flame length before 50 ms Reynolds statistics. It does not establish
  this diagnostic's uniform hot-fill recipe.
- Muller 2015, PDF page 9, starts averaging after the region is considered
  developed, then averages for 0.01 s. Sharma's manuscript page 17 calls for
  initial-condition-independent flow-through evolution in its multi-element
  discussion; that statement is not an exact G2 initialization prescription.

These statements support discarding startup before statistical comparison, not
inventing an author initialization. The two proposed fills are explicitly our
development controls, and original cold-start transport evidence is preserved.
