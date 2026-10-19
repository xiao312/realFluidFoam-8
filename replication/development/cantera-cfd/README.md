# Cantera transport experiment in OpenFOAM

This draft isolates conductivity and species diffusion in the ideal-gas 1D
flame. It supplies these coefficients from the qualified Cantera C bridge at
the current pressure, temperature and composition. The solver uses the same
current-state native species enthalpies as the energy-update experiment.
In default mode, chemistry integration, native thermodynamics, viscosity, equations, mesh and
PIMPLE placement remain the recorded baseline. No nonideal CFD is supported yet.

Inputs: pinned OF8/native libraries, a separately qualified bridge binary and
SDK, explicit bridge model inputs, and an original-zero fresh-start case.
`constant/canteraBridge` has `libraryPath` and `inputDirectory` (absolute paths),
`stage 1` and `options full`. Other stages/options fail until their energy and
chemistry coupling is implemented and qualified. Species order must match exactly.
Outputs: a separately named `rfCanteraBridgeFoam`, binary/input hashes,
frozen-state parity report, original-zero verification, Qdot and tracking fields.

Dependencies: `cantera-bridge`, `flame-tracking`, `fresh-start`, the pinned native
library and OF8 container. This module does not change those sources or active
runs. Dependents: the ideal-flame transport comparison. No credentials are used.
Generated files and temporary state stay inside the selected project root;
source/build/model references are immutable read-only inputs. Each MPI rank owns
one bridge context. There is no network access from the solver. Earlier immutable
transport-only builds retain their `rfCanteraTransportFoam` executable name.

The initial and end-step transport update follows the baseline property-update
placement. Boundary coefficients use each patch's current TPY. Transport queries
skip source evaluation. Cp and mixture enthalpy remain native, so this experiment
is not a complete Cantera thermodynamics replacement. Absolute Cantera species
enthalpies are never inserted into the native sensible-enthalpy equation.

Example: `python3 instrument.py plan RELEASE NEW_SOLVER`, then `apply` for an
isolated build tree. `submit.sh plan ROOT RELEASE BRIDGE_JOB KEY` performs
read-only discovery; `apply` submits compilation and a fresh-zero smoke test.
Full flames require the successful qualification receipt and are generated anew.

Verification: `git diff --check`, Python compilation, Bash syntax, pinned binary
hash checks, a one-core bridge parity check, and a scheduled eight-rank smoke
case. Check finite T/Y, original start time zero, source values and transport
coefficient parity. Passing startup does not establish steady flame speed.

An optional `chemistryMode adiabaticCP` adds the independently qualified Cantera
constant-pressure reactor. The default `native` preserves the transport-only
experiment. The CP mode is a separate physical closure, not solely a switch from
SEULEX to CVODE. For each cell and PIMPLE iteration, the supplied current TPY
starts an independent integration of duration deltaT. Integrated species sources
are `rho_start*(Y_final-Y_start)/deltaT` in kg/(m3 s). The sensible-enthalpy source
is `Qdot=-sum(Hf_native*RR)` in W/m3, matching the native energy convention.
The reactor's final T is diagnostic only; the CFD energy equation updates T.
Pressure/transport/PIMPLE and thermodynamic property updates retain their placement.

Only stage1/full is permitted. Molar formation enthalpies must match the bridge
reference values before the first integration. Legacy native molecular weights
differ from Cantera by at most 5.007e-5 relative; startup checks a 6e-5 ceiling
and prints the measured maximum. Native mass-specific formation heats are used
in Qdot. Frozen-state conversion predicts at most 0.000102 K equivalent energy
defect per 50-ns step (0.01149 K over 5 us); this is a known coupling limit, not
exact mass-basis parity. No species weights or initial fields are silently changed.
The source diagnostic reads the
actual selected source; native chemistry is not also advanced. Existing
transport-only runs continue using their immutable source and binaries.
`chemistryRtol` and `chemistryAtol` are explicit required controls for CP mode;
their units differ from native concentration-based ODE tolerances. A separate
CP smoke must pass before a fresh full flame is submitted.

CP example: `submit.sh plan ROOT RELEASE BRIDGE_JOB phi110 build none adiabaticCP
REACTOR_QUALIFICATION_JOB`. The reactor receipt must name the same library hash.
The runtime configuration records mode and tolerances; a full run requires a
smoke receipt with the same chemistry mode. No reactor checkpoint is reused.

`runtimeProfiling true` writes rank-local `cantera-runtime.csv` with wall seconds
per step for chemistry, diffusion-pair corrections, linear solves, flow equations
and property updates. This read-only observer uses the standard C++ clock and
does not change solver fields. Smoke tests enable it; compare all ranks because
rank-zero time alone cannot establish load balance or CPU cost.
