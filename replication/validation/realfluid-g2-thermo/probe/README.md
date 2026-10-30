# Runtime real-fluid thermodynamic probe

This module loads the actual registered `psiReactionThermo` implementation. It
adapts the established `replication/validation/properties/rfPropertyProbe.C`
pattern rather than implementing another cubic EOS or caloric model. It records
cold oxygen and methane density, Cp, Cv, sensible/absolute enthalpy, transport,
finite-difference dHs/dT and nontrivial enthalpy inversion. These are numerical
diagnostics; agreement with reference data and independent review are separate.

Inputs are a prepared `realfluid-g2-thermo/export.mjs` output directory (exact
thermophysicalProperties and manifest), an explicitly selected pure `O2` or
`CH4`, and a new output case. `node prepare.mjs --thermo-dir DIR --species O2`
prints the read-only plan; add `--out NEW_CASE` to write. The source adapter must
already contain explicit bounds covering the requested temperatures. Original
NASA bounds and extrapolated states remain in the input receipt. No coefficient
or bound is silently changed here. No secrets or network access are needed.

Build `realFluidG2ThermoProbe` using wmake and the complete matching fork library
stack in a Slurm allocation. Its Make/options follow the existing property
probe. The wrapper supplies the qualified GCC/multiarch flags and isolated
FOAM_USER_APPBIN/FOAM_USER_LIBBIN. Run blockMesh, then the probe with `-case`.
`cold-properties.csv` and `cold-inversion.csv` preserve actual library values.
The process exits nonzero for nonfinite/nonpositive properties or an inversion
error greater than 1e-5 K. That numerical threshold is not a paper-fit criterion.
The read-only Node plan and `node --check prepare.mjs` are local preparation
checks; real library loading/inversion require execution evidence.

The full fork registers PRchungTakaMixture/PengRobinson and
SRKchungTakaMixture/soaveRedlichKwong with rfJanaf. PR is not the volume-translated
PRVTA model in Müller. rfJanaf adds EOS enthalpy departure to NASA Ha and subtracts
the ideal NASA formation enthalpy at 298.15 K to form Hs. Its inversion clamps
temperatures to dictionary bounds; extending those bounds only enables explicit
polynomial extrapolation, not experimental validity below the original range.

For a fresh flow case, `realFluidG2ThermoProbe -case CASE -initialize-Ha` requires
time zero and a case-owned Ha field with deliberately selected boundary types.
It overwrites Ha values with the executing full-library Hs plus species formation
enthalpy. This is preparation from prescribed p/T/Y, not a CFD restart. It avoids
reusing ideal-gas Ha after changing EOS. Save its log and input/output hashes.
For an `inletOutlet` Ha patch it also initializes the stored backflow refValue;
ordinary field assignment alone would leave the generator's zero placeholder
there. Its prescribed reference p/T/Y is the initial patch state. This does not
invent a pressure-dependent inlet condition for a different mixed boundary.
After a successful write it creates `constant/fgmHaInitialization`, identifying
time zero and the actual thermoType dictionary. Cold G2 preparation enables the
solver's opt-in marker check. The admitting wrapper additionally checks hashes
of the initialized fields and complete runtime; the marker is not a scientific
qualification or a substitute for those immutable input receipts.
`ha-initialization-boundaries.csv` records actual area-weighted boundary p/T/rho
and Ha. Use its inlet densities to replace the generator's explicitly labelled
ideal-density placeholder estimates when discussing residence times.
Pressure-dependent fixed-T inlet enthalpy must also be kept consistent during
the subsequent flow solve; initial conversion alone does not qualify that
runtime boundary coupling. Its dependents are fresh cold-property diagnostics
and later real-fluid G2 initialization, not flamelet chemistry generation.

To qualify the fixed-temperature boundary helper itself, prepare a new case
with `--boundary fixed`, then run `realFluidG2ThermoProbe -case CASE
-boundary-pressure`. It perturbs pressure by 10%, compares the helper's Ha to
the independent full-field thermo evaluation, and requires a nonzero real-fluid
enthalpy departure change. A separate `--boundary bad-ha` case must fail with
the explicit incompatible-Ha error under the same command. The default
`--boundary gradient` preserves the ordinary property sweep. This probe includes
the solver-owned helper from the same frozen archive; it does not reimplement
its boundary update. These checks do not require CFD or evolved state reuse.
