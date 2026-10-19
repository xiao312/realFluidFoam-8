# Cantera bridge qualification, 20 October 2026

The C interface reproduces the saved ideal, smooth-SRK and dense-diffusion
FreeFlame properties inside the pinned OpenFOAM 8 environment. It now supplies
conductivity and mixture diffusion coefficients to an isolated ideal-gas CFD
experiment. No production solver has been replaced or merged.

Source is draft/cantera-bridge at 0f31be8, based on integration 8a0c8d0.
Bridge qualification job 124942015 checked 51 states per model. Maximum scaled
errors in density, absolute enthalpy, Cp and conductivity were 3.17e-10 or less.
Relative mass-source imbalance was below 4.4e-16; the partial-enthalpy Euler
identity error was below 7e-15. The ABI0 client also passed with the OF8 core
library preloaded, while the bridge and pinned Cantera SDK use ABI1.
Transport-only calls exactly reproduced conductivity and diffusion from complete
evaluations while skipping chemistry. Invalid composition and species counts fail.

Bridge SHA256: `b5ab1a37e58a62b205dbd0c64ded62668a56341e43266ac2ffd1180c72c02001`.
Client SHA256: `47c55f6641636aacb50708db3955db3aaf35e6cfe8b34f5a6bc428bbc77c2d79`.
SDK is the preserved Cantera 3.2 build in job 124917358. All dependencies are
recorded by the qualification job's ldd output. Earlier job 124941247 passed
host property checks but stopped during OF8 shell startup under errexit.
Source 4fc26d7 initializes OF8 before enabling strict shell checks; retry
124941425 passed. Those failed and successful receipts remain preserved.

CFD build/smoke job 124942088 passed with eight MPI ranks and 8,000 cells.
It generated original time-zero fields and ran to 100 ns. Temperature stayed
between 298 and 2230.0375 K; maximum species-sum error was 1.15e-12. The first
tracking record was exactly zero. Solver SHA256 is
`b10bbc15cd9e2e6eeedb9b23965dba4cddf69a5500ef96ab545bcbd82cd7c93e`.

Full phi=1.10, 100-atm, 298-K job 124942608 uses that solver and bridge, eight
cores and an eight-hour ceiling, targeting 300 us. It generates a new original
zero state; it does not continue the smoke case. The existing energy-only and
native controls remain on their pinned binaries.

This experiment changes kappa and Dimix and applies the separately tested
current-state native species-enthalpy refresh. It retains native Cp, enthalpy,
viscosity, chemistry integration and equation placement. The transport update
uses the same initial/end-step placement as the native baseline. It therefore
isolates transport against the energy-corrected control, not against the
unchanged native solver. Absolute Cantera enthalpies are not used in the native
sensible-enthalpy equation. Nonideal CFD and CVODE coupling remain unimplemented.

The flame result, time/grid independence and conservation remain unqualified.
A successful ABI or smoke test is not a flame-speed replication result.
