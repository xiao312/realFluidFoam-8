# Payload attempts and measured outcomes

Every entry is a real scheduler allocation. Status words below are scheduler or
compiler outcomes, not CFD quality judgements.

## Attempt 0 — platform probe (job `125203749`, TIMEOUT)

Purpose: learn the OF8 image before spending a build allocation. The 600 s wall was
consumed by SIF sandbox conversion (578 s) plus a 1 s payload, so the job was killed
after the payload had already printed its facts; cleanup took 24 s. Timing is
separated in `/workspace/forge-out/runs/of8-probe/timing.json`. It established the
paths, compiler, one CPU, missing `git`, the preset `FOAM_USER_LIBBIN` and the
absence of `realFluidReactingFoam` from `PATH`.

## Attempt 1 — exact-source build (job `125204321`, FAILED)

Payload `job-build.sh` (worktree file sha256 `eedf15b8…`, adapter-composed script
`f1ef5c96…`), 1 rank, 7200 s wall. Frozen archive hash matched, 1 865 members hashed,
`wmake` and the OF8 headers were found. The first translation unit failed:

```
g++ ... -c ODESolvers/ODESolver/ODESolver.C
/usr/include/features.h:461:12: fatal error: sys/cdefs.h: No such file or directory
```

So the compile step could not resolve the system C library headers; this is a
toolchain/image defect, not a source defect. `wmake -show-cxx`, `-show-compile` and
`-show-link` are **not supported options in OpenFOAM 8** (the original
`unknown option` output is retained in `build.log`), so the actual flags were read
from the compile command instead. `status.txt` = `FAILED libraries rc=2`,
`libs.sha256` and `exe.sha256` were never created.

Diagnosis: the image compiler is `/opt/gcc-11.2.0`, while `/usr/include/features.h`
belongs to a glibc whose headers live in a multiarch directory
(`/usr/include/x86_64-linux-gnu`). Unless that directory is on the include path, no
C++ translation unit in the image can compile — including OpenFOAM's own reuse of
`-I/opt/openfoam8/src/OpenFOAM/lnInclude`.

## Attempt 2 — same source, proven toolchain configuration (`of8-build-v2`, submitted)

Payload `job-build-v2.sh` (sha256 `3e24e40e…`) repeats the frozen-source verification, then (a) logs
`g++ -dumpmachine`, the compiler search dirs, the default include search, the
existence of each candidate header directory and the `wmake` `linux64Gcc` `c`/`c++`
rule files, (b) tries three compile configurations on a one-file test
(`default`, `CPLUS_INCLUDE_PATH=/usr/include/x86_64-linux-gnu`,
`CPATH=/usr/include/x86_64-linux-gnu`), and (c) only builds if one of them compiles
`#include <cstdint>`. If none does, the job stops with `FAILED toolchain-headers`
instead of burning the allocation. Objects are written inside the run tree, so a
later allocation can continue an interrupted build incrementally.

This is one retry with a changed, measured hypothesis — not a blind repetition of
attempt 1, and not a second same-signature failure since the signature was resolved
before resubmitting.

## Attempt 2 result — the probe itself was broken (`125205324`, FAILED at 02:01:31Z)

The payload reached the build (`host a02r1n18`, archive sha256 `04e60b6f…` matched,
1865 member hashes, `WM_PROJECT_DIR=/opt/openfoam8`) and then failed on the very
first translation unit with the same
`/usr/include/features.h:461: fatal error: sys/cdefs.h: No such file or directory`.

Its own probe had already recorded every configuration as `OK`, including
`default`, so it built with `default`. Reading `probe/attempts.txt` and the wrapper
shows why: the default probe was written

    try_config "default" true   ->   env true g++ -std=c++11 -O2 -c probe/t.cpp ...

which executes `true` with the compiler arguments, never the compiler. `default`
therefore "passed" without compiling anything, was chosen first, and every
configuration that might have worked (`CPLUS_INCLUDE_PATH`, `CPATH`, discovered
header dir, `/usr/bin/g++`) was skipped. The probe TU was also too weak: it included
only `<cstdint>`/`<cstdio>` and was compiled without the wmake flags, so it was not
the include chain that fails in the real build.

## Attempt 3 — faithful probe, config-driven (`of8-build-v3`)

Payload `job-build-v3.sh` (sha256 `8afea6f7…`). Changes, all derived from the
attempt-2 evidence:

* the probe TU is the *real* failure: `#include <cstdint>` plus OpenFOAM's public
  `bool.H` (which is what pulled `features.h` in), compiled with the same
  `-Dlinux64 -DWM_ARCH_OPTION=64 -DWM_DP -DWM_LABEL_SIZE=32` and
  `-I/opt/openfoam8/src/OpenFOAM/lnInclude -I/opt/openfoam8/src/OSspecific/POSIX/lnInclude`
  that `wmake` uses;
* the `default` case is a plain compile with no environment overrides — no `env true`
  placeholder, so it cannot pass by accident;
* configurations are tried in the order the registry documents for this image:
  a `g++` shim adding `-isystem /usr/include/x86_64-linux-gnu
  -B/usr/lib/x86_64-linux-gnu/ -L/usr/lib/x86_64-linux-gnu`, then
  `CPLUS_INCLUDE_PATH`, then `CPATH`, then shim+`CPLUS_INCLUDE_PATH`, then `default`;
* the chosen configuration, the resolved `g++` and the exported variables are written
  to `compile-config.txt`, and `status.txt` names the configuration in every outcome;
* the build still stops before `Allwmake` with `FAILED toolchain-headers` if no
  configuration compiles the faithful probe.

## Attempt 3 — header preflight only (job `125251689`, COMPLETE rc=0)

`job-build-v3.sh` with the repaired probe: the faithful probe (OF8 `bool.H` plus wmake's
`-D/-I` set) compiled under the `wrapper-isystem` configuration, so this image can host
the build. The allocation was sized for a preflight, not a build, so the payload stopped
after recording `probe/attempts.txt` and `compile-config.txt`. Nothing was compiled at
OpenFOAM scale and no executable exists from this attempt.

## Attempt 4 — complete solver, parallel, hash-identified (`of8-build-v4`)

`job-build-v4.sh`. Differences from attempt 2 that matter scientifically and for evidence:
`src/Allwmake` and `wmake` run with `-j 3` instead of `-j 1` (468 translation units cannot
fit a 7200 s wall serially once the 578 s image conversion and the 20-25 min cleanup tail
are subtracted); a payload budget stops between the library and solver stages rather than
letting the scheduler kill a half-built tree with no status file; and compiler identity
(`compiler.sha256` over the g++/gcc/cc1plus binaries actually invoked, `toolchain-identity.txt`
with the `-v` banner and linker/libc versions) is retained next to `libs.sha256` and
`exe.sha256`. The frozen archive is the same bytes as attempt 1, verified against
`snapshot.json` inside the job before anything is compiled.

## Attempt 5 — resumed tree, serial pre-build of the unit that was OOM-killed (`of8-build-v5`)

Attempt 4 produced five libraries (`libODE`, `libspecie`, `libthermophysicalProperties`,
`libfluidThermophysicalModels`, `libreactionThermophysicalModels`) in 848 s and then died
with

```
g++: fatal error: Killed signal terminated program cc1plus
make: *** [.../chemistrySolver/EulerImplicit/EulerImplicitChemistrySolvers.o] Error 1
trap rc=2 elapsed=848s
```

which is a kernel kill of a compiler process, not a compile error: `-j 3` held three
`cc1plus` processes resident inside a 4 GiB job (one GiB per rank). The blocker is
therefore specific and measurable — parallel translation units of the templated chemistry
and transport libraries do not fit the allocation's memory — and the response is specific
too:

* `BUILD_JOBS` defaults to 2, and `thermophysicalModels/chemistryModel` is compiled first
  and alone (`wmake -j 1`) so the heaviest units never run side by side;
* the tree is resumed from attempt 4 (`RESUME_TREE`) instead of being re-extracted, so the
  848 s already spent is kept. A resumed tree is only accepted after
  `sha256sum -c members.sha256` proves that every source member recorded by the earlier
  attempt still hashes to the same value; the cache contributes objects, not source bytes.

No source, no flag and no compiler changed between attempts 4 and 5.
