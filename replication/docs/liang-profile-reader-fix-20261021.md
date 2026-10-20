# Hydrogen saved-profile reader correction

Five finer-grid hydrogen controls stopped before solving because `std::stod`
rejects representable subnormal values on the SCNet runtime. The bounded parser
now preserves those finite concentrations. It changes no flame equation,
transport coefficient, initialization normalization or convergence criterion.

Affected jobs: `125093097`, `125093101`, `125093120`, `125093125`, `125093127`.
Each log contains `stod`; these are failed input reads, not converged flames.
Their source was `ae10e5c32ea9e794a2ab584f1f03eb72af4788cd`,
build `125091444`. Their original jobs and numerical guesses remain recorded.

The parser uses `strtod`, accepting its range flag only for a finite, nonzero
subnormal result. It rejects overflow, underflow to zero, nonfinite values,
empty fields and trailing junk. Errors identify the source file, row and column.
Negative trace values are preserved exactly; the parser does not clip them.

## Qualification

An isolated regression was first compiled against the immutable old header.
Job `125094059` reproduced the `stod` failure in 30 seconds. The corrected
header and regression then passed in job `125094559`, in 26 seconds:

- Eight valid fixtures preserve both ordinary values and subnormal traces.
- Six invalid fixtures fail with the expected row and column.
- The actual Case 3 native-Soret profile, job `125091783`, loads all 1,969 rows.
  All species values equal the original parsed values; 83 are subnormal.

Both jobs used the same existing Cantera SDK and GCC 11.2.0. Their compilation,
input hashes and qualification outputs remain under their job directories.
Local receipts are under `state/liang-hydrogen-20261020/` in the operator
project. The fixed regression is now part of every hydrogen build.

This qualification covers numeric input handling. A newly committed driver
must still pass its full model build checks before the matched finer-grid
controls are resubmitted. Paper agreement is assessed separately.
