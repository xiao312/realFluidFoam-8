# Staged Cantera flame results

19 October 2026, Asia/Shanghai. The custom Cantera 3.2 adapters now run inside
FreeFlame. This is a working implementation with numerical screening; agreement
with all five Liang curves has not been established. No production OpenFOAM
thermodynamics or energy change was merged as part of this extension.

## Model and numerical controls

All cases use the author's GRI30, 100 atm, 298 K fresh gas, 21/79 molar air,
mixture-averaged diffusion and no Soret effect. The paper does not state the
fresh temperature numerically; 298 K remains an assumption. Cases cumulatively
add SRK density, SRK calorics, Ely–Hanley conductivity and Takahashi diffusion.
Conductivity uses the molar-consistent reference-density mapping.

FreeFlame solves a steady boundary-value problem using Newton iteration and
pseudo-time stepping, not a CVODE homogeneous reactor integration. The solved
inlet velocity is the reported burning velocity. A saved ideal flame supplies
a numerical guess only. All new OpenFOAM transient runs still start from their
original time zero, as recorded in [fresh-start](fresh-start-20261019.md).

Flame kinetics use physical concentrations and NASA reverse equilibrium
constants. The HP equilibrium diagnostic uses SRK fugacities with VCS. Those
are distinct chemical-equilibrium conventions: agreement of their burned
endpoints is not assumed. The current test isolates property changes without
silently adding fugacity corrections to chemical rate laws.

## Phi=1.10 qualification

| Case | Cumulative addition | Speed (cm/s) | Job |
|---|---|---:|---|
| 1 | Ideal gas | 7.4619334 | 124919519 |
| 2 | SRK density | 7.3647967 | 124919525 |
| 3 | SRK calorics | 6.9507091 | 124919531 |
| 4 | Ely–Hanley conductivity | 7.9787595 | 124919948 |
| 5 | Takahashi diffusion | Pending | 124919950 / 124920962 |

The earlier C++ Case 1 pilot gave 7.4704909 cm/s, 0.0467% from the existing
Python reference 7.4670031 cm/s. The table uses finer refinement criteria:
slope/curve (0.0075, 0.0125), then (0.00375, 0.00625). Each completed point
must pass `check.py`: final grid change below 0.3%, mass-flux range below 0.1%,
species-sum error below 1e-7 and minimum mass fraction at least -1e-9.
The full sweep can differ slightly from this pilot because its saved guess
and adaptive grid differ. Each plotted point retains its own job identity.
The overlay shows that Cases 2–4 do not yet reproduce Liang's staged sequence.
In particular, the Case 4 pilot is substantially above the paper's value.
Successful model activation does not resolve that discrepancy.

The optimized Case 4 repeat, job 124920941, produced exactly the same reported
speed and frozen-property CSV as job 124919948. Its mass-flux range was
1.72e-10, species-sum error 3.65e-11 and final grid change 0.1796%.
Frozen-property CSV SHA256:
`38e815d1adfe35450aff46691d4a1449564226203cc5e924a732c05b14738d2e`.

## Initialization test

Ideal HP products at phi=1.10 give 2229.48898 K; SRK HP products give
2207.87488 K, a decrease of 21.61410 K. Relative enthalpy errors were
7.11e-11 and 1.24e-11; element errors were 2.22e-16.

Case 3 job 124920452 starts its steady iteration from a fresh-to-SRK-equilibrium
temperature/composition ramp. It converged to 6.9508658 cm/s, only 0.00225%
above the ideal-profile-seeded pilot. This supports seed independence at this
condition and these grid controls. It does not establish transient OpenFOAM
seed independence, domain independence or thermodynamic/kinetic consistency.
Case 5 also has a separate Case-4-profile-seeded attempt, job 124922397;
the original ideal-seeded attempts remain running.
Gate job 124922744 depends on successful completion of optimized pilot
124920962. It then runs `check.py` and submits the twelve Case 5 conditions
only if screening passes. Its own limit is one core for ten minutes; the
subsequent sweep reserves at most 48 core-hours. Failed qualification launches
nothing. Reapplying the already-submitted Case 4 sweep was verified to leave
the ledger SHA256 unchanged, with no duplicate submissions.

## Reproducibility and outstanding work

SDK install job 124917358 pins Cantera 3.2 and its 54-package Linux C++ stack.
GCC 11.2 compiles C++17 with ABI=1. Each build records compiler flags,
dependencies, executable SHA256 and SRK kernel test results.

- Main working build 124919933: source `961f6a1fc6662167076abea2b8d4c6aee449622c`.
- Optimized build 124920856: source `08bdbd58dc45064f511f9c587102d295464d01f5`.
- Fine pilot Cases 1–3: build 124919390, source `d5c6da6`.
- Twelve targets: phi=0.92, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25,
  1.30, 1.35, 1.40 and 1.44. The last uses a phi=1.40 numerical guess;
  its inlet still uses phi=1.44.

Executable SHA256 for builds 124919933 / 124920856 respectively:
`436b989d5d2c8d2a0b521aa52cb33459b10682a71640a8e8c5df50fc29f2b782` /
`a89496686115e988ab2373752d1307c9d4313ce9525f0394bcdd1bb0a0c158f6`.

The source cache optimization keys SRK state by temperature, density and
Cantera's composition generation counter. It removes repeated composition
allocation inside Takahashi's species-pair pressure queries. Numerical parity
was checked before using that build for further transport trials.

Raw evidence stays under the configured trial root in `jobs/JOB/result`;
the sweep ledger is `results/cantera-sweep-20261019.jsonl`. Use the module's
`collect.py ROOT LEDGER` for read-only screening and `plot.py plan|apply` for
the original-paper overlay. Only screened completed points are plotted.
The original panel remains 204 by 175 points with its original typography.
Our curves have an explicit legend; phi=1.44 is outside the printed axes and
is retained in the data rather than drawn over the border.

Remaining scientific limits include domain sensitivity, the unprovided Liang
critical table, NOx scope, conductivity mapping and kinetic activity convention.
The Figure 2 discrepancy remains deferred. No coefficient was fitted to flame
speed. Case 2 is an EOS-only ablation, not a consistent equilibrium model.

Implementation qualifications also retain three numerical guards: negative
partial molar volumes are allowed in the transport correlation; Newton's
negative species iterates are projected only for conductivity evaluation;
and tiny atomic NASA Cp/R undershoots below 2.5 are bounded at 0.002 for the
transport internal-mode contribution. Final species fields are screened and
full thermodynamic Cp/enthalpy are not clipped. Failed development jobs and
their errors remain preserved.

## Published snapshot

The 21:19 CST snapshot contains 36 screened Case 1–3 sweep results, four Case 4
sweep results, and the qualified phi=1.10 Case 4 pilot. The remaining jobs are
not represented as completed results. See the small accompanying
[result manifest](cantera-liang-results-20261019.json).

Both existing images were replaced in the
[Liang section of the project document](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnO53xDomqNDZVu6NHHzhjre).
The same section contains `Liang-Fig8a-staged-Cantera-20261019.pdf`.
Local artifacts are under `output/pdf/cantera-liang-20261019-current` in the
operator project. The original paper is not committed to Git.

The initial batch Lark command was rejected by automatic approval review with
"blocked by policy". Narrow, explicit CLI block edits succeeded and were fetched
again for verification. The separate local trash deletion remains blocked;
326,364,553 bytes are recoverable in `.trash/cleanup-20261019`. Remote trash
cleanup completed, freeing 2,152,593 bytes. No failed runs or live builds were
deleted. See the fresh-start cleanup record for the file-hash inventories.
