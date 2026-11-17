# SRK caloric correction: development scope

The previous reviewed-mesh campaign exposed a reproducible root-selection
failure near the injector. This change targets numerical inversion and an
explicit homogeneous root policy. It does not fit paper curves or change
transported energy, chemistry, reference enthalpy or acceptance criteria.

## Executed baseline

The retained G2 point has p = 5.203039 MPa, T = 162.88355 K and 23 species.
Largest-root inversion leaves about 238 J/kg residual from six initial guesses.
Actual samples 10 microkelvin apart jump by 8872 J/kg in selected enthalpy.
The transported target lies within that sampled jump.

The existing homogeneous-Gibbs option reduces the point residual to 0.0173 J/kg.
It passes the CFD-style caloric and joint density/enthalpy checks. The stricter
fixed-pressure target check still fails from all six guesses. These outcomes
remain failed where their original criteria fail.

## CoolProp review

CoolProp 8.0.0 is pinned for supplementary reference calculations. Its installed
revision is `ae81610e7d23efc57f9d051c8e70a4d66e87537f`.

The [cubic backend source](https://coolprop.org/_static/doxygen/html/_cubic_backend_8cpp_source.html)
enumerates cubic density roots. Its global, unimposed-phase path compares Gibbs
energy instead of assuming the vapor root. Explicit phase requests use a
different path. This supports explicit phase policy in our implementation.
It does not prove global mixture phase stability.

The [cubic API documentation](https://coolprop.org/coolprop/Cubics.html)
states that supported flashes and properties are limited. Pure O2/CH4 and
matched reduced-cubic checks are suitable references. CoolProp's standard
parameters and caloric reference must not be treated as identical to this
fork's historical constants, mixing parameters and NASA formation basis.

The [flash implementation](https://coolprop.org/_static/doxygen/html/_flash_routines_8cpp_source.html)
separates branches and uses bounded root solves for applicable inversions.
A temperature bracket alone cannot establish that a discontinuous caloric
target has a root. Our final energy residual remains the convergence authority.

## Implementation and qualification

Energy inversion now requires an evaluated residual. Newton steps must reduce
it; a bracketed fallback handles poor derivative steps. An unresolved gap fails
explicitly rather than returning a falsely converged temperature. The residual
limit is 1e-8 J/kg plus 1e-10 times the energy scale. No EOS branch is silently
forced by the inverter.

The probe's target-only option isolates the existing strict captured-point
checks from the wider property sweep. It refuses missing target configuration.
The complete 15-library stack and all dependent applications require rebuilding.

Qualification must include the exact captured points from multiple guesses,
the largest-root gap as a rejecting control, pure-stream and single-root
mixture round trips, independent root checks, and exact dynamic linkage.
Then run a fresh-zero G2 case on the owner-reviewed geometry. Track sustained
reaction, pressure/energy consistency and actual literature profiles.

Implementation is not executed qualification. Homogeneous Gibbs selection does
not implement composition-changing VLE. New failures remain visible and guide
the next development action; they do not authorize weaker criteria.

## Executed first qualification

Full-stack source `0c30b603a83810479dca12fb65a919478e7233a2`
rebuilt all 15 libraries and four applications in job 128238372.
The envelope returned 0 after 1220 seconds. The earlier job 128238085
failed before payload in four seconds because a required scope marker was
missing; no compiler or scientific result came from that attempt.

All six captured fixed-pressure targets now satisfy the unchanged strict
criterion. Maximum absolute enthalpy residual is 1.631945e-5 J/kg, compared
with 0.0172581 J/kg under the previous homogeneous-Gibbs inverter.
All six joint density/enthalpy queries pass. The original largest-root case
rejects its unresolved approximately 238 J/kg gap rather than reporting
convergence. The positive pure-stream runs report zero numerical failures.
However, the subsequent oxygen missing-target negative control truncated its
property/inversion exports. Those raw rows require regeneration before CFD;
the original receipt and empty exports are preserved.

The probe now handles target-only audits before opening property/inversion
streams. This output-preservation repair needs its own compiled check.
The solver and all library sources are unchanged by that probe-only repair.

## Independent matched-cubic reference

The captured fixed-composition coefficients satisfy the square-alpha identity
to 1.67e-15 relative error. An algebraic mapping matches its reduced a(T) and b
in CoolProp 8.0.0, accounting explicitly for the different gas constants and
SRK critical constants. This diagnostic pseudo-fluid does not replace any
CFD material parameter. Both imposed-phase roots and residual Helmholtz
energies come from CoolProp; the smaller residual Gibbs energy determines
the homogeneous choice. An unspecified-phase custom-fluid flash failed and
is not used as evidence.

Across 51 executed temperatures, maximum relative density difference from
the fork is 5.678e-13. Combining CoolProp residual enthalpy with the exact
frozen NASA ideal/formation polynomials gives maximum absolute Ha difference
2.239e-7 J/kg and Hs difference 6.980e-8 J/kg. No offset is fitted. This checks
fixed-composition root/caloric implementation, not composition-changing VLE,
transport accuracy, source interpolation, or reacting CFD agreement.

The prepared fresh-zero G2 comparison preserves C19 geometry, table, stream
assignment, ramp, ignition and final criteria. It explicitly changes the
root policy and evaluated-residual inversion. Its first requested end time
is 4 ms; this is a coupling milestone, not a developed literature mean.
