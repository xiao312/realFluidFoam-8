# Warm FGM coupling on the retained G2-related mesh

This module prepares a clean time-zero warm ideal-gas FGM diagnostic on the
registered `mascotte-legacy-wedge-200622` mesh. It tests the physical table and
absolute-enthalpy solver under injector advection and mixing. It does not claim
to reproduce cryogenic G2, turbulence, the exact paper geometry or steady flame
morphology. The retained mesh's oxygen inlet diameter differs from the paper;
its injector-exit axial origin also needs an explicit comparison transform.

Inputs: a hashed physical v2 table directory, its exact NASA7 phase metadata,
and the registered mesh directory containing manifest.json and polyMesh. The
generator verifies the registered manifest and every copied mesh file, measures
the actual inlet areas/radii, and records those values. Bulk mesh/fields stay
on SCNet. No credentials or network access are used.
The retained mesh is binary OF7: float64 points and compact int32 face offsets
and labels. The parser follows the existing qualified mesh-contract audit and
checks each block terminator/count; it does not assume ASCII mesh data.
Inlet area is the sum of actual face-vector magnitudes, matching OpenFOAM's
flow-rate boundary. The registered final oxygen face has a 5.25e-11 m axial CAD
offset; face tilt and aggregate plane error are recorded rather than silently
projecting its area onto x or requiring identical normals on very small faces.

`node prepare.mjs --table-dir TABLE --metadata PHASE --mesh-dir MESH`
prints the read-only plan. Add `--out NEW_CASE` to write. Optional `--bounds
clamp` explicitly permits counted lookup clipping for diagnostic exploration;
the default is strict `error`. Optional `--end-time SECONDS` defaults to 20 us.
`--ranks N` sets the matching decomposition (default 2); scheduler resources must
be admitted for that same count.
This is an early transient coupling run, not a steady result. Run inside a
FlamePilot Slurm admission; never start the solver on a login node.

Initial Z=0.2 and raw C at local eta=0.5 come from actual finite-rate data.
Every initial species, temperature and Ha uses that same state. Inlets use the
table's pure streams (must be >=200 K here). This uniform partly reacted initial
fill is an explicit ignition/starting condition, not evolved CFD. Full-annulus
mass flows are O2=0.0444 kg/s and CH4=0.1431 kg/s from Muller/Singla; each wedge
patch receives the corresponding measured-area fraction. The source's swapped
Sharma prose values are not used. Pressure is the table's registered pressure.

Dependencies: `fgm-of8/direct-verification` provides table loading and NASA
conversion; OF8 provides flowRateInletVelocity, mesh tools and the solver.
The module writes its own explicit schemes, including `div(phi,Ha)` and the
multivariate `div(phi,Yi_h)` scheme; it does not import historical case files.
The source and table identities must be frozen with the admission. Verification
starts with checkMesh, then measured field bounds, mass/energy budgets,
source/state consistency and clipping counts. Plot T/Z/C and selected species
at the written times with the warm/ideal/early-transient qualification visible.
Independent code/science review and human acceptance remain separate.

The admitting wrapper owns the actual scheduler/rank selection. Use `checkMesh`,
`decomposePar`, the admitted parallel
solver, and `reconstructPar` before running `node check.mjs CASE`. The checker
expects `log.solver`, emits `direct-g2-result.json`, and reports mechanical
completion separately from scientific acceptance. A normal exit and finite
fields do not qualify the warm approximation or an out-of-table clipped state.

Local syntax verification: `node --check prepare.mjs`, `node --check
mesh-input.mjs`, and `node --check check.mjs` must exit zero. The first real input
preparation must also execute the read-only plan against the exact physical table
and registered mesh. No synthetic table is permitted to stand in for that check.

Progression after the startup diagnostic: inspect actual CPU time, table bounds,
thermodynamic pressure departure and profile stability before selecting a fresh
0.1 ms run, then fresh longer runs spanning the 50 mm inlet-based convection
time and several chamber convection times printed in the input manifest. Every
stage initializes at time zero. OH and temperature axial/radial profiles are
sampled, but a uniform hot initial fill and a 20 us startup cannot establish a
flame length or the paper's time-averaged morphology. A smaller, separately
declared mesh may answer coupling questions if 200622 cells are too costly;
it must have its own geometry identity and cannot replace this registered asset
silently. Cryogenic real-fluid thermodynamics and a turbulence closure remain
separate required steps before a physical G2 comparison.

Longer morphology studies also require a separately defined localized ignition
recipe with fresh unburnt surroundings, rather than this uniform reacted fill.
That recipe must be supported by actual unburnt/mixing table states over the
required raw-C range. A narrow family of burning profiles alone may not cover
it; clipping a cold unburnt state onto a burning branch does not supply the
missing physics. This generator intentionally exposes that coverage limitation
rather than inventing an unregistered ignition state or reaction source.

Observation and scaling inputs for subsequent fresh runs are described in
`progression.md`. The optional `--observations FILE` and `--decomposition FILE`
JSON inputs are parsed by `observations.mjs`. Their exact contents and hashes
are recorded in the case manifest. Defaults preserve four full field writes,
while CSV profiles carry explicit column names. An optional time average uses
OF8's time-weighted fieldAverage; its actual Properties counters must accompany
any mean plot. No mean is enabled by default. The observation module generates
small case dictionaries only, uses no network or credentials, and does not
submit jobs. It depends on OF8 libsampling and libfieldFunctionObjects.

`node forecast.mjs CASE --durations 0.0001,0.001 --ranks 16,32` reads the actual
solver ClockTime/physical-time records and predicts fresh-run cost from the
last completed steps. Rank projections are explicitly ideal scaling bounds,
not measured speedups. It prints JSON and never changes a case. Check both
modules with `node --check`; run `node observations.test.mjs` for configuration,
time-average labelling and decomposition rejection checks. These parser checks
do not qualify the generated function objects or physical results: the next
admitted clean-start case must do that.

The optional read-only API `inspectMesh(MESH, { boundaryGeometry: true })`
also measures non-wedge patches' x/r extent and near-axial boundary-face planes.
It reuses the same hash-checked binary parser and emits compact geometry only.
It does not infer a paper coordinate origin from a patch name or presumed lip
position. The coordinator must interpret the measured injector surfaces against
the paper drawing before selecting a comparison transform.
The two azimuthal wedge planes are explicitly excluded because they contain
almost all boundary faces and do not identify the injector lip. Plane grouping
uses a Map keyed by 1e-8 m bins; there is no pairwise search among faces. Execute
this optional audit inside the next Slurm allocation with a 30-second timeout.
An unavailable geometry receipt does not block a labelled warm/cold diagnostic;
the paper-coordinate transform remains unresolved.
