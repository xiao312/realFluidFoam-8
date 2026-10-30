# From current table diagnostics to paper G2 profiles

The next useful CFD evidence is time-resolved cold mixing and reacting profiles
on the retained mesh. The paper's long averaging windows are later comparison
requirements, not prerequisites for running those diagnostics.

## Current scientific inputs

The cold table was generated from a fresh physical Spitfire trajectory at
5.61 MPa with O2 at 85 K and CH4 at 288 K. Its published artifact identity is
`a2ba27d3b8ae15085fead9480e0da4045f1415c1492cdfd9376d0d9ba700cf57`
for `physical.tbl`; the receipt says `table_built_not_accepted`. The explicit
post-peak extinction branch and numerical zero-tail projection remain part of
that table's definition. The held-out data include branch/coverage refusals;
this is not an arbitrary-progress full-manifold qualification. The warm table
is a separate control, not an allowed substitute for cold G2 inlet conditions.

The table transports raw `C = Y_CO2 + Y_CO`. Its lookup coordinate is a locally
mapped table coordinate, not automatically Sharma's equilibrium-normalized
progress variable. Fixed-Z source integration can remove the explicit stiff
source timestep, but cannot establish pressure/enthalpy/transport conservation
in CFD. Those checks remain attached to the actual solver run.

The retained wedge has 200622 cells, a 3.2 mm oxygen opening and a 0.2 m chamber.
It is a development mesh. Cavalieri's injector is a diverging 3.6-to-5.0 mm
oxygen duct, with methane annulus diameters 5.6 and 10.0 mm. A mesh source label
does not qualify those geometries as equal. The current mesh injector origin
also needs a geometric receipt before the paper's axial stations are compared.

## Preliminary physical time scales

Actual full-SRK purestream property probes at 5.61 MPa give oxygen density
1181.226802270157 kg/m3 at 85 K and methane density 41.75775004549758 kg/m3 at
288 K. Their CSV SHA256 identities are respectively
`c2d327eaa64f7bccb4feb469040561b653cd12cd2c5c49aa4a2e5f4b178c5d07` and
`92dd40808cb6b92566f339c26210fcd5b0896ae1234509783472e82804656513`.
These are measured property-probe values, not a completed G2 boundary receipt.

Using the actual wedge area fraction 0.01387126727713, areas
1.1155935404174525e-7 m2 (oxygen) and 7.477962844114543e-7 m2 (methane), and
full-annulus mass flows 0.0444 and 0.1431 kg/s, `U = mdot * fraction / (rho*A)`
gives the following inferred inlet scales:

| Quantity | Oxygen | Methane |
| --- | ---: | ---: |
| Inlet speed | 4.67369 m/s | 63.56754 m/s |
| Travel over 15 mm | 3.209 ms | 0.236 ms |
| Travel over 50 mm | 10.698 ms | 0.787 ms |
| Travel over 70 mm | 14.977 ms | 1.101 ms |
| Travel over 200 mm | 42.793 ms | 3.146 ms |

These are inlet-velocity estimates, not a measured mixed-flow residence time.
Thermal expansion, entrainment and recirculation change actual residence. The
paper quotes different oxygen velocities because its injector geometry differs.

After the short coupling checks, practical original-zero-time runs are:

1. **0.1 ms:** transport/source coupling, boundary fluxes and energy budgets;
   retain snapshots and point histories. This is startup evidence.
2. **1 ms:** preliminary methane/shear-layer development and first comparative
   profiles. Dense oxygen has moved only about 4.7 mm at its inlet speed, so the
   downstream paper flame structure cannot be called established.
3. **5–15 ms:** a useful first oxygen-core, radial-temperature and flame-opening
   assessment over the paper's 15–70 mm stations. Judge progress by actual fluxes,
   station histories and initial-fill removal, not end time alone. Inspect
   running original-zero-time jobs at intermediate times without restarting from
   an evolved CFD state.
4. **Statistical comparison:** only after the flow is developed, accumulate
   clearly defined means and RMS. Schmitt used Reynolds statistics for 50 ms
   after one convective time based on oxygen speed and flame length. Cavalieri
   accumulated 60 ms after flushing the initialization. A 3D LES claim also
   requires geometry, turbulence, mesh and sampling convergence evidence.

This sequence is not a wall-clock promise. Its feasibility depends on the actual
stable timestep and measured throughput after source integration qualification.

## Reusable next comparisons

`cavalieri2025-fig-6` is the immediate quantitative profile target: six panels
with radial mean/RMS temperature at x = 15, 45 and 70 mm. All eighteen original
PDF paths are extracted. M3 is the primary numerical reference; M1/M2 show the
paper's own sensitivity. An instantaneous curve can be displayed early, with its
time stated, without calling it the mean or inventing RMS. The paper contains
resolved/filtered temperature statistics; do not silently substitute a new
density-weighted temporal average.

`schmitt2020-fig-21` adds centerline normalized velocity, mean oxygen and oxygen
RMS. Its G2 flame-length definition is mean Y_O2 below 0.1, around 12 oxygen
diameters. This is distinct from an OH maximum or an optical flame end. The
original raster is ready; overlapped G2 oxygen mean/RMS curves still need careful
digitization before numerical scoring.

`singla2005-fig4cd-g2-ohstar` and `sharma2023-fig-9` add anchoring, opening and
dense-core morphology. The former averages 200 exposures of 30 microseconds;
the latter reports ensemble OH sampling every 0.1 ms without specifying a total
duration in the Figure 9 discussion. Ground-state OH mass fraction, line-of-sight
excited OH* emission and Abel-transformed emission are different quantities.
Until an emission/measurement model is provided, compare them as explicitly
labelled morphology views with no concentration or color-error score. Schmitt
also warns that line-of-sight integration, absorption/re-emission and dense-jet
effects affect optical comparisons (PDF page 21).

The source contracts and original captions are in `targets.json`. They reuse
the existing fixed catalogue IDs; no duplicate targets or new acceptance labels
are introduced.
