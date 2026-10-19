# Parallel-layout qualification, 20 October 2026

The proposed 32-rank layout is faster in the 100-ns original-zero smoke, but
does not yet reproduce the eight-rank fields within the declared numerical
screen. It is not approved for the long comparison campaign at this snapshot.
The established eight-rank runs remain unchanged.

Both layouts retain the 8000-cell, 4-mm mesh and original central products slab.
The manual layout distributes the 400 initially hot cells across all 32 ranks;
each rank has 250 cells, including 12 or 13 initially hot cells. It has 95 internal
partition interfaces. Initial global T, p, U and all 53 species match exactly.
No saved transient field is reused.

| Test | Job | Result |
| --- | --- | --- |
| Standard eight-rank CP smoke | 124950245 | Completed, 122 s solver wall time |
| First 32-rank preparation | 124953306 | Failed before solving: OF8 requires a quoted manual-decomposition filename |
| Corrected 32-rank CP smoke | 124953793 | Completed, 43 s solver wall time |
| Global field comparison | 124953974 | Failed numerical parity screen |
| Strict eight-rank smoke | 124954635 | Submitted from original zero |
| Strict 32-rank smoke | 124954643 | Submitted from original zero |

The standard-layout comparison reconstructs original cell order using each
processor's `cellProcAddressing`; it does not compare unrelated local indices.
At 100 ns, maximum differences are 0.227276 K in T, 439.725 Pa in p,
0.0155573 kg/m3 in density, 0.0109331 m/s in velocity, 108.234 J/kg in sensible
enthalpy, and 2.64584e-6 in CH4 mass fraction. Peak absolute Qdot difference is
1.07403e8 W/m3, compared with the reference peak 2.82460e11 W/m3.
All initial field differences are exactly zero. Passing the individual finite-
field smoke did not establish decomposition independence.

The first pressure corrector uses relTol=0.1. Its residual and iteration count
depend on the partition; the final corrector reaches its 1e-7 absolute criterion.
This is a candidate explanation, not yet a diagnosed cause. The next pair sets
all linear absolute tolerances to 1e-10 and relative tolerances to zero, while
retaining the same timestep, PIMPLE and physical inputs. Its source is e62bdf4.
The bridge remains the independently qualified build124947872, with reactor
qualification124948146. No tolerance in the field-parity checker was relaxed.

The full eight-rank CP pilot124950538 continues from its own original zero.
The 2.84-fold smoke solver speedup excludes build/setup and does not predict
the eventual steady-flame cost; the reaction-zone load changes over time.

Reproduction: `development/cantera-cfd/submit.sh` has read-only `plan` and
mutating `apply` actions, with explicit execution and numerical profiles.
`decomposition_parity.py REFERENCE_CASE CANDIDATE_CASE` writes a JSON report to
stdout and exits nonzero on failure. Full job inputs and failed receipts remain
under the project-owned SCNet jobs directory.
