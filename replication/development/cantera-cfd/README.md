# Cantera transport experiment in OpenFOAM

This draft isolates conductivity and species diffusion in the ideal-gas 1D
flame. It supplies these coefficients from the qualified Cantera C bridge at
the current pressure, temperature and composition. The solver uses the same
current-state native species enthalpies as the energy-update experiment.
Chemistry integration, native thermodynamics, viscosity, equations, mesh and
PIMPLE placement remain the recorded baseline. No nonideal CFD is supported yet.

Inputs: pinned OF8/native libraries, a separately qualified bridge binary and
SDK, explicit bridge model inputs, and an original-zero fresh-start case.
`constant/canteraBridge` has `libraryPath` and `inputDirectory` (absolute paths),
`stage 1` and `options full`. Other stages/options fail until their energy and
chemistry coupling is implemented and qualified. Species order must match exactly.
Outputs: a separately named `rfCanteraTransportFoam`, binary/input hashes,
frozen-state parity report, original-zero verification, Qdot and tracking fields.

Dependencies: `cantera-bridge`, `flame-tracking`, `fresh-start`, the pinned native
library and OF8 container. This module does not change those sources or active
runs. Dependents: the ideal-flame transport comparison. No credentials are used.
Generated files and temporary state stay inside the selected project root;
source/build/model references are immutable read-only inputs. Each MPI rank owns
one bridge context. There is no network access from the solver.

The initial and end-step transport update follows the baseline property-update
placement. Boundary coefficients use each patch's current TPY. Cantera source
evaluation is skipped. Cp and mixture enthalpy remain native, so this experiment
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
