# Executing oxygen caloric/derivative audit

Query the exact qualified SRK property implementation at6MPa,5.61MPa and the
two retained pure-oxygen rho/e failure pressures. The factory creates fresh
one-cell pure-O2 fields with the original full53 thermo dictionary. No flow,
phase flash, restart, parameter fitting or acceptance change occurs here.

Inputs: pinned S07 probe599c29fe/source6a9a2ac, R54 library receipts/products,
original thermo manifest and explicit temperature arrays. Outputs: actual
cold-properties.csv (including Cp and finite-difference dHs/dT), executing SRK
coefficients, per-query exits and summary metrics. The fixed1e-3K finite-
difference increment is a resolution limit near a phase/critical discontinuity;
a mismatch is not automatically proof of an analytic derivative error.

Dependencies: existing probe factory, exact R54 thermo and S07 executable,
Node built-ins/OF8. No new compilation, scheduler implementation or credentials.
FlamePilot admits a2core4GiB allocation; Bash/Node/hash/runtime preflights run
before queries. Main.sh delivers all query data even for explicit numerical
failure codes. Delivery is distinct from physical/scientific approval.

Read-only example: node prepare.mjs NEW_CASE p6000. Add --apply only inside
Slurm. Verify source/product hashes, pure composition, query pressures and
finite rows. Retain nonfinite/failed cases and NASA extrapolation disclosures.
