# Fresh seeded diffusion-flamelet experiment

This module runs two independent physical trajectories at chi_st=1e4 and 1e5/s
to explore burning states missing from the single extreme-extinction table.
It does not replace that table, integrate CFD, change a progress definition in
the solver, claim steady convergence, or publish/accept results.

Job 126428092 reached the initial-state evaluator but stopped before integration
because the enthalpy-error reduction used Python `abs` on a list. The correction
uses NumPy's array-aware absolute value and retains the same 0.01 J/kg criterion.
Failure receipts now bind a complete traceback. This repair changes neither the
seeded physical state nor the reused chemistry runtime; a new allocated physical
run remains necessary.

The pinned cold Cantera/Spitfire runtime is reused without a rebuild. The model
is an ideal-gas, adiabatic, constant-pressure, unity-Lewis diffusion flamelet in
mixture-fraction space, with variable Cp and enthalpy-flux terms. It is not an
x-space counterflow calculation. Inlets are pure O2 at 85 K and CH4 at 288 K,
5.61 MPa. Existing low-temperature extrapolation qualifications remain explicit.

## Initialization and inputs

Inputs: the existing `../direct-flamelet/cold.json`, exact mechanism/source and
runtime qualification identities, both upstream patch receipts, and `settings.json`.
`--chi` selects exactly 10000 or 100000/s. Default `--plan` loads no scientific
runtime or writes. Execution requires a new output directory.

For each Z, unburnt Y and total enthalpy are the inlet mass-weighted mixtures.
A fresh HP equilibrium calculation supplies product Y only where the seed is
nonzero. The seed fraction is `0.9*(1+cos(pi*(Z-Zst)/0.06))/2` within a compact
half-width 0.06, and zero outside. Blend unburnt/product species, then solve HP
for temperature at the original mixed enthalpy. No arbitrary temperature pulse,
external ignition energy, or prior evolved state is imposed. Endpoints remain
the exact pure inlet states. Species/element sums, HP residuals, actual initial
temperatures, and finite Cantera/Griffon source evaluations are retained before
integration. A failed initialization is preserved and cannot start a trajectory.

The numerical experiment uses 129 clustered Z points, 0.2 ms physical duration,
first dt=1e-10 s, max dt=2e-6 s, temporal tolerance1e-8 and nonlinear tolerance1e-10.
Each independent trajectory has a 300 s integration wall allowance and 8000-step
ceiling; checkpoints are written every 25 accepted steps or 10 wall seconds.
A ceiling/exception is not success: retain actual reached time and partial data.
The wrapper runs the second case even if the first fails and records both exits.

## Outputs and analysis

Raw time/T/Y trajectories and checkpoints remain immutable. Exported profiles
reuse the direct-flamelet physical exporter and preserve species production
rates. Frame selection combines physical-time samples and changes in both
`CO2+CO` and `CO2+CO+H2O`; it is not tuned to paper agreement. Diagnostics include
element/enthalpy/clipping behavior, temperature history, both progress histories
and sources, chemical versus diffusive progress evolution, and branch direction
changes. H2O-added progress is an analysis candidate, not the Sharma coordinate.
Steady numerical convergence is not a prerequisite to retain an actual physical
trajectory, but incomplete integrations remain visibly partial. No automatic
table construction or source extrapolation occurs.

## Dependencies and boundaries

Depends on `direct-flamelet` common input/identity/export/clipping helpers, pinned
Cantera3.2.0 and Sandia Spitfire735711dc with the existing energy/cold patches.
The exact shared-object and qualification receipt are checked by the allocated
wrapper. Dependents are later physical table analysis and G2 development review.
There are no credentials or network calls. Outputs stay in the chosen fresh
directory; compute must run through the FlamePilot Slurm adapter, never a login
node. The prepared adapter request does not submit itself.

```sh
python run.py --config ../direct-flamelet/cold.json --settings settings.json \
  --chi 10000 --plan
# Allocated execution additionally supplies mechanism, source, environment,
# upstream patch receipts, and --out NEW_DIRECTORY, as in direct-flamelet.
```

Verification: syntax and configuration plan locally; actual HP/element/finite-rate
initialization checks and physical transient in Slurm. Inspect reached time and
raw/checkpoint receipts, not just process exit. The initial experiment contains
no broad synthetic test suite. Source and packet are exact Git archives with LF
and SHA256 receipts; no Windows checkout files become untracked runtime inputs.
