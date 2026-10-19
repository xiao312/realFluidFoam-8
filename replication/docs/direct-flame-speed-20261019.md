# Direct Equation (40) checkpoint check

19 October 2026, Asia/Shanghai. The next measurement is the paper's direct OH
displacement-speed formula, before changing flame physics or boundary conditions.
This draft starts from integration `99d64f7cab456488f35df2df9c01f2b1cb1be6d7`.
The diagnostic implementation is `99ea3fbe1fd741735d8252fd4d6715820e8bd648`.
No integration merge or solver/library equation change is part of this test.

Nguyen 2022 Section 5.3, Eq.(40), gives

\[
S_d^* = \frac{\dot\omega_{OH}-\nabla\cdot\mathbf j_{OH}}
{\rho_u|\nabla Y_{OH}|}.
\]

The supplied PDF is the primary reference. The same fixed rising OH level,
2e-5, used in the existing comparison is the primary diagnostic level. Levels
1e-5 and 3e-5 test sensitivity. The paper does not specify a numerical OH level.
The existing 0.95–1.00-ms kinematic result at phi=1.10 is 6.36695 cm/s; the
temperature-front result is 6.13473 cm/s. Neither is a direct evaluation of
the chemistry/diffusion numerator.

## Controlled test

Job **124856329**, two cores, maximum 20 minutes (0.667 core-hours), processes
copies of six checkpoints from completed job **124797651**, times 0.95, 0.96,
0.97, 0.98, 0.99 and 1.00 ms. It advances no timestep. The donor case release is
`b54a8bf3297036e37e6c95732d25b7f8ab94b620`; its solver binary SHA-256 is
`f2df3effff068d9acf08ee023dc73ec3137a619a32ceeed4b1539255b28e4f6e`.
The utility links the same qualified library build **124657926** and uses the
existing pinned OF8 image. The read-only plan enumerated 4,132 input files,
55,848,903 bytes, before submission. Copied inputs are hashed individually.

The [utility module](../validation/flame-speed/README.md) calculates net mass
rates through the selected SRKchungTaka chemistry model's `calculate()`. It
forms the ordinary and molecular-weight diffusion Laplacians and subtracts
both all-species correction sums from the deployed species equation. Those
terms equal `-div(j_OH)` in that equation's spatial formulation. The energy
equation's separately constructed `YVi` is not substituted for this flux.
Density and transport are recomputed from each saved T/p/composition using the
qualified library; saved/recomputed density must agree within 1e-7 relative.
The same-state calculation differs from the time-integrated reaction source
and partly updated fields within the solver's sequential species loop.

Local checks: five manufactured-front/invalid-input tests passed; shell syntax
and whitespace checks passed. Compilation, checkpoint processing and numerical
agreement are separate scheduled checks. A successful diagnostic job does not
establish that the flame is steady or that the two estimators agree.

## Observed result: direct and kinematic measurements disagree

The utility compiled, linked to the qualified library, reconstructed all six
checkpoints and wrote all six CSVs. The job then **failed**, exit 1, on the
predeclared density reconstruction check. Elapsed time was 3 min 43 s on two
cores, 0.124 core-hours. Maximum relative density difference is 4.5941e-7,
above the 1e-7 guard. The guard remains unchanged. A subsequent local reporting
option emits provisional values with failure flags and a nonzero exit; it does
not change the job's status. Seven local tests now include that failure path.

The transferred CSV hashes match the remote originals. Cross-check against the
previously plotted snapshot gives exactly equal T, p and saved rho, and at most
3.86e-16 absolute difference in OH after reconstruction. This is the same saved
flame, not a different run or operating condition. The density mismatch is too
small as a denominator change to account for the much larger speed discrepancy;
its origin still needs a separate checkpoint/thermo-state audit.

Provisional instantaneous Eq.(40), same six times and fixed rising OH levels:

| OH mass fraction | Mean over six snapshots (cm/s) | Range (cm/s) |
| --- | --- | --- |
| 1e-5 | 123.542 | 120.872 to 126.688 |
| 2e-5, primary | 15.883 | 14.647 to 17.534 |
| 3e-5 | -59.578 | -60.344 to -58.986 |

At 1.00 ms and OH=2e-5, chemistry contributes -45.277 cm/s and corrected
diffusion +60.285 cm/s, leaving +15.007 cm/s. Existing front tracking gives
6.367 cm/s over 0.95–1.00 ms; Nguyen's digitized value is approximately
6.8 cm/s. The direct result is strongly dependent on marker level and cannot
be reported as a converged laminar burning velocity. Do not replace the Figure
12 sweep with a single unqualified point or select a level that fits the paper.

These results directly evaluate the continuous formula with instantaneous
constitutive rates and finite-volume spatial operators at a checkpoint. The
paper does not specify its discrete source-sampling implementation. The next
test must record **the actual timestep-averaged chemistry source and lagged
diffusion terms used in the species solve**, alongside the instantaneous
evaluation, on a copied-checkpoint short replay. Then vary timestep at fixed
mesh, and mesh at fixed controls, independently. This will distinguish source
splitting/sequential updates from derivative/interpolation error and an evolving
flame. No cause is established yet, and no physical-model correction is justified
by these numbers alone.

Raw evidence is `state/eq40-124856329/` outside Git; the small
[numerical receipt](direct-flame-speed-20261019.json) retains terms, hashes,
source/build/job identities, failure status and snapshot cross-checks.

## Interpretation before further simulation

1. If Eq.(40) and tracking agree across OH levels and late snapshots, the
   observed speed discrepancy is unlikely to be explained by estimator choice
   alone. Test longer relaxation and domain/seed independence next.
2. If chemistry and diffusion nearly cancel and the resulting speed varies
   sharply with level, retain each signed contribution. Check the spatial and
   timestep sensitivity and compare instantaneous with in-step averaged sources.
3. If the direct and kinematic speeds disagree, do not replace the plotted
   values merely because one is closer to the paper. Isolate interpolation,
   discrete convection, source splitting and sequential coefficient lagging
   with an identical-checkpoint short replay before altering physical models.

The independent paper-setting audit is on `draft/replication-suite`, commit
`eb538b036a506331ce00982bb659325029dec349`, in
`replication/docs/paper-setup-reaudit-20261019.md`. It records measured 1-D/2-D
costs and separates explicit paper mismatches from unspecified project choices.
