# Density/internal-energy recovery as a next coupling diagnostic

The current Cr100 G2 controls complete 1 ms, but the independent Cr1 cases
fail near 162 K. This note proposes an isolated diagnostic, not a qualified
solver change. Existing absolute-Ha cases and failed verdicts remain intact.

## Observed problem

The exact R61b Schmitt state replay, job128078384, fails fixed-pressure enthalpy
recovery at 5.250615 MPa for both tested homogeneous root policies. The same
composition and enthalpy target recover at 5.6 MPa. Across a 10-microkelvin
interval, the largest-root path jumps by 17.178 kJ/kg. Independent polynomial
roots match the returned density: the available root set changes from one dense
root to three roots, and the policy selects the new largest root. This is not
evidence that loosening Newton tolerances repairs the thermodynamic path.

The completed 1 ms solver budgets also distinguish small assembled-equation
residuals from accepted-state enthalpy drift after coupling: 0.02121 J for
Schmitt and 0.000785 J for Cavalieri. These are diagnostic budget differences,
not independently qualified total-energy conservation errors. Energy and
pressure stages consume about 93.5% and 92.4% of measured step wall time.

## Upstream implementation inspected

[PelePhysics SRK source, pinned e2a9595](https://github.com/AMReX-Combustion/PelePhysics/blob/e2a95959175fb07a5006aa551ef93579bdc60250/Source/Eos/SRK.H#L452)
provides `REY2T`: density, internal energy and composition determine temperature
through Newton iteration using real-fluid Cv. It reuses composition/density
terms within that iteration. `RTY2P` then evaluates pressure directly, while
`RTY2E` evaluates ideal and departure contributions to internal energy.
`RHY2T` is explicitly unsupported. The implementation requires a reasonable
temperature guess and checks the iteration ceiling; it is not a phase flash.

The [EOS documentation](https://pelephysics.readthedocs.io/en/latest/EOS.html)
describes SRK support in PeleC and its additional computational cost. This is
an implementation reference, not evidence that our mechanism, transport,
phase treatment or G2 predictions would match PeleC.

## Proposed falsifiable test

First add a zero-step density/temperature property path using our exact SRK
coefficients and caloric reference. Round-trip e(rho,T,Y) and p(rho,T,Y) before
attempting e-to-T recovery. Compare analytical Cv with finite differences away
from discontinuities. Exercise the retained cold, hot and critical compositions
with multiple guesses and both pure-stream endpoints. Check energy-reference
and SI/CGS conversions explicitly; do not copy upstream constants silently.

Then test closed, fixed-volume composition changes with conserved total mass,
elements and internal energy, allowing pressure to respond. Such a control has
different constraints from an open-flow pressure/enthalpy update. A smooth
fixed-density temperature inversion does not establish mechanical stability,
mixture VLE, pressure equilibrium at material contacts, or conservative CFD.

Only after those controls should a separate solver candidate be considered.
Pressure correction, species transport, total energy and EOS density must use
compatible accepted states. Preserve the current baseline, require fresh
time-zero CFD, and measure pressure/velocity equilibrium and physical energy
flux budgets. Do not replace the current method by changing its energy variable
without deriving the corresponding equations.

No new EOS API, dependency, root policy, build or CFD admission is introduced
by this documentation checkpoint. Raw source/hash receipts, query data and
timing audits remain in the operator evidence workspace.
