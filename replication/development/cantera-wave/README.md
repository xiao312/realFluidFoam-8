# Cantera-profile travelling-wave initialization

This diagnostic creates original time-zero CFD fields from a screened, ideal-gas
Cantera flame profile. It places two opposed planar fronts in the existing
4-mm, 8000-cell domain, with their half-temperature contours 0.1 mm from the
centre. It tests whether CFD preserves a known flame structure. It does not
replace the paper's hot-ignition reconstruction or establish steady flame speed.

Inputs: a supported equivalence-ratio key, Cantera `profile.csv`, its result
record in the frozen Figure 8(a) JSON, a new case path, velocity recipe, and an
endpoint in microseconds. Only screened Case 1, 100-atm, 298-K profiles are
accepted. Profile bytes must match the recorded SHA256. Outputs are the original
zero fields and a manifest identifying the reference, interpolation, physical
mapping, clipping of roundoff-level negative species, and all input hashes.

The `travelling` recipe mirrors the reference temperature and composition about
the domain centre. Here `u_b` is the reference velocity at the joined centre
state, which can differ slightly from the far-downstream value. On the right,
velocity is `u_b - u_ref`; it has the opposite
sign on the left. In the centre-rest frame each front initially moves outward
at `u_b`, while its propagation speed relative to fresh gas is the independently
calculated `u_ref,u`. The `zero` recipe uses the identical T/Y fields and U=0,
isolating the initial velocity field. Initial velocity is an input, not a flame
speed acceptance result. Subsequent front motion must be measured independently.

Dependencies: `fresh-start` for the original-zero case, `ideal-baseline` for
supported conditions, the shared adaptive ASCII field reader, and the standard
Python library. Existing native or
Cantera-transport solvers may consume the generated case after their own
qualification. The Cantera SDK is not needed by this generator. Credentials
are external. Profile/result inputs are read-only; all generated paths must
remain under the selected project root. No CFD checkpoint is accepted or copied.

Example: `python3 prepare.py plan phi110 profile.csv results.json NEW_CASE
--velocity travelling --end-us 20`. Inspect the plan before `apply`. Mesh,
chemistry, transport and boundary dictionaries retain the fresh-start choices.
The normal runtime boundary-density finalizer must still run before execution.
The source has no submission side effect.

The runtime saves its arguments in named variables, then clears positional
arguments before sourcing OF8 bashrc. OF8 otherwise sources existing argument
files as shell settings. Initial attempts 125031691/125031693 exposed this with
the CSV/JSON inputs and were cancelled; they are excluded from comparisons.

`submit.sh plan|apply ROOT RELEASE LIBRARY INCREMENT_TEST PROPERTY_TEST
PROFILE RESULTS VELOCITY` submits one eight-rank, 20-microsecond diagnostic.
Both property receipts must pass and identify the same library. The job builds
the current-species-enthalpy native solver against that library, tests ideal
small increments, verifies original zero fields, and records distinct CPU
assignments. Its one-hour limit reserves at most eight core-hours. The recipe
is part of the submission ledger identity. It cannot restart or extend a case.
The completed endpoint must pass finite-field and zero-time-history checks;
subsequent independent front tracking supplies the speed comparison.

Verification: `python3 prepare.py verify CASE` checks all 53 zero-time species,
normalization, symmetry of T/Y, antisymmetry of U, expected front positions,
source hash, and absence of positive-time directories. Use the existing
fresh-start verifier after decomposition. A mismatched profile hash or nonideal
reference must fail before case creation. Record native/Cantera molecular-weight
differences separately; interpolating a Cantera profile does not remove them.
