# Discrete mass and energy accounting

This read-only module audits actual G2 solver logs and per-step boundary phi.
It separates assembled equation residuals from the final PIMPLE state change.
It introduces no acceptance threshold, interpolation, new solve or case edit.
Missing flux/timestep records remain missing; a partial integral is never
reported as complete conservation.

The supported formulation is fixed-mesh Euler time integration with absolute
enthalpy FGM. `energyState.H` records H=integral(rho*Ha), kinetic energy K,
PV=integral(p), chemical enthalpy and E=H+K-PV. `EEqn.H` records each outer
iteration before thermo correction and subsequent pressure corrections;
`reactingFoamSolveZ.C` records the final state after those updates. The audit
uses the last energyEquation at each completed time, retaining all outer rows.
Actual adjacent state times determine dt, including variable time steps.

For a static mesh, OpenFOAM's [Euler implementation](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/finiteVolume/ddtSchemes/EulerDdtScheme/EulerDdtScheme.C)
uses current-minus-old conservative fields divided by the current dt. Its
[density equation](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/src/finiteVolume/cfdTools/compressible/rhoEqn.H)
couples that derivative to div(phi) and any fvOptions source. Consequently the
mass audit uses the right-endpoint sum dt*sum(boundary phi), not a trapezoid.
The final EOS rho replacement can differ from the density solve. Unlogged mass
sources and omitted patches must remain explicit interpretation limits.

Let D,C,L,G,P,Q be logged ddtW, convectionW, diffusionW, kineticW, pressureW,
sourceW. Signs follow the assembled equation, so outward transport is positive
and heating Q is subtracted. At a step of duration dt:

```
estimated kinetic boundary power = G - delta(K)/dt
final-state energy defect = delta(E) + dt*(C + L + estimated kinetic power - Q)
assembled term sum = D + C + L + G + P - Q
enthalpy coupling difference = delta(H) - dt*D
pressure coupling difference = -delta(PV) - dt*P
final defect = dt*assembled term sum + enthalpy difference + pressure difference
```

The reconstructed kinetic flux includes any difference between the final K and
the K used in the explicit energy term. It is an estimate, not an independently
sampled kinetic boundary flux. The module therefore exposes this limitation and
does not claim to isolate the kinetic PIMPLE contribution. The difference
between the assembled term sum and residualW also exposes unlogged fvOptions
or accounting contributions. The stored residual remains separate from both.

Results include each step, cumulative signed/absolute defects, largest
transients, throughput scales and a sensible-energy inventory scale
abs(H-Hchemical)+abs(K)+abs(PV). Zero denominators give null ratios, not a chosen
floor. Large formation-energy offsets are not the sole normalizing scale.
Mass diagnostics retain individual patch contributions. Each final state is
bound by log order to its single intervening `Time = ...` marker, and phi must
match that exact numeric timeName. This handles the observed 12-digit timeName
versus 15-digit energyState output without nearest-neighbor matching. dt still
comes from the actual energyState times; no printed-time rounding is integrated.

Inputs are a JSON manifest following `input.example.json`. Source files,
solver log, case dictionaries, optional execution receipt and every supplied
flux file are hash-checked; source commit and executable identity are recorded.
The code checks the known operator and state conventions against supplied
source. The supplied execution receipt remains evidence, not a parser-inferred
proof that arbitrary executable bytes came from that commit. Hash mismatches
fail before output. Files are read locally or in an admitted allocation; no
network or secret handling exists in the module.

`node audit.mjs INPUT.json` prints the report without writing. Add
`--out NEW_DIR` to save report.json and per-step CSV; an existing directory is
refused. The source of the auditor itself is hashed into the report. Dependencies
are Node built-ins only; later figure/report renderers may consume its JSON.
It does not change `direct-fgm` generators or scheduler adapters.

Verification: `node --test audit.test.mjs` checks an independently constructed
open control-volume conservation history with variable dt and a missing-time
negative case; both tests should pass. The actual frozen r8 log was also audited;
see [the measured result](observation-20261031.md). Synthetic identities do not
constitute physical validation.
