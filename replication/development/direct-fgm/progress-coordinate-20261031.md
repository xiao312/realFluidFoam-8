# Physical progress-coordinate diagnosis, 31 October 2026

The current extinction-trajectory FGM table does not reproduce the full-chemistry
relaxation at the state where the G2 pilot stopped. Reducing the CFD timestep or
clipping the progress variable would not resolve that discrepancy. The failed
table and every run remain retained; no result in this report is scientifically
accepted.

## Executed evidence

| Experiment | Slurm job | Outcome |
| --- | --- | --- |
| Fresh full-SRK source-root G2 pilot, 32 ranks | 126426676 | Failed at 0.837 microseconds when the source reached the table boundary; completed profiles through 0.592 microseconds are startup diagnostics. |
| Two independent full-species constant-pressure CVODE reactors | 126427683 | Completed, exit 0:0, 386 allocation seconds; both reached 2 ms. Actual chemistry integration took 4.96 seconds. |
| Two fresh enthalpy-preserving seeded flamelets | 126428728 | Completed, exit 0:0, 518 allocation seconds; both reached 200 microseconds. |

The G2 runtime uses source `f368f8bf894dceff3e9a781d108a3f6a133e8928`
with individually identified retained libraries. Its physical table SHA256 is
`a2ba27d3b8ae15085fead9480e0da4045f1415c1492cdfd9376d0d9ba700cf57`.
The independent reactors execute
`d69bad630d84ab66087f91dd94b2a3677bc94b7c`; the ignition experiment executes
`14193ad6e19fd092699fd357de3f8f03dbaea305`. All use the qualified OF8 environment
`f46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793`;
the chemistry drivers load pinned Cantera 3.2.0, and the flamelets additionally
use the retained cold-kinetics and energy-corrected Spitfire runtime.

## What the independent reactors show

Both reactors start afresh from actual table temperature/composition at
Z=0.286519345725 and 5.61 MPa. They evolve all GRI30 species and energy, rather
than the scalar table ODE. No saved CFD fields are continued.

| Quantity | Table-boundary initialization | CFD source-stage initialization |
| --- | ---: | ---: |
| Initial CO2+CO mass fraction | 0.558466118075 | 0.556906478719 |
| Maximum CO2+CO mass fraction | 0.558473764261 | 0.556911869804 |
| Time of maximum | 0.218129 ns | 0.204720 ns |
| Final CO2+CO mass fraction | 0.554054851671 | 0.554055230111 |
| Initial CO2+CO+H2O mass fraction | 0.937930006402 | 0.926294681266 |
| Final CO2+CO+H2O mass fraction | 0.958769394289 | 0.958771012762 |

The source-stage reactor reverses before reaching the original table's maximum.
The frozen table ODE instead reaches that maximum after about 26.1 ns. Its initial
source is physical at the initial state; its subsequent scalar closure fails to
follow the full chemistry. Chemical motion orthogonal to CO2+CO matters here.

Conservation checks pass without changing criteria: scaled enthalpy drift is
2.44e-14, elemental mass-fraction drift 2.33e-15, and no negative species occur.
The final states agree closely with separately calculated HP equilibrium. The
water-inclusive coordinate is nondecreasing within the declared 1e-9 tolerance
in these two reactors. This is evidence for a candidate coordinate, not proof of
a globally single-valued flamelet manifold.

## Fresh flamelet evidence and remaining limits

The compact ignition seed blends fresh HP products with unburnt mixture and
inverts temperature at the original mixed-stream enthalpy. It preserves pure
85 K oxygen and 288 K methane endpoints. Initialization enthalpy error is at most
0.005928 J/kg and elemental error 2.745e-16.

At stoichiometric scalar dissipation 10000/s, the fresh flamelet remains burning
at about 3569.53 K after 200 microseconds. At 100000/s the same seed quenches to
288 K. This exposes ignition and burning-branch dependence; it does not invalidate
the separately retained burning solution at the latter dissipation.

Adding water does not remove every reversal across mixture fraction. The
10000/s family still has substantial bidirectional excursions above 1e-5 at
ten mixture-fraction nodes. A compact seed also does not supply zero-to-burnt
coverage at every node. Neither trajectory is automatically installed as a CFD
table. A new approximate branch selection must retain omitted states, actual
chemical source values, coverage limits and independent lookup errors.

These chemistry tests use ideal-gas GRI30 with explicitly extrapolated NASA
polynomials above 3000 K. They are not full-SRK CFD histories. Sharma's Figures
1–2 instead use 60 bar and the Kong mechanism; that model difference remains.

## Reproduction and next diagnostics

The executable modules are [progress-reactor](../../fgm/progress-reactor/README.md)
and [ignition-family](../../fgm/ignition-family/README.md). The
[G2 comparison renderer](../../validation/g2-paper-review/README.md) binds actual
sample hashes, original figure assets, captions and runtime records. It reports
terminal failures prominently and does not turn startup samples into temporal
means. Exact duplicate MPI-boundary samples are retained raw and removed only
in a separately identified plotting derivation.

A separate fixed-chi steady-flamelet diagnostic is being qualified to advance
G2 flow and energy work while the finite-rate manifold is repaired. Its laminar
delta-PDF assumptions must remain distinct from the papers' LES/PDF treatment.
At this checkpoint it has source review but no completed physical qualification.
