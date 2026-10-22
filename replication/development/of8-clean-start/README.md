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
- `job-smoke.sh` — `blockMesh`, `checkMesh`, then the solver for 100 ns
  (1 000 steps of 1e-10 s, serial). Keeps the generated case immutable by copying
  it into the run directory, records input and field hashes, and rewrites
  `endTime` to the last written time if the allocation nears its wall so the run
  stops and writes cleanly instead of being killed.
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
