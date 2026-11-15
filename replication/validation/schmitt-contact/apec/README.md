# Conservative single-component APEC contact prototype

This isolated OF8 application tests the approximate pressure-equilibrium flux
of Terashima, Ly and Ihme (2025), DOI10.1016/j.jcp.2024.113701, using actual SRK
oxygen thermodynamics. The two-point flux adapts the public Trixi.jl implementation
at commit3ffaf4b91885fd3ede90d54476263ad3073a722d; retain NOTICE.md.

Inputs: fresh serial uniform-x contact cases, pure O2, original absolute-energy
reference, maxAcousticCo/maxDeltaT/endTime and explicit contactAPECInviscid yes.
Outputs: conserved rho/momentum/total energy, actual EOS properties, profiles and
boundary-budget/pressure diagnostics. It does not implement reaction, mixture
composition derivatives, diffusion, LES or a G2 replacement. No network/secrets.

The shared ContactDF state/mixture types supply SRK coefficients and initial
checks only. This application uses a shared conservative energy flux and direct
rho/e recovery; it does not freeze gamma, project energy or inherit double-flux
energy synchronization. Smooth oxygen contacts are the initial physical tests.
Central APEC is not a general positivity-preserving shock scheme. Invalid accepted
states fail and are retained; inadmissible Newton trials trigger step reduction.

Dependencies: existing contact factory, initializer, ContactDF state definitions,
OF8 and pinned custom thermo DSOs. Dependents: the S16 qualification wrapper.
No production solver or scheduler depends on this experimental application.

Build with wmake inside a FlamePilot allocation. Prepare a fresh oxygen case
with the contact factory and configure.mjs, run initializeSchmittContact, then
realFluidContactAPEC -case NEW_CASE. First run a uniform control and nx2 oxygen
contact. Verify normal end, actual EOS/caloric identities, derivative finite-
difference agreement, mass/energy budgets and pressure/velocity departures.
Neither compilation nor a normal exit establishes paper or reacting acceptance.

The explicit --uncorrected control disables only the APEC internal-energy
face correction. It retains the same central flux, recovery and time scheme.
The S17 comparison keeps the nx2 physical erf width fixed while changing grid
resolution400/800/1600, separating under-resolution from a source-clock issue.
The inherited low-temperature NASA extrapolation remains a declared limitation.
