# PR heat-capacity derivative regression

This module checks the PR `Cp-Cv` identity against derivatives of the pressure
law. It does not fit model parameters or test agreement with a paper.

Inputs are the checked-out `PengRobinsonI.H` source and fixed O2/CH4 critical
properties. The optional `--header PATH` selects another trusted local header.
Output is a JSON summary on stdout. A failed criterion returns a nonzero status.
There are no generated files, external services, secrets or Python dependencies.
Node.js and its standard library are the only runtime dependencies.
The thermophysical library is the source dependency; cold-property qualification
and subsequent CFD are the consumers.

```sh
node replication/validation/pr-cpmcv/check.mjs
```

The check extracts the actual scalar `CpMCv()` body. It translates its limited
C++ scalar syntax into JavaScript and supplies the coefficient and state inputs.
This avoids maintaining a second copy of the expression under test. It is not
a C++ compilation check. Only trusted repository source may be supplied.

The independent reference evaluates the PR pressure law in molar volume.
Five-point numerical derivatives supply `p_T` and `p_v`, then
`Cp-Cv=-T*p_T²/(p_v*W)`. Two step sizes must agree within `2e-7` relative error.
The source result must agree within the same tolerance. The old SRK-shaped
expression is an explicit negative control. No CFD acceptance limits change.

## Observed failure and separate density discrepancy

The retained full build used source `282aa996a78939cbdaf591520231fb2c0476567d`.
Job `126403130` ran probe source `3dfa316dd2134d342befe38eb685f56d064935dd`.
At 5.61 MPa, PR oxygen gave these values:

| Temperature, K | Cp, J/(kg K) | Cv, J/(kg K) |
| --- | ---: | ---: |
| 140 | 2473.727634 | -7735.125006 |
| 165 | 2762.083630 | -78166.501848 |
| 170 | 2101.008287 | -1203.663523 |

All retained inversion errors were below the existing `1e-5 K` criterion.
PR also gave `Cv>Cp` for O2 at 150/155/160 K and CH4 at 200 K.
Positive-only checks did not detect those additional unphysical results.

At 85 K, PR oxygen density was 1329.023702 kg/m³; the paper inlet value is
1177.2 kg/m³. SRK gave 1181.226802 kg/m³. The PR density error remains separate:
this correction changes `Cp-Cv`, not the pressure law or root selection.
NASA polynomial use below its original temperature range remains unqualified.

## Required runtime qualification

1. Retain the original build, four CSV pairs, source and library hashes.
2. Create an isolated build copy and a new product directory inside the trial.
3. Apply only the frozen correction to the matching 282 source tree.
4. Rebuild affected template consumers with the qualified compiler options.
5. Build the exact property probe against that new library set.
6. Rerun PR/O2, PR/CH4, SRK/O2 and SRK/CH4 at their original states.
7. Retain positive/finite and `1e-5 K` inversion criteria unchanged.
8. Also require `Cp>Cv>0` at these stable single-phase states.
9. Report density, Cp, transport and inversion deltas separately.

Do not qualify PR CFD from the local source check alone. Mixed-fluid checks and
scientific comparison remain separate from these pure-fluid regression curves.
