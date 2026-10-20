# Methane numerical tolerance controls

The six default-tolerance reruns reproduce their previous solutions exactly.
Changing CSV output from 16 to 17 significant digits does not remove the
small Case 5 thermal-coefficient projection residual. The paired tighter
controls remain in progress at this checkpoint.

These controls use the same phi=1.10, 100-atm Case 4 steady guess for Cases
1, 4 and 5 with Soret off/on. They test numerical reproducibility, not a
new physical operating condition. The
[original six controls](liang-methane-phi110-controls-20261021.json) use a
different steady guess and remain a separate, qualified comparison.

## Matched defaults

Source `56e6bcba5cec8eeaf47a3ba366dec3b9ec26eb90`, build `125100350`,
uses the same default steady tolerances, `rtol=1e-5` and `atol=1e-11`.
Each result now records these values and its 17-digit precision in
`numerics.txt`.

| Case | Off job | On job | Off speed, cm/s | On speed, cm/s |
| --- | ---: | ---: | ---: | ---: |
| 1 | 125100405 | 125100406 | 7.461699994 | 7.364020278 |
| 4 | 125100407 | 125100409 | 7.134560604 | 7.040883876 |
| 5 | 125100411 | 125100414 | 7.050827540 | 6.956672381 |

The [parity record](liang-methane-default17-parity-20261021.json) verifies
identical input receipts, byte-identical refinement/property-check files,
and parsed profiles differing by less than 6e-15 relative.
All six numerical flame screens pass. The strict native-flux audit passes
Cases 1/4, but Case 5 retains a normalized coefficient-sum residual of
`1.245583851e-10`, above its unchanged `1e-10` threshold.
Its thermal-flux reconstruction residual is only `1.39e-17`.

Thus the projection residual is not a decimal-output artifact.
The maximum node-composition sum error in the corresponding original
solution is `2.817e-10`. The native coefficient projection uses the
unnormalized Newton solution fractions. Neither this residual nor its
threshold crossing explains a percent-level flame-speed discrepancy.
No profile was normalized and no audit threshold was relaxed.

## Tighter convergence

The matched `rtol=1e-7`, `atol=1e-13` jobs are `125100416`,
`125100417`, `125100418`, `125100420`, `125100421` and `125100424`.
They retain the same physical inputs, steady guess and refinement rules.
Their completed profiles must pass the same screens and native-flux checks
before any new diagnostic point is plotted. The defaults remain archived.
