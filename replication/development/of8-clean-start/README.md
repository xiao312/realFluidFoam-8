# OF8 clean-start diagnostic (liang-8a Case1, ideal methane/air)

Status: **diagnostic in progress**. This module asks a narrower question than the
publication ladder and must not be read as a result for any ladder target.

## Question

Does the exact committed tree at `b778d884` build `realFluidReactingFoam` with the
registered OF8 profile, and does that executable, started at original time zero on
the versioned `phi110` premixed case (phi 1.10, 10.1325 MPa, `Tu` 298 K, GRI-3.0
`ideal.yaml`), produce a finite, mass-fraction-normalised, thermodynamically
consistent 100 ns startup?

Explicit non-goals:

- no laminar flame speed and no comparison to any Liang figure value;
- no convergence, mesh- or domain-independence statement;
- no MPI qualification (the payload is one rank);
- no statement about the payload's 8-rank or `full`-mode siblings;
- no fuel/temperature sensitivity sweep, no conductivity-model comparison.

The historical instantaneous-source flame speed stays discarded; nothing here
revives it, and every run starts from `startTime 0` with the generated initial
field (`restart: false`).

## Isolation

Branch `draft/of8-clean-start`, forked from the frozen r3 candidate
`b778d884afaceb2454957c5ddb2288a3bd24af84` in a separate worktree. The r3
submission (`candidate.bundle 700bc22f…`) is untouched, and nothing here is merged
into `campaign/forge-20261021` while review `ladder-r3` is pending.

## Inputs (frozen before the jobs)

| item | identity |
| --- | --- |
| source commit | `b778d884afaceb2454957c5ddb2288a3bd24af84` |
| source archive | `src.tar.gz`, 13 076 480 B, 2 451 members, sha256 `04e60b6f…3d094ec` |
| payload manifest | `/references/science-inputs-0400/methane-phi/phi110/manifest.json` |
| mechanism | `author-gri30.yaml`, sha256 `c6e72c25…` |
| thermo species input | sha256 `60235162a165af5f78c05455e38342c0ca2717bb928929552222801df7ef0722` |
| case generator | `ideal-baseline/prepare.py` -> `premixed-paper/prepare.py` (key `phi110-equilibrium`) |
| generated case receipt | `of8-clean-start-case-receipt-v1`, sha256 `fb421bc5…` (72 files) |

`prepare_case.py` calls the committed generator and then adapts **only** three
controller entries, each with a recorded reason in the receipt:
`application` -> `realFluidReactingFoam`, `endTime` 1e-09 -> 1e-7 s,
`writeInterval` 1e-09 -> 2e-8 s. `constant/*`, `0/*`, `blockMeshDict`, schemes and
solution are unedited; `startTime` stays 0, `deltaT` stays 1e-10 s and
`adjustTimeStep` stays `no`.

## Payloads

- `job-build.sh` — exact-source build. Verifies the archive hash against
  `snapshot.json`, extracts, hashes every member, logs `wmake -show-cxx`,
  `-show-compile` and `-show-link`, builds `src/Allwmake` libraries with `-j 1`,
  then `wmake applications/solvers/realFluidReactingFoam`, and records
  `libs.sha256`, `exe.sha256`, `ldd.txt`, `status.txt`, `rc.txt`.
  Submitted as job `125204321`, 1 rank, 7200 s, environment `openfoam8`
  (receipt `script_sha256 f1ef5c96…`, i.e. the adapter-composed script; the
  worktree file hashes to `eedf15b8…`).
- `job-build-v2.sh` — the same build with a proven toolchain configuration in front
  of it (see `RUNS.md`), sha256 `3e24e40e…`.
- `job-build-v5.sh` — the build that succeeds (see **Build record**). Verifies
  `members.sha256` on the resumed tree, pre-builds `thermophysicalModels/chemistryModel`
  serially at `-j 1`, then runs `src/Allwmake -j 2` and the solver link under a
  `BUILD_BUDGET`, writing `status.txt`, `libraries.log`, `chemistry-serial.log`,
  `libs.sha256`, `exe.sha256`, `ldd.txt`, `solver-help.txt`, `compiler.sha256`,
  `toolchain-identity.txt` and `compile-config.txt`.
- `job-smoke.sh` — `blockMesh`, `checkMesh`, then the solver for 100 ns
  (1 000 steps of 1e-10 s, serial). Keeps the generated case immutable by copying
  it into the run directory, records input and field hashes, and rewrites
  `endTime` to the last written time if the allocation nears its wall so the run
  stops and writes cleanly instead of being killed.
- `job-diag-v1.sh` — the bounded clean-start diagnostic on the built executable:
  verifies `exe.sha256`/`libs.sha256` against the build directory, copies the
  frozen slab case and hashes its bytes, runs `blockMesh`/`checkMesh`, solves
  1 000 fixed 1e-10 s steps from time 0 with five writes, then runs `metrics.py`
  on the written fields and self-tests `test_metrics.py` in the same allocation.
  A nonzero solver exit, an inversion residual above the enthalpy round-trip
  floor, a negative mass fraction or a drifting total mass/energy is recorded as
  the result; no flame speed, convergence or acceptance is claimed.
- `metrics.py` — serial post-processing, stdlib only.
- `test_metrics.py` — 7 unit tests on a synthetic slab case (no solver, no network).

### Measured platform facts that shape the payloads

Probe job `125203749` (600 s, TIMEOUT) established, after almost the whole
allocation was spent in SIF sandbox conversion (`squashfuse`, `fuse2fs` and
`gocryptfs` are absent): `WM_PROJECT_DIR=/opt/openfoam8`, OF version 8,
g++ 11.2.0, one CPU, `python3` at `/opt/python/bin/python3`, **no git**,
`FOAM_USER_LIBBIN` preset to `/workspace/build/lib` (overridden), and no
`realFluidReactingFoam` on `PATH` (it has to be built). Timing is separated in
`/workspace/forge-out/runs/of8-probe/timing.json`: 578 s startup/conversion, 1 s
payload, 24 s cleanup — therefore ~6 600 s of payload at most inside a 7 200 s
allocation, and the build gets its own allocation.

## Build record

Job `125270465` (`of8-build-v5`, 4 ranks, 4 GiB, 7 200 s, environment `openfoam8`,
submitted 2026-10-23T01:27:50) produced a complete solver from the frozen archive:

- compile configuration `wrapper-isystem` (the probe that chose it is retained in
  `probe/attempts.txt`); compiler `/opt/gcc-11.2.0/bin/g++` sha256 `f1f617fe…`,
  `gcc` sha256 `2ab85310…`, wrapper sha256 `32cd1f00…`;
- serial pre-build of `thermophysicalModels/chemistryModel` at `-j 1`, rc = 0, 645 log
  lines (17:39:41Z to 17:56:11Z);
- `src/Allwmake -j 2`, rc = 0 in 1 838 s, 165 compile lines, **15 libraries** in
  `lib/` — including `libchemistryModel.so` `723a84d9…`,
  `libcombustionModels.so` `1118a1e9…`, `libreactionThermophysicalModels.so`
  `32532fc9…` and `librhoReactionThermophysicalTransportModels.so` `10986b8e…`;
- the solver link, rc = 0 in 43 s, produced `bin/realFluidReactingFoam` sha256
  `a1a4f6b8db32ebbf2b5922f29fd6464775a14970d2efef999e40b80bbf85d4f6`, with 45 `ldd`
  lines and 37 lines of `-help`;
- payload 1 966 s inside the allocation, against 578 s of SIF sandbox conversion.

**What blocked it before, and why the fix was a schedule rather than a rewrite.** Attempt
`of8-build-v4` (job `125267677`) died after 848 s with `g++: fatal error: Killed signal
terminated program cc1plus` while five libraries were compiling at `-j 3`: the 4 GiB job
cap, not a source error. Attempt 5 lowered the parallelism to `-j 2` and compiled the
heaviest templated translation unit (`chemistryModel`) alone first, then resumed the rest.
The OOM-killed unit is now built, so the mitigation is confirmed on the failing target and
not only in principle.

**Provenance limit, unchanged.** `members.sha256` proves the source members are the ones in
the archive; it says nothing about the object files copied in from the earlier tree, and
the five libraries that already existed are copied rather than rebuilt. `libs.sha256` and
`exe.sha256` record what the job actually produced, and `job-diag-v1.sh` re-verifies both
before running anything. A build from an empty tree at `-j 2` has not been run.

## Measurements on the run

`metrics.py` reads only saved fields plus the committed `thermo.inputData_GRI` and
reports, per saved time:

1. geometry reconstructed from `constant/polyMesh/points` (cell count, `dx`, length);
2. finiteness and ranges of `T`, `p`, `rho`, `he`, `U`;
3. mass fractions: per-species range, `sum(Y) - 1`, and the ideal-gas closure
   `rho` versus `p M_bar / (R T)` using the committed `molWeight` values;
4. temperature recovered from the stored sensible enthalpy by bisection on the
   committed janaf bands, and the relative residual against the stored `T`;
5. total mass and total sensible enthalpy per unit area at each time, and their
   change relative to the first saved time;
6. a density-deficit weighted front position (unburned reference = median of the
   first 5 % of cells, deficit clipped at zero), the peak-gradient position, and
   the front motion relative to the gas.

Not available from this solver and therefore **not claimed**: in-situ flame-speed
diagnostics (`flameSpeedProperties` exists in the generator but no solver in this
tree includes `FlameSpeedDiagnostics.H`), and `RR`/`Qdot` sign-and-unit checks from
saved fields. Any statement about those must come from a separately instrumented
build and be labelled as such.

## Declared limits

- The generated case is shaped for the family's 8-rank layout, and
  `replication/development/ideal-baseline/check.py` requires `processor*` output
  and `inlet-densities.csv`; it is therefore not runnable unchanged at one rank.
  The serial checks above are this module's own and are labelled serial-adapted.
- The module-level `unittest` discovery in `ideal-baseline` reports two errors
  natively because `history.py` imports `numpy`, which is not installed here; that
  is an environment limit, not a measured pass.
- 100 ns of physical time is startup evidence only: the flame has propagated a
  small fraction of the 4 mm domain at these conditions.
