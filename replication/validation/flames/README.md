# Laminar flame cases

This module reconstructs the 2022 counterflow and premixed cases using the pinned
GRI30 input and the compiled solver. It does not treat a coarse pilot as a paper
comparison. Inputs are the validation input directory and an explicit case
configuration; outputs are fresh case directories under a job's project root.
No secrets or network access are required. It depends on the property stage and
the environment runner; subsequent convergence studies depend on its pilot costs.

Counterflow specifications from the 2022 paper:

| Case | Inlets | Domain radius / length | Velocity constraint |
| --- | --- | --- | --- |
| 1 atm oxy-fuel | CH4 300 K; O2/CO2 21/79 mol% 1000 K | 20 / 20 mm | strain 100/s, equal momentum flux |
| 200 atm oxy-fuel | same | 5 / 5 mm | strain 100/s, equal momentum flux |
| 100 atm air | CH4 and air 300 K | 20 / 20 mm | methane 1 m/s; matched mass flow |

The last case uses case 6 of Juanos and Sirignano (2017), section 6, rather
than the oxy-fuel strain constraint. Source: https://sirignano.eng.uci.edu/theme/pdfs/39.pdf
(SHA256 8104c6f00cb5b610b9ac9776cc4484be5baad39212a027dcd9a68440f8582a31).
The published comparison differs in diffusion formulation and dimension.

All cases use SRK/rfJanaf/chungTaka, GRI30, `ode` with `seulex`.
ODE tolerances 1e-8 absolute and 1e-6 relative are project settings to be checked
for sensitivity. Do not inherit EulerImplicit from the author's tutorial.
Obtain inlet densities from the actual library before setting velocities.
For equal momentum, Uo/Uf = sqrt(rhof/rhoo) and Uf+Uo = a*L/2.
For matched mass flow, Uo/Uf = rhof/rhoo (equal inlet areas).

The premixed case uses 100 atm, 298 K and phi 0.90–1.40 in steps of 0.05.
The paper specifies 0.5 micrometre cells, central ignition and waveTransmissive
pressure at both ends. Domain length, initial kernel and OH surface choice are
reconstructed inputs requiring sensitivity checks. Report density-weighted OH
displacement speed, not raw laboratory front velocity.

Verification must include mesh checks, selected chemistry model from runtime logs,
finite bounded fields, mass-fraction sums, temporal convergence and mesh sensitivity.
Store failed runs. The first pilot measures cost and stability only; paper meshes
and converged reference comparisons follow after that evidence is available.

Minimal pilot example (after loading the isolated OF8 build environment):

```sh
python3 -B generate_counterflow.py ../inputs CASE oxy-1
blockMesh -case CASE
checkMesh -case CASE
rfPropertyProbe -case CASE -initial
python3 -B finalize_inlets.py CASE
realFluidReactingFoam -case CASE
```

Expected setup: 320 cells, 100 timesteps of 1e-8 s, inlet velocity constraints
recorded in `pilot.json`. Initial composition is a 50/50 mass blend of the two
streams at 1800 K, an explicitly reconstructed ignition state. This short run
cannot establish a steady flame. `oxy-200` and `air-100` select the other cases.
The generator refuses an existing output and verifies the pinned coefficient
hashes. It writes zero inlet speeds until `finalize_inlets.py` consumes densities
from `rfPropertyProbe -initial`; do not run the solver before finalization.

`summarize.py CASE` reads the final ASCII scalar fields and records finite positive
T/p/rho, species bounds and the 1e-8 mass-fraction sum criterion in
`pilot-summary.json`. It returns 3 for a failed numerical check. This is not a
steady-state or mesh-convergence test, nor an integrated mass conservation balance.
