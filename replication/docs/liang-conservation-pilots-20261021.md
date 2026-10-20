# Hydrogen conservative-residual pilots

At 04:45 CST on 21 October, all ten rich-hydrogen pilots had completed. The
conservative species residual reduces elemental drift, but the four completed
conservative runs do not yet pass the declared balance screens. No model
coefficient or acceptance limit was changed.

Source `a299287e2f6886521e864aa9d7dafb0a618dcc91`, build job `125095444`,
executable SHA256
`164c3728a71807ab6ca8948c273fc71506f1df207ec53851d78a665a8e161e66`.
All use the Burke author-pair input, 100 atm, 298 K, phi=1.4, 10 mm domain,
pressure-based chemistry and Soret off. Same-case completed steady profiles
supply numerical guesses; these are not transient CFD restarts.

| Case | Residual | Initial grid factor | Job | Speed (cm/s) |
| --- | --- | ---: | ---: | ---: |
| 1 | baseline | 1 | 125095636 | 76.132613574 |
| 1 | baseline | 2 | 125095639 | 76.047749892 |
| 1 | total enthalpy only | 1 | 125095642 | 76.108930038 |
| 1 | total enthalpy only | 2 | 125095651 | 76.050053446 |
| 1 | conservative species and total enthalpy | 1 | 125095658 | 76.002942058 |
| 1 | conservative species and total enthalpy | 2 | 125095660 | 76.001715482 |
| 3 | baseline | 1 | 125095667 | 75.545583932 |
| 3 | baseline | 2 | 125095671 | 75.487108485 |
| 3 | conservative species and total enthalpy | 1 | 125095677 | 75.435972475 |
| 3 | conservative species and total enthalpy | 2 | 125095682 | 75.436426156 |

Native flux/residual identities agree to below 1e-14. Chemical mass and element
conservation, inlet/outlet flux definitions and total diffusion mass closure
pass their declared checks. The remaining measured failures are:

| Job | Largest active-element flux span / inlet flux | Energy-flux span (equivalent K) | Failed screens |
| ---: | ---: | ---: | --- |
| 125095658 | 2.364e-6 | 0.002885 | elemental flux |
| 125095660 | 2.508e-5 | 0.086002 | elemental and energy flux |
| 125095677 | 2.395e-6 | 0.002764 | elemental flux |
| 125095682 | 2.373e-5 | 0.088884 | elemental and energy flux |

Limits remain 1e-6 relative active-element flux span and 0.05 K equivalent
energy-flux span. The driver used the unchanged default steady tolerances
1e-5 relative and 1e-11 absolute. The next controlled comparison tightens
those tolerances to 1e-7 and 1e-13 with the same source inputs, guesses and
grid factors. It tests whether incomplete nonlinear convergence explains
these balance errors; this explanation is not yet established.

Liang's Figure 3 Case 3 reading at phi=1.4 is about 71.81 cm/s. The small
discretization effect here does not resolve that scientific discrepancy.
Raw snapshots, configurations and native balance tables are retained outside
Git under the local `liang-hydrogen-20261020` state directory. The independent
`conservation.py` audit preserves measured failures and file hashes.
