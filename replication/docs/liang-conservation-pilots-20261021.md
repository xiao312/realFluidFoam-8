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

## Tighter convergence: qualification passed

The ten matched controls subsequently completed from source
`fcd11507e74587a4e3aced0f383d630018121a01`, build `125096463`, with
steady relative/absolute tolerances 1e-7/1e-13. Driver SHA256:
`e0bafb55a7a648074e7d48ecfb2e45d5c863abd11dadc380c633e76aa86115a5`.
The driver change exposes those tolerances; property models, native residual
definitions, inputs, guesses and grid factors remain the same.

All four conservative controls passed every predeclared native balance check.
The [machine-readable audit](liang-conservation-tight-20261021.json) retains
the individual identities, physical flux checks and output hashes.

| Case | Grid factor | Job | Speed (cm/s) | Burned T (K) | H-flux relative span | Energy span (equivalent K) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 125096726 | 76.002275 | 2311.856851 | 7.457e-8 | 0.0001695 |
| 1 | 2 | 125096732 | 75.983343 | 2311.857490 | 4.712e-8 | 0.0008850 |
| 3 | 1 | 125096747 | 75.435335 | 2299.636248 | 7.378e-8 | 0.0002060 |
| 3 | 2 | 125096750 | 75.417332 | 2299.636857 | 4.755e-8 | 0.0008903 |

Doubling the initial grid changes speed by less than 0.025% in each case and
burned temperature by less than 0.001 K. This supports incomplete nonlinear
convergence as the cause of the earlier conservative balance failures.
It does not resolve the Case 3 paper-speed discrepancy. The native residual
identities also passed deliberate species/enthalpy face-flux corruption tests:
both injected errors were detected, and captured original files were unchanged.

## Completed five-case, three-condition comparison

All 30 conservative controls now pass every native balance check: Cases 1–5,
phi=1.0/1.3/1.4, and two initial-grid factors. The
[expanded record](liang-conservation-expanded-20261021.json) contains the
observed build identities, native audits, grid pairs and unchanged paper
comparisons. The largest two-grid speed change is 0.0541%; the largest
endpoint-temperature change is 0.000883 K.

Case 2 uses source `31694902ffebc63222959adb2d95751c5ea3a165`,
build `125099135`, executable
`dcc81cba72e91f1b5003081b88696847ac5241924485f3ad06c625cea1df73f3`.
That driver changes output precision relative to `fcd1150`; its governing
equations and physical inputs remain the same.

| Phi | Case 1 | Case 2 | Case 3 | Case 4 | Case 5 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 42.551313 | 44.179617 | 41.811552 | 42.387778 | 41.523363 |
| 1.3 | 73.513284 | 76.321841 | 72.920055 | 73.682476 | 72.745064 |
| 1.4 | 75.983343 | 78.946432 | 75.417332 | 76.184626 | 75.254799 |

Values are fine-grid speeds in cm/s. Figure 3 has no readable reference at
phi=1.0; none is extrapolated. At 1.3 and 1.4, Cases 1/2 pass the existing
speed screen with errors below 0.31%. Cases 3–5 fail: their errors are
5.02–5.97%, 8.37–8.55% and 9.86–10.22%, respectively.

All twelve selected Figure 4 density/burning-flux comparisons lie inside their
existing graphical reading allowances. The Case 1→2 burning-flux increase is
0.55–0.92%, much smaller than the speed increase, consistent with the paper's
density-effect explanation. These are graphical comparisons, not additional
experimental validation.

Figure 5 remains imperfect. At phi=1.0, ideal Case 1 ends at 2484.882 K,
5.443 K above its paper marker; at phi=1.3 it ends at 2359.280 K,
1.425 K below the marker. Case 3 at phi=1.3 is 5.052 K below the paper line
despite its higher flame speed. A uniform temperature shift would not resolve
these discrepancies. Cases 3–5 converge to the same endpoint within 0.001 K
at each condition, as expected when only transport changes.

Conservation and mesh qualification therefore strengthen the numerical result;
they do not establish full replication or justify fitting transport coefficients.
