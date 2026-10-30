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
