# Energy-to-temperature inversion

This module inverts the executing thermodynamic function at fixed pressure.
It owns numerical convergence for the existing `THs`, `THa`, `TEs` and `TEa`
interfaces. It does not select an EOS phase, change transported energy,
normalize composition, or implement phase equilibrium.

Inputs are target energy in J/kg, pressure in Pa, an initial temperature,
and the existing value, derivative and temperature-limit member functions.
The output is a temperature whose evaluated energy satisfies the residual
criterion. There is no new dictionary option or external dependency.

Newton iteration requires residual reduction. A bracketed fallback handles
unhelpful derivatives. A small temperature step or bracket is not convergence.
The residual limit is `1e-8 J/kg + 1e-10*max(1, abs(target), abs(value))`.
Unbracketed targets and unresolved branch jumps fail with their target,
pressure, initial guess and best residual. No failed temperature is accepted.

Dependencies are the existing OpenFOAM scalar/error facilities and the supplied
thermodynamic functions. All custom thermo, transport, chemistry and solver
binaries that instantiate this header must be rebuilt together. No secrets,
network access or additional runtime library is used.

Example: the existing `model.THs(h, p, Tguess)` call uses the new stopping rule.
Root selection remains an independent, explicit EOS configuration.

Verification uses the executing full-library one-cell probe through Slurm.
Replay the retained G2 point from six initial guesses under both root policies.
The homogeneous-Gibbs case must pass the unchanged target residual checks.
The largest-root gap must be rejected explicitly. Then run pure-stream and
single-root mixture round trips, linkage checks, and a fresh-zero CFD case.
Numerical inversion success does not establish VLE or paper agreement.
