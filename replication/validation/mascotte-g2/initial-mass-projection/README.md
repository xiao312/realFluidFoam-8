# Original-zero mass-flux projection

This experimental helper creates a density-weighted potential-flow initial
velocity and face mass flux. It tests startup compatibility; it does not produce
a developed flow, solve chemistry, change geometry or repair an EOS branch gap.
No scientific validation follows from successful projection.

Inputs: an undecomposed original-zero direct-FGM case initialized through the
executing EOS, a qualified runtime and the helper executable. The Node CLI
defaults to a read-only plan. Apply requires Slurm, a fresh `/workspace/cases`
case and no prior projection/phi. Outputs: changed `0/U`, new `0/phi`, log and
JSON receipts. All other initial fields and constant/system inputs are hash
checked unchanged. No secrets or scheduler authority enter this module.

The helper holds executing EOS density fixed and solves
`div(rho grad(Phi)) = div(phi_initial)` with zero normal correction on walls and
inlets, zero Phi at the outlet and preserved geometric constraints.
The corrected face flux is authoritative for solver startup; reconstructed U
need not reproduce it by interpolation. Report that discrepancy and kinetic
energy change. No thermodynamic fields, composition or time advance.
Relative cell-divergence L1 and net boundary flow must each be <=1e-8 of inward
mass flow before writing. This is a projection check, not a flame criterion.
Projected high velocities still need physical examination.

Dependencies: OF8 finiteVolume/meshTools, qualified real-fluid factory and
matching headers/libraries, Node.js. Dependents: explicit G2 startup experiments.
No job submission or pressure-model selection belongs here.

```sh
node initialize.mjs /workspace/cases/NEW_CASE /workspace/build/NEW/bin/initialMassProjection
# After reviewing the plan, within its admitted allocation:
node initialize.mjs /workspace/cases/NEW_CASE /workspace/build/NEW/bin/initialMassProjection --apply
```

Build `wmake` in `probe/` with `LIB_rfFoam8_SRC`, `FOAM_USER_LIBBIN` and
`FOAM_USER_APPBIN` bound to matching products. Verification: Node syntax,
compile/link/ldd identity, fresh uniform-flow and reviewed-mesh physical controls,
unchanged-field hashes and measured divergence/boundary flow. Decomposed/evolved
cases and repeated application must fail. Syntax tests alone do not qualify it.

The algorithm uses the correction/reconstruction pattern in official
[OF8 potentialFoam](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/applications/solvers/basic/potentialFoam/potentialFoam.C)
with density weighting. Solver `compressibleCreatePhi.H` reads saved phi.
