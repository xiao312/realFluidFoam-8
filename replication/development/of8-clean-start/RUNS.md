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

## Diagnostic — bounded clean start on the built executable (`of8-diag-v1`)

`job-diag-v1.sh` is the measurement the build exists for. It accepts only a build
directory whose `status.txt` starts with `BUILT` and whose `exe.sha256` and
`libs.sha256` still verify, copies the frozen 1-D methane/air slab without editing
it, records the hashes of `0`, `constant` and `system`, runs `blockMesh` and
`checkMesh`, solves 1 000 fixed steps of 1e-10 s from `startTime 0` with five
writes, and then measures the saved fields with `metrics.py`: the enthalpy ->
temperature round-trip residual (a temperature inversion appears here), species
positivity with the ideal-gas density closure, and total mass and total sensible
energy at every write. The checker is self-tested in the same allocation, because
a broken checker reports a clean run for a dirty one.

Scope: a startup window, not a flame. A failure of any check is the finding; a pass
is bounded startup evidence and nothing more.

## Defect found in the shared metric module (fixed)

`janaf_h_over_R` evaluated `a1 + a2*T/2 + ... + a6/T`, i.e. `h/(R*T)`, while every caller
treated the result as `h/R`. Every sensible enthalpy, every inversion target and every
energy integral was therefore wrong by a factor of order `T` - about 1000 at 1000 K, and
temperature dependent, so a comparison between two temperatures was wrong by more than a
constant. The synthetic round-trip test could not see it because it built `he` with the
same function.

Fixed in `metrics.py` and `expected_energy.py`; `test_metrics.py` now also pins absolute
anchors (N2 `hs(1000 K)` = 21 463 J/mol = 766.2 kJ/kg within 0.5 percent, N2 `cp(1000 K)`
= 1169 J/(kg K) within 2 percent, CH4 `hf` = -74.87 kJ/mol within 1 percent). All eight
tests pass. Commits `86b6a26`, `f62a5ef`.

## Postprocess of the retained incomplete field (`of8-diag-v1`, 2e-08 s)

Read-only, with the fixed metric, on the one field that job saved before it hit the wall
(**not** a bounded run and **not** a conservation result):

| quantity | value |
| --- | --- |
| cells, dx | 8000, 5e-7 m |
| T range | 298 - 2232.32 K |
| p range | 10.1325 - 10.1966 MPa |
| rho range | 14.76 - 113.03 kg/m3 |
| species sum error | 1.2e-12 |
| ideal-gas rho closure | 9.0e-7 |
| solver `Cp` vs JANAF polynomial | 9.0e-7 |
| inversion round-trip (T -> hs -> T) | 4.1e-16 |
| mass, sensible-energy integral | 0.430678 kg/m2, 7746.82 J/m2 |

The `Cp` agreement is the useful part: the solver's own heat capacity and the independent
JANAF evaluation agree to 1e-6, so the fixed enthalpy polynomial really is the solver's
thermodynamics, and that time zero state is thermodynamically consistent. It says nothing
about conservation over time.

## Bounded clean-start energy diagnostic (`of8-energy-diag-v1`)

`job-energy-diag.sh` runs two 32-cell cases that provably reach `endTime`, generated from
inspectable dictionaries by `prepare_energy_case.py`, both at `startTime 0` with no
carried-over field and with no `endTime` rewriting anywhere in the wrapper:

* `caseA` chemistry off, 300 K | 1200 K step, 1000 fixed 1e-8 s steps to 1e-5 s, four
  writes. Conserved quantity: `sum(rho*he)*V` (sensible enthalpy).
* `caseB` chemistry on, GRI-3.0, uniform 1500 K, 100 steps to 1e-6 s, four writes.
  Conserved quantity: `sum(rho*(ha - p/rho))*V` with `ha = hs + hf`, because
  `sensibleEnthalpy` drops the formation term from the solver's variable.

The stop is verified rather than assumed: `rc = 0`, an `End` marker in the log, the last
`Time =` equal to `endTime`, and the expected number of written time directories; each of
those is recorded per case in `<case>.stop.txt`. Boundary conditions were corrected before
the run to an adiabatic, impermeable, rigid box (`p`, `T`, species `zeroGradient`, `U`
`fixedValue 0`), because a wave-transmissive patch would let mass and energy leave the
domain and the declared conservation statement would have been false. The temperature field
was also given its temperature dimensions. Commit `6f95e1e`.

The built solver does not write its energy variable, so the integral is recomputed from the
written `T` and `Y` through the JANAF table and the source used is recorded per write
(`inversion.energy_source`).

## Energy diagnostic v2 — corrected total-energy accounting (`of8-energy-diag-v2`)

Job `125287686` (1 rank, 2400 s wall, source commit `85eff53`, `overall=0`, 246 s inside the
allocation) reruns exactly the two v1 cases through the corrected `expected_energy.py`, so
the number in the summary and the number the solver conserves are the same quantity and
come from one commit. Both cases again report `rc=0`, an `End` marker, `last Time` equal to
`endTime` and 4 of 4 writes (`caseA.stop.txt`, `caseB.stop.txt`); the in-allocation self-test
ran 10 tests OK.

`caseA` (chemistry off, 300|1200 K, to 1e-5 s), declared quantity `total_energy_J_per_m2`,
`E = sum(rho*(hs + hf - p/rho + 0.5|u|^2))*V` over the closed rigid box:

| t (s) | E (J/m2) | sensible | sum(pV) | K | E rel. first write |
|---|---|---|---|---|---|
| 2.5e-6 | -490.885690 | 632.277890 | 405.4827 | 2.47e-4 | 0 |
| 5e-6 | -490.886707 | 632.424173 | 405.6299 | 1.93e-4 | +2.07e-6 |
| 7.5e-6 | -490.890382 | 632.537439 | 405.7468 | 1.58e-4 | +9.56e-6 |
| 1e-5 | -490.888390 | 632.641544 | 405.8489 | 1.55e-4 | +5.50e-6 |

The sensible enthalpy rises by 5.75e-4 relative while `sum(pV)` rises by 0.366 J/m2: that
rise is pressure work inside the box, not an energy defect, and the total energy moves by
5.5e-6 of |E| with mass constant to 1.1e-12. The offset from the analytic expectation falls
from -2.18e-5 to -1.63e-5 relative over the run, consistent with the initial pressure
equilibration transient (|u| up to 1.96 m/s). `caseB` (chemistry on, 1500 K, to 1e-6 s) is
flat: `E = 754.802093` J/m2 at every write (-4.4e-11 against the first write, -1.37e-6
against the analytic value), mass constant, `T = 1500.00` K, chemistry inactive in 1 us as
expected, `sum(pV)` constant to 1e-5 J/m2. Inversion residuals are at the round-trip floor
(<= 3.8e-16), no cell fails, species closure <= 1.7e-13, ideal-gas density closure 9.0e-7
and solver `Cp` against the independent JANAF evaluation 9.0e-7 on every write.

Limits: 1 us and 10 us startup windows at 1 atm on 32 cells; no flame, no flame speed, no
convergence claim, and the integral is recomputed from `T`, `Y` rather than read from a
solver energy field (the build does not write one).

## Mixing diagnostic v1 — killed before the solve by an unterminated dictionary (`of8-mixing-v1`)

Job `125290253` (1 rank, 3000 s wall, source commit `aee51f6`) generated the 80x40 case and
died in `blockMesh` after 3 s:

```
--> FOAM FATAL IO ERROR:
keyword deltaT is undefined in dictionary ".../mix-80x40/system/controlDict"
```

`prepare_mixing_case.py` wrote `endTime 0.0002`, `deltaT 2e-07` and `writeInterval 5e-05`
without semicolons, so the dictionary parser folded each following keyword into the previous
value and the run had no time controls. Fixed in `b295c0a`: terminators added, a generated
controlDict test asserts every body entry ends in `;`, and `job-mixing.sh` now refuses to
call `blockMesh` if `endTime`, `deltaT` or `writeInterval` is missing or unterminated, so
this failure names the entry instead of surfacing as a mesh tool error. `status.txt` is
`FAILED blockMesh`; no fields were produced and nothing from this attempt is used as a
result. Resubmitted as `of8-mixing-v2`.

## Mixing diagnostic v2 — mesh and dictionaries accepted, inlet patch rejected (`of8-mixing-v2`)

Job `125291239` (1 rank, 3000 s wall, source commit `89bfba9`) is the first mixing attempt with
terminated time controls: `blockMesh` built 3200 cells and `checkMesh` reported `Mesh OK`, so
`b295c0a` fixed the dictionary. The solver then refused the initial field in 0 s:

```
--> FOAM FATAL IO ERROR:
size 3200 is not equal to the given value of 40
file: .../mix-80x40/0/T/boundaryField/inlet from line 3217 to line 3217
```

The inlet is the `x = 0` plane and therefore has `ny = 40` faces; the generator had written
the `nx*ny` cell list as the patch value as well. Fixed in `e1e4eae`: `T`, `U` and every
species write a 40-entry face list for the inlet and keep the cell list for the internal
field, with a test that each boundary list length equals the patch face count. `status.txt`
is `FAILED overall=1`; no time directory was written and nothing here is used as a result.
Resubmitted as `of8-mixing-v3`.

Two dictionary/field defects in a row on this generator, both invisible in a diff read and
both caught only by the solver: this is the practical reason the bounded cases go through a
scheduler allocation before any figure work is attempted.

## Contact advection on the built solver (`of8-advection-v1`, numerics only)

Job `125289267` (1 rank, 3000 s wall, source commit `995bcb6`, `overall=0`, 226 s inside the
allocation, 29 module tests OK) ran the three periodic ideal-gas contact cases. All three
reached `endTime = 0.02 s` with `rc=0`, an `End` marker, `last Time` equal to `endTime` and
4 of 4 writes; the automatic step took 220 steps at `maxCo = 0.11`.

Every case starts at time 0 from a generated `0/` directory and is periodic in x, so there
is no boundary flux at all and mass, momentum and total energy have exact conservation
statements. Measured at the last write:

| case | max\|p-p0\|/p0 | max\|U-u0\| (m/s) | mass drift | momentum drift | total-energy drift | T L2 / jump | T range (K) |
|---|---|---|---|---|---|---|---|
| nx2 (2 cells) | 7.18e-2 | 1.01 | -8.96e-7 | -5.1e-3 | +6.87e-2 | 0.275 | 348 - 3046 |
| nx4 (4 cells) | 6.23e-2 | 1.27 | -8.96e-7 | -6.3e-3 | +5.83e-2 | 0.241 | 376 - 3040 |
| nx6 (6 cells) | 5.37e-2 | 1.26 | -8.96e-7 | -5.3e-3 | +4.58e-2 | 0.239 | 438 - 3035 |

This is a negative result about the numerical scheme, and it is the useful outcome of the
case: the rigid shift the target describes is not reproduced. The contact is not merely
smeared, it heats: the cold side drifts from 300 K to 348/376/438 K, the hot side overshoots
by up to 1.5 percent, pressure oscillates by 5-7 percent of 1 atm despite a Mach number of
0.012, and total energy *rises* by 4.6-6.9 percent while mass is conserved to 9e-7. Momentum
drift is 0.5-0.6 percent. Refining the interface by 3x reduces the pressure excursion by
only 25 percent and the energy drift by 33 percent, so this is not a marginally resolved
contact going away with resolution; it is a property of the discretisation at these settings
(60 cells, central fluxes, `sensibleEnthalpy`, `hePsiThermo` + `perfectGas`).

Consequence for the ladder: nothing downstream of this solver should be read as
energy-conserving until that is understood. The diagnostic exists precisely so that the
1-D flame and counterflow work cannot inherit an unmeasured conservation error, and the
registered `schmitt2020-fig-5` target stays blocked on its real-fluid equation of state
(6 MPa, 1000 -> 100 kg/m3 oxygen cannot be represented by an ideal gas at any temperature).
No figure replication is claimed, and the metric's own self-test (synthetic pure shift,
zero drift, `T` L2 7.8e-12 K) shows the reported drift is the solver's, not the metric's.

## The CH4 sensible-enthalpy "discrepancy" was my arithmetic error

An earlier note carried an unresolved item: `hs_CH4(1000 K) = 2.409 MJ/kg` measured against
an "expected 1.895 MJ/kg", suspected to implicate the JANAF band switch at
`Tcommon = 1000`. There is no such value. NIST Shomate coefficients for 298-1300 K give
2.3797 MJ/kg, so GRI is 1.24 percent high, which is the known inconsistency of the GRI CH4
enthalpy polynomial; O2 agrees with NIST to 0.03 percent and N2 to 0.03 percent at 1000 K.
`test_ch4_and_o2_sensible_enthalpy_anchors` now pins those numbers against the committed GRI
file, so the item is closed by a test rather than by another estimate. No coefficient was
changed.

## Contact-advection cases (`schmitt2020-fig-5`, numerics only)

The registered target asks for oxygen at 6 MPa, `rho` 1000 -> 100 kg/m3, `u = 10 m/s`,
`dx = 0.01 m`, `n_x = 2/4/6`, `t = 20 ms`. The frozen build is `hePsiThermo` +
`perfectGas`: it has no real-fluid equation of state, and 1000 kg/m3 oxygen at 6 MPa is a
supercritical liquid-like state that an ideal gas cannot represent at any temperature.
That is a blocker, recorded in every receipt. `prepare_advection_case.py` builds what the
binary can test: a periodic 1-D ideal-gas domain at 1 atm, `u = 10 m/s`, an error-function
temperature contact 300 K -> 3000 K (density ratio 10, the ratio the target uses) with
width `n_x*dx`, chemistry off, to 20 ms. Periodicity means no boundary flux at all, so
mass, momentum and formation-inclusive total energy are exactly conserved in exact
arithmetic, and the exact solution is a rigid shift of the initial profile.

`job-advection.sh` runs `nx2`, `nx4`, `nx6` and `advection_metrics.py` reports, per write,
the mass/momentum/energy integrals, `max|p-p0|/p0` and `max|U-u0|` (the two quantities the
target plots), density positivity, species closure, `Cp` against the JANAF polynomial and
the L2 error against the shifted initial profile. `test_advection.py` (10 tests) checks the
geometry, the periodicity, the time controls and that the metric recovers the exact answer
on a synthetic pure shift: zero drift, `T` L2 1e-11 K.

## Corrections after the 08:00 owner inspection (`run-audit`, 2026-10-23 08:30 CST)

Read-only audit of retained fields, no rerun. Three earlier statements were wrong and are
withdrawn here rather than edited out of the record above.

**1. The solver does write its conserved energy variable.** `createFields.H` declares
`AUTO_WRITE` `volScalarField HE(thermo.he())` and `realFluidReactingFoam.C` refreshes it
every step, so `HE` is present in every written time directory of `of8-advection-v1` and
`of8-energy-diag-v2`. `run-audit/audit3.py` compares the solver's `HE` with
`sum_i Y_i hs_i(T)` from the same JANAF table the solver was built with:

| case | writes | max cell `|HE-hs|/|hs|` | `rho*HE` vs `rho*hs` (relative) |
| --- | --- | --- | --- |
| advection nx2 | 0.005, 0.02 s | 8.96e-7 | 1.0e-6 |
| energy caseA | 2.5e-6, 1e-5 s | 8.96e-7 | 1.0e-6 |
| energy caseB | 2.5e-7, 1e-6 s | 8.96e-7 | 1.0e-6 |

The `T -> he -> T` inversion reported above is therefore circular and is *not* an
independent verification of anything; the residual `3.8e-16` only says the bisection
inverts its own table. The statement that the build exposes no energy field is wrong.
What survives is weaker and still useful: the integral `E = sum rho*(hs + hf - p/rho + |u|^2/2) V`
computed from `T`, `Y`, `p`, `U` agrees with the same integral computed from the solver's
own `HE` to about 1e-6 relative in all three cases, so the reported drifts are properties
of the budget built from solver fields and not of the reconstruction. The drift itself
(energy caseA `+5.50e-6`, advection nx2 `+6.87e-2` of `E` over the run) remains an open
diagnostic: it is not established as a solver defect, a diffusion effect or a
discretisation error.

**2. The contact-advection cases do not test mesh refinement.** All three cases have 60
cells over the same 0.6 m domain; `nx2/4/6` is the number of cells used to *represent the
initial interface width*, not the cell count. The statement "3x interface refinement removes
only ~25 percent of the pressure excursion ... so it is a property of the discretisation,
not a resolution artefact" is withdrawn: interface-width refinement at fixed cell count says
nothing about mesh convergence. The measured values stay as diagnostics (cold side 300 K ->
348/376/438 K, pressure excursion 5.4-7.2 percent, `T` L2 0.275/0.241/0.239), and the run is
described as a single-resolution, three-interface-width measurement.

**3. The configured physical model is not pure advection, and the seam is a second
interface.** `EEqn.H` keeps conduction (`laplacian(kappa,T)`) and species-enthalpy diffusion,
`phi` on the periodic patch is shared between the first and last cell, and `p` is a
thermodynamic pressure that the energy equation does not constrain in a closed box. A rigid
temperature shift is an inviscid/advection reference solution only; it is not the exact
solution of the model that was run. Thermal diffusion and the periodic seam both smooth the
contact, so part of the observed cold-side heating is physical for this configuration. The
remaining part (energy budget drift, momentum drift `-5.3e-3` to `-6.3e-3`, mass conserved to
`8.96e-7`) is unresolved.

**4. Real-fluid equations of state are compiled into this build.** The frozen source tree
`runs/of8-build-v5/src-tree` contains `src/thermophysicalModels/specie/equationOfState/
{PengRobinson,PengRobinsonGas,soaveRedlichKwong,...}` and
`psiReactionThermo/psiReactionThermos.C` registers `forSRKchungTakaGases`,
`forPRchungTakaGases`, `forSRKchungKineticGases`, `forPRchungKineticGases` and
`forIdKineticGases`; `lib/libfluidThermophysicalModels.so` carries the `PengRobinson`
symbols. The earlier "the frozen build has no real-fluid equation of state" claim is
withdrawn. The *case* selected `hePsiThermo` + `perfectGas`/`janaf`, which is a dictionary
choice, not a capability limit. What is still true: an ideal-gas density of 1000 kg/m3 at
6 MPa is physically unsuitable for the dense oxygen state in `schmitt2020-fig-5`, and the
`schmitt2020-fig-18-g2` deviations remain explicit.

**5. Pressure entries are target-specific.** `5.61 MPa` belongs to the Müller
flamelet/property targets and `5.59 MPa` to the Singla/Candel G2 targets; the two are not a
transcription error and the earlier "reconcile 5.59 vs 5.61" note is withdrawn.


## Mixing diagnostic v6 (`of8-mixing-v6`, job `125295010`) — solver aborted in chemistry construction

The build was accepted, the source frozen from `9693472`, `blockMesh` built 3200 cells,
`checkMesh` passed, the static gate passed (3 species, both patches 40 faces) and the
self-test passed — then the solver aborted while constructing the chemistry model:

```
FOAM FATAL ERROR: Attempt to return primitive entry ITstream : .../chemistryProperties/reactions,
    line 10 ... primitiveEntry 'reactions' comprises ... the punctuation token '(' ... as a sub-dictionary
```

`ReactionList` calls `dict.subDict("reactions")`, so an empty reaction list must still be a
dictionary block. The generator wrote `reactions ();`, a primitive token list, and the gate
did not check that form because it only compared the species a reaction list names against
the thermo table (an empty list names none). Fixed in `777c013`: the generator writes
`reactions { }`, `admission.reaction_list_form()` rejects the token-list form with the job
id in its message, and the negative control is in the tests.

## Mixing diagnostic v7 (`of8-mixing-v7`, job `125296683`) — solved, then lost its metrics; the cold stream is outside the JANAF range

`rc_solve=0`, 1000 steps, `t = 2e-4 s`, 4/4 writes, 155 s solver time, `max Co = 4.6e-3`,
`T` 200–288 K, continuity cumulative `1.9e-8`, `checkMesh` clean. Two separate problems:

1. **The metric step never ran.** The freeze list omitted `metrics.py`, which
   `mixing_metrics.py` imports, so the post-solve step died with `ModuleNotFoundError`;
   `mix.metrics.json` does not exist in the run directory. `metrics.py` is now frozen and
   `freeze_source.sh` refuses to hand a run an import closure it does not cover
   (`admission.import_closure`), tested with the exact failure. The measurements were later
   produced from the retained fields by the corrected scripts and are recorded with that
   provenance; they are *not* a run-time artefact of `125296683`.
2. **The 100 K oxidiser cannot be represented by this thermophysics.** The solver log
   carries 1,703,400 `janafThermo ... out of temperature range 200 -> 3500; T = 100`
   warnings and the cold half of the domain is written at exactly 200.0 K, i.e. the
   thermo floor, not the inlet temperature. Extending a JANAF fit below 200 K is not
   physical, so this case is a *numerical solver smoke test only*: it exercises clean
   start-up, mass-flux-matched inflow, four writes and a verified stop, and it says nothing
   about cryogenic oxygen mixing or about `schmitt2020-fig-18-g2`. No G2 claim is made here.

The measured mixing quantities are retained as diagnostics; the mass and momentum
imbalances at this early transient (`1.15e-6` vs `1.12e-6` kg per interval, momentum
imbalance ≈ 1 because the inlet and outlet pressure terms cancel to 1e-5 of their own
size) show the outlet-flux estimate is not closed at this resolution and must not be read
as a validation.
