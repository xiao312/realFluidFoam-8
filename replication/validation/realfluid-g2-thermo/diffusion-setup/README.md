# Guarded SRK diffusion-setup qualification

This module verifies the optional omission of unused SRK diffusion matrices. It
does not change property models, field equations, source acceptance or table
coverage. The source optimization requires `hePsiThermo`, fixed controls,
absolute enthalpy and laminar/Fourier transport with an explicit tabulated
composition model.

Inputs are the existing six physical-state pair directory, a newly compiled
probe, and the physical steady/FGM periodic cases. The build must recompile the
basic and reaction thermophysical registrations, combustion library, solver and
probe. The other library identities remain in the composed runtime receipt.
There is no network or secret access. Output CSV/JSON and logs stay in the
allocated case directory. These checks do not establish paper agreement.

`node audit-setup.mjs PAIRS PROBE --plan` checks the physical A/B/A inputs without
mutation. `--apply` requires Slurm, writes a probe dictionary and executes fresh
processes for both modes. It compares active cell/patch properties and corrected
X/Y exactly, requires the four matrix row counts to change from 53 to zero, and
tests raw Dimix success in baseline mode and explicit rejection in optimized
mode. Repeated A must match before and after B. The existing six-state
property/inversion checks and public-Dimix negatives run independently first.

`node compare-steady.mjs BASELINE OPTIMIZED` requires both existing periodic
checkers to pass, equal time-zero Ha, all 53 species and thermo/flow fields at
four output times, and identical energy, caloric and composition histories.
Every numerical difference must be zero. Paths, timers and log headers are not
compared as physics. Run both cases from freshly generated time zero. The
existing FGM source-on pair uses its own checker plus the same exact-zero
requirement. Timings are reported separately from physical parity.

Dependencies: `diffusion-performance`, the concrete SRK mixture probe, and
`mascotte-g2/steady-flamelet`. Dependents: an operator-owned allocated
qualification packet and, only after its evidence, later G2 diagnostics.
Local verification is `node --check audit-setup.mjs` and
`node --check compare-steady.mjs`; compilation and physical checks require the
frozen OF8 environment and actual Slurm execution.
