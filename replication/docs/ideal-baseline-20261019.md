# Ideal-gas baseline, 19 October 2026

Our solver passed the ideal-family startup check. Eleven production cases are
submitted. Their flame speeds are not accepted or plotted as converged results.
The independent Cantera sweep agrees with Liang Fig.8(a), Case 1, within the
estimated image-reading uncertainty across the resolved phi=0.95–1.40 range.

At phi=1.10, Cantera gives 7.4670 cm/s versus about 7.46 cm/s from the paper
image. The largest difference over ten image points is 0.0162 cm/s, below the
declared ±0.03 cm/s reading uncertainty. This is a raster comparison, not an
error against an author-supplied numeric table. The phi=0.90 result lies outside
the resolved top-panel range and is excluded from that error statement.

## Inputs and methods

Both calculations use methane/air, 100 atm, 298 K, GRI30 and exact 21/79 molar
O2/N2 air. The adapter reads all 53 author NASA7 species and 325 reaction
parameters. Cantera retains its atomic weights, constants and bundled transport.
Liang's supplied main article does not state Tu numerically. Tu=298 K follows
Nguyen and remains a declared assumption for the Liang comparison.

Cantera 3.2.0 FreeFlame solves an adiabatic steady planar flame. It uses
mixture-averaged transport with molar gradients and no Soret. Five refinement
levels yield 1,122–1,202 points over 4 mm. The last speed changes are
0.208–0.288%. The inlet velocity is the solved burning velocity, not a user guess.
Domain and transport-database equivalence to modified PREMIX remain unqualified.

Our unchanged diagnostic executable uses idKineticMixture, perfectGas, janaf,
sutherlandKinetic and sensibleEnthalpy. Chemistry is idKineticStandard / ode /
SEULEX, absTol=1e-8, relTol=1e-6, with laminar combustion and integrated rates.
It retains the 4-mm, 8,000-cell, two-outlet setup. A central 0.2-mm ideal HP
products slab initializes each phi separately; velocity starts at zero.
maxCo=0.1, maxDeltaT=50 ns, target=0.2 ms. Eight MPI ranks per case.
This is a transient propagation calculation, distinct from Liang's steady BVP.
The comparison requires relaxed profiles and consistent front/source diagnostics.

## Runtime evidence and traceability

Smoke 124877695 completed in 2 min 38 s, exit 0. The log confirms the ideal
thermo and chemistry selections. All 1,360 common written field bodies are
identical with diagnostics enabled/disabled. Species-sum error is 8.39e-13.
The fresh density differs from pW/(RT) by 8.96e-7 relatively. Native Qdot is
finite. These checks establish startup health and diagnostic noninterference.

Case/runner source: `128d13ddb4e40c8a539053f22a90fb452738597e`.
Cantera analysis implementation: `9d863b6e4dee532558114e98bf56be267067169a`.
Plotting revision: dba2b1 (running-state labels updated).
Solver build 124870644, binary SHA-256
`e3ef56491e44c2dfdd79826805f992ed8220901643ac14554c38ca8e81e6b385`.
Library build 124657926 and the locked OF8 container remain unchanged.
The executable equations and original live real-fluid jobs were not modified.
The setup and analysis merged into the single `develop/reacting` branch.

| phi | Our solver job | Cantera speed (cm/s) |
|---|---|---|
| 0.90 | 124878341 | 5.7057 |
| 0.95 | 124878481 | 6.3824 |
| 1.00 | 124878268 | 6.9147 |
| 1.05 | 124878510 | 7.3302 |
| 1.10 | 124878193 | 7.4670 |
| 1.15 | 124878594 | 7.3435 |
| 1.20 | 124878305 | 7.1204 |
| 1.25 | 124878625 | 6.8737 |
| 1.30 | 124878627 | 6.6191 |
| 1.35 | 124878634 | 6.3659 |
| 1.40 | 124878676 | 6.1218 |

Each full job reserves at most 48 core-hours (8 cores × 6 hours). Eleven jobs
plus the startup reserve at most 532 core-hours. This is a reservation limit,
not measured consumption. No automatic continuation is scheduled.
An SSH submission session timed out after four successful submissions; the
ledger was inspected and only missing cases were submitted. No duplicate jobs.

## Known transport difference

At the unburned phi=1.10 state, our saved density and Cp differ from Cantera
by about 0.00109%. Our viscosity is 2.645% higher and conductivity is 6.553%
higher; OH mixture diffusivity is 0.191% lower. Units and raw values are in the
JSON record. Our Sutherland/Eucken-style mixture transport therefore is not
an exact substitute for Cantera/CHEMKIN transport. A CFD speed discrepancy
cannot immediately be attributed to the equations or the equation of state.

The future real-gas sequence must control this transport difference explicitly.
Selecting the existing SRK/Chung family changes more than the EoS alone.
First evaluate ideal-case propagation, numerical sensitivity and energy/species
flux consistency. Then isolate EoS, nonideal enthalpy, conductivity and diffusion.

## Comparison artifacts and checks

Local output `output/ideal-baseline-20261019-v3/` contains the original-panel
comparison, a direct paper-pixel overlay, PDF/SVG exports and digitized points.
Green circles on the overlay are Cantera results. No seed or startup CFD
diagnostic is substituted for a developed flame speed. The original paper is
kept locally; no downloaded PDF or paper image is committed to the public fork.

Two module tests passed: mechanism translation against grouped reference rates
at four temperatures, and all seed conditions/normalization. Shell syntax,
whitespace checks, mesh checks and scheduled on/off checks passed.
See [machine-readable evidence](ideal-baseline-20261019.json) for hashes,
refinement histories and the timestamped scheduler snapshot.
Reference method: [Cantera 3.2 one-dimensional flows](https://www.cantera.org/3.2/python/onedim.html).
Paper audit: [Liang 2019](liang-2019-premixed-audit.md).
