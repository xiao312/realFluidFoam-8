# Cantera chemistry coupling qualification, 20 October 2026

The ideal-gas constant-pressure Cantera reactor now passes both independent
reactor checks and an original-zero, eight-rank OpenFOAM startup test. A full
phi=1.10, 100-atm flame was submitted as job **124950538**. Its 300-us target is
not yet a result. Nonideal CFD and steady flame-speed agreement remain unqualified.

## Code and binary identity

- CFD source: `2ead1ab4f4d0e45da05322b32abde16a9be8f6a1`, branch
  `draft/cantera-bridge`; release `releases/cfd-2ead1ab` under the project root.
- Solver build and successful smoke: **124950245**, executable
  `rfCanteraBridgeFoam`, SHA256
  `32c69ccbc8ea5efc2721be51368f620475be7c33623cd8a36ea9466b57e929c6`.
- C bridge build **124947872**; independent reactor qualification **124948146**.
  Submission verifies that the qualification receipt names the same library hash.
- Cantera SDK **124917358**, native realFluidFoam libraries **124657926**, pinned
  OF8 container `openfoam8-rootfs-7d4e96e0b1a9`.
- Full flame **124950538** uses this qualified solver and freshly generated
  original time-zero fields. It does not continue the smoke or a previous flame.

The optional `adiabaticCP` mode integrates each cell from its current TPY for
one CFD step, using Cantera's ideal-gas constant-pressure reactor and CVODE.
It supplies rho_start times the mass-fraction increment divided by deltaT.
Native formation heats convert these sources to Qdot for the sensible-enthalpy
equation. The reactor's final temperature is not assigned to the CFD field.
Native chemistry is not also advanced. This changes the reactor closure as well
as the integrator; it is not an isolated SEULEX-versus-CVODE comparison.

## What passed

The independent Python Cantera reference uses seven flame temperatures and
three integration durations, including 50 ns and 5 us. The C ABI tests check
species and temperature agreement, elemental and enthalpy conservation,
reverse call order, and recovery after an invalid duration. Ideal and smooth-SRK
reactor checks pass, but only the ideal model is enabled in CFD.

The 100-ns CFD smoke has 8000 cells over 4 mm and eight MPI ranks. It reaches
the requested endpoint from time zero with maximum species-sum error
1.2207e-12, temperature 298--2230.0371 K, and finite pressure, density and species.
Its endpoint receipt explicitly retains `scientific_acceptance: false`.

The native-chemistry control **124948805** reproduces every saved field payload
of the earlier qualified transport smoke **124942088** exactly at 100 ns across
all eight ranks. Headers containing path provenance were excluded. A separate
control **124947365** took 29 minutes versus approximately four minutes for the
other builds; the slowdown was not reproduced and its cause is unresolved.

At the last smoke step, rank 3 spent 2.405 s in CP chemistry, 1.277 s in the
energy update, 0.438 s in diffusion-pair corrections, and 0.227 s in property
updates. These are rank-local timings, not aggregate CPU cost or a long-run ETA.

## Failed tests and fixes

All failed jobs remain excluded from comparisons and retain their logs.

| Job | Failure | Resolution |
| --- | --- | --- |
| 124947372 | Pure-species formation check also invoked a mixture diffusion check | Evaluate composition-independent ideal enthalpies at a mixed state |
| 124948225 | OF8 species API has `Wi(i)`, not `W(i)` | Use the OF8 interface |
| 124948808 | Small molar enthalpy discrepancy at startup | Compare NASA h/R; record each library's gas constant |
| 124949326 | Species source had the wrong OpenFOAM matrix sign; T rose to 3000 K and species sums failed | Use native `fvMatrix += sourceField` assembly; fresh rerun 124950245 passed |

OpenFOAM's matrix source stores the negative of volume times an added explicit
field. Its laminar model uses the same addition operation. Directly writing
positive V*RR into a matrix subsequently placed on the equation RHS reverses
the intended chemistry contribution. See the
[OF8 laminar model](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/combustionModels/laminar/laminar.C)
and [matrix implementation](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/fvMatrices/fvMatrix/fvMatrix.C).

## Remaining coupling limits

Legacy species molecular weights differ from Cantera by up to 5.007e-5 relative;
OF8's gas constant is 8.9583e-7 higher. Startup verifies the underlying NASA
polynomials and records the mass-basis discrepancy instead of modifying inputs.
The frozen-state audit bounds the equivalent energy defect at 0.000102 K per
50-ns integration among the sampled states, not throughout every future flame.
The CFD equation still uses native Cp and mixture enthalpy. Cantera supplies
conductivity, mixture diffusion and, in the new mode, chemistry integration.
Long-time front tracking, Qdot, time-step sensitivity and comparison with the
steady ideal FreeFlame curve are still required.
