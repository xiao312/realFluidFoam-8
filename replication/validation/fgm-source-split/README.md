# Fixed-state source splitting qualification

This module owns qualification of the optional `strangFixedState` coupling.
It does not change tables, fit paper curves or submit jobs. The source default
remains `explicit`. Inputs are an exact physical v2 table, matching thermodynamic
metadata, the new combustion library/solver, and clean time-zero cases.
Outputs are source-stage events, field histories and comparison receipts outside
Git. No secrets or external services enter the scientific code.

Dependencies are OF8, the fork's FGM reader and the source kernel copied from
direct-flamelet commit `c67dfe2910dc2275270d3dccc2a5f3fedb75862a`.
Consumers are the 0D/1D source/energy checks and later bounded G2 diagnostics.
Use the existing direct-verification case generator and actual table inputs.

Minimal solver selection in `system/controlDict`:

```text
fgmEnergyForm absoluteEnthalpy;
fgmProgressSourceEnabled yes;
fgmSourceIntegration strangFixedState;
```

Use `ddtSchemes { default Euler; }`, fixed 25 ns or 50 ns timesteps initially,
and explicit fresh output directories. The mode refuses local time stepping.
The usual source table is generated from ideal-gas flamelets; matching its Z/C
does not establish thermal or kinetic consistency with a PR/SRK CFD state.

Generate a read-only plan with:

```sh
node replication/validation/fgm-source-split/prepare.mjs --table-dir TABLE_DIR --metadata PHASE_JSON --kind 0d --delta-t 2.5e-8 --outer 2
```

Add `--out NEW_CASE` to create fresh inputs. `--kind 1d` creates an 80-cell periodic
profile over 0.1 mm at 10 m/s. Both cases use actual table states at Z=0.2;
the 1D eta profile is `0.5+0.03*sin(2*pi*x/L)`. These inputs replace the base
generator's synthetic receipt. `--integration explicit` supplies the comparison
path. The default duration is 500 ns; boundary events can require a shorter
explicit duration. Missing coverage remains a failed qualification, not permission
to clip progress or alter source values.

Local preparation checks are `node --check prepare.mjs` and the read-only plan.
Allocated verification builds the updated library and solver, then runs `wmake`
in this module for `fgmSourceStepProbe TABLE Z RHO C DT`. Add `expect-event` only
when testing a preselected outward event. An unexpected event returns failure.

## Allocated verification sequence

1. Compile the unchanged scalar prototype and compare actual-table curves with
   the retained DOP853 reference, including outward-boundary event behavior.
2. Compile `source-step-probe.C` against the new FGM library. It compares the
   OF8 reader with the scalar kernel and repeats a fixed-state transport step
   with 1, 2 and 3 outer iterations. Original input arrays must remain unchanged.
3. Run a fresh closed 0D actual-table case at 25 ns and 50 ns. Record C, Ha, T,
   density and the source-stage logs; compare with the fixed-state reference
   only while its fixed-density assumption applies. Otherwise report coupling
   differences explicitly.
4. Run a periodic 1D advecting actual-table profile at the same timesteps and
   1/2/3 outer correctors. Compare progress profiles, integral Ha and mass against
   the finer timestep. Retain Euler/upwind transport error separately from the
   source integrator error. Do not infer order two from the splitting name.
5. Repeat the legacy explicit check without the new option. Its source path
   must remain unchanged. Outward events must fail, not become clipped passes.

CFD outputs must establish source nonaccumulation and energy behavior. The
fixed-state probe checks immutable input arrays but cannot alone verify OF8's
lazy oldTime handling; `fgmSourceOldTime` runtime records cover that boundary.
No numerical criterion or failed paper comparison is relaxed by this candidate.

## Batch checks and predeclared limits

`node check.mjs CASE SOLVER_LOG` writes `source-split-result.json`, per-time
field CSV and energy histories. Its limits are fixed in the input receipt before
execution: mass drift 1e-7 relative; closed total energy drift divided by the
actual formation-energy change 1%; assembled energy residual 1e-6 relative;
absolute-energy table-Q contribution <=1e-20 W; oldTime changes exactly zero;
no lookup clipping. A nonzero source must change the progress variable. Missing
fields, end time, source stages or audit records fail. The conserved closed-box
energy is integral(rho*Ha + rho*K - p), not integral(rho*Ha).

`node compare.mjs OUTPUT CASE...` requires the twelve split cases (0D/1D,
25/50 ns, 1/2/3 outers). Before execution, the comparison targets are 2% of the
local C span RMS for timestep refinement and 1% for outer-count sensitivity.
These are bounded diagnostic gates, not a paper-agreement criterion. Runtime
and numerical failures are retained even if another case passes. The identity
transport probe separately requires <=1e-10 C-span outer nonaccumulation; CFD
outer results need not be bit-identical because pressure and density are coupled.
An optional explicit baseline is reported separately and cannot qualify splitting.

For the allocated cold-table/ideal-thermo diagnostic, explicitly supply
`--nasa-extrapolation 200,6000`. NASA coefficients and transition temperatures
remain unchanged. Every species' original/effective bounds are retained;
no extrapolation is silently enabled by the generator. The full282 run requires
literal executing h(p,T,Y)-versus-stored-h closure <=1e-8 at every correction,
scaled by max(1, |h|, |h(p,T,Y)|, |Cp*T|), and no JANAF range warnings.

`--initial-eta 0.95` prepares a bounded hot-state control. The batch separately
replaces its declared extended dictionary with an original-range dictionary,
preserving both hashes and requiring the runtime caloric audit to reject the
known 3000 K clipping defect. This deliberately invalid input is not a successful
physical run. Main comparison cases retain initial eta=0.5.

## Independent uniform reference

`python reference.py --table physical.tbl --case-result CASE/source-split-result.json`
is a read-only plan. Add `--out NEW_REPORT.json` to compare a completed uniform
0D case with adaptive SciPy DOP853 at two tolerances. Dependencies are Python
3.11+, NumPy and SciPy; no Cantera runtime or C++ exact-step kernel is used.
The fixed density is the actual time-zero CFD mass/volume, and the source is
independently read from the hash-bound physical table. The reference reports
density drift and spatial nonuniformity, and requires its own refinement to
agree within 1e-7 of the local C span before numerical-reference confidence.
No CFD or scientific pass is granted by this extra diagnostic. Boundary events
terminate integration; linear endpoint continuation only locates events in
rejected RK stages. Accepted states must remain covered, with no clipping.
