# Ideal flame diagnosis — 19 October 2026

The native ideal-gas chemistry agrees closely with CVODE on eight independent
flame states. The species-enthalpy cache fails a runtime refresh check. This is a
confirmed energy-transport defect; its contribution to the low flame speed is not
measured yet. Production solver and library builds remain unchanged.

## Chemistry evidence

Job 124897206 used source c5e1463, library build 124657926 and the pinned stock
OF8 container. Both executables were built and linked separately. Native
idKineticStandard and stock standard chemistry produced byte-identical CSV files
at both tolerance settings. All four probe processes completed successfully.

The frozen phi=1.10 states span approximately 498–2100 K and include peak heat
release. Every test uses 100 atm. Cantera 3.2 CVODE integrates both physical CP/CV
reactors and a separate control with OpenFOAM's concentration/Cp-temperature
ODE. Comparing different ODE formulations would conflate coupling and integration.

| Check against the matching CVODE ODE | Largest relative L1 mass-source difference |
| --- | ---: |
| Instantaneous, reference pressures matched | 0.00680% |
| 50 ns, SEULEX absTol=1e-8 / relTol=1e-6 | 0.01793% |
| 50 ns, SEULEX absTol=1e-12 / relTol=1e-8 | 0.00493% |

The maximum absolute mass-fraction difference after 50 ns is 1.67e-8 at current
tolerances. Differences at trace/near-equilibrium rates require separate care.
These eight states do not prove chemistry independence for every transient state,
but provide no evidence of an integration discrepancy large enough to explain the
earlier roughly 10% phi=1.10 flame-speed gap on their own. At 161.4 us, the
original case has risen to 6.968 cm/s (temperature) and 7.091 cm/s (OH), versus
7.467 cm/s in Cantera: incomplete relaxation is still a competing explanation.

The initial instantaneous source discrepancy reached 1.083% with the original
Cantera mechanism. It largely disappears when its NASA reference pressure is set
to OpenFOAM's 100000 Pa instead of 101325 Pa. The physical test pressure is still
10132500 Pa. This diagnostic does not change the saved Cantera flame curve.
Remaining differences include molecular weights and gas-constant conventions.

An earlier stock test with absTol=1e-14 / relTol=1e-10 exceeded the ODE step limit
(job 124896763). That failed attempt is retained; tighter tolerances are not
assumed to be free of robustness/cost penalties.

## Confirmed cache defect

The native probe increased temperature by 100 K through the enthalpy field and
called thermo.correct(). All 53 species at all eight states retained their old
thermo.hei() values: 424/424 unchanged. Direct composition.HE(i,p,T) evaluated at
the new state disagreed with that cache. For methane the absolute discrepancy is
309–640 kJ/kg; for nitrogen it is 107–129 kJ/kg over these states.

Source inspection agrees with the experiment: heThermo constructors fill heList_;
hei() returns heList_[i]. hePsiThermo::correct()/calculate() do not refresh it. The
solver's timestep-end `hei[i] = thermo.hei(i)` copies the stored values. EEqn uses
these fields in both species-enthalpy diffusion corrections. A restart constructs
a new cache at the restart temperature, which can also introduce restart-history
sensitivity.

The failing runtime check is reproducible with:

```
python replication/development/solver-comparison/analyze.py SNAPSHOT CVODE_REFERENCE result.json --assert-cache-refresh
```

Expected result on the unchanged library: nonzero exit and
`FAIL: species enthalpy does not refresh after thermo.correct()`.
Static lineage check: the downloaded OF6 solver snapshot 3cc6aaca and OF6
thermophysical-library snapshot 61f86014 contain the same pattern: heList_ is
filled by init() during construction, hei() returns it, and hePsiThermo::correct()
calls calculate() without refreshing the species cache. This suggests an upstream
lineage issue rather than a new solver-development regression. No OF6 runtime
probe was run, and this does not identify the private code used for paper results.

The next isolated physics change should refresh species enthalpy at the current
pressure and temperature, then rerun phi=1.10 with all other settings unchanged.
Do not combine it with chemistry tolerance, transport, or pressure-reference edits.

## Cross-solver runs

Stock reactingFoam job 124896761 is running from c18481d. It has the same 4 mm,
8000-cell mesh, initial species/T slab, zero velocity, pressure boundaries and
50 ns timestep ceiling. It uses its native Fourier/unity-Lewis transport, so this
is a full-solver comparison, not a chemistry-only control.

DeepFlame source is 7cb3294b275525cb8829ada3d3fbc067ab9323eb, with OF7 and native
Cantera 2.6. Build job 124897210 failed at linking because the compiler used the old string
ABI, whereas the selected OF7 and Cantera libraries use the new ABI. Dependent
flame job 124897805 was cancelled automatically. Job 124898271 then caught an ABI
preflight failure: inherited CPLUS_INCLUDE_PATH forced old compiler headers even
with the ABI macro set. Build 124898712 clears these inherited include paths and
uses GCC 11 explicitly (source d015691). Its ABI preflight passed, but final linking could not find libmpi.so.40.
The site module retained the default HPC-X compiler wrapper on PATH. Clean build
124899720 selects the installed OF7 OpenMPI 4.1.5 for headers, linking and runtime
(source 4c9adb7); dependent flame job is 124899733. CPU/CVODE is enabled;
DNN and GPU chemistry are disabled. DeepFlame uses an isothermal CV chemistry
substep while the native OpenFOAM chemistry includes a temperature equation.

The first setup attempts failed before simulation: compute-node package DNS,
OpenFOAM shell initialization under errexit, OF8 sampled-set naming, and CRLF
upstream shell files. The offline dependency bundle, corrected wrappers and
per-version sampler retain those failures in separate jobs. No existing baseline
job was cancelled or edited.

Raw results are in the project state directory `solver-comparison-20261019` and
SCNet `jobs/JOB_ID`. The adjacent JSON records quantitative evidence and hashes.
The current comparison paragraph in Lark was replaced in place; existing paper
images were retained.

## Case-sensitive source verification

DeepFlame is exported directly from Git objects with git archive and extracted on
Linux. The Windows sparse working tree is not a build input. A read-only audit of
build 124898712 checked all 554 archived files and every path component. It passed:
`src/dfCombustionModels/CombustionModel` and `combustionModel` remain distinct.
The native cache files heThermo.C and psiThermo/hePsiThermo.C also match Git
objects at build source b1153ea9, byte for byte. The cache defect is present in the
pinned source; it is not a changed Windows copy.
Only four documented CRLF-to-LF shell/configuration entry conversions differ from
the archive. No C/C++ content differences were found. A comparison of full file
paths alone would have missed this directory collision. Archive SHA256 and the
audit are recorded in the adjacent JSON; future wrappers enforce both checks.

The stock profile adapter reuses the existing trackingCore. At 47.43 us, its last
5-us medians are 6.602/6.597 cm/s for the left/right temperature markers and
5.880/5.872 cm/s for OH. Marker disagreement shows that these are early transient
observations. They must not be compared as matched-age values with the native
161-us observation. Both histories need the same physical-time window.

## Matched-age observation

A later stable stock snapshot covers 55.43-74.93 us. The same trackingCore processes
its sampled T, U, rho and OH. The native in-situ output supplies the primary markers.
Over 69.93-74.93 us, medians pool both sides (22 valid samples for each entry):

| Solver | Temperature marker, cm/s | OH marker, cm/s |
| --- | ---: | ---: |
| Native ideal solver | 6.470 | 6.409 |
| Stock OF8 reactingFoam | 6.576 | 6.285 |

Both remain below Cantera's 7.467 cm/s. Native uses species-dependent transport;
stock uses unity-Lewis transport, and its fields pass through line sampling. This
is a full-solver diagnostic, not an isolated test of chemistry or transport.
At 177.92 us the original native case has risen to 7.048 cm/s (temperature) and
7.167 cm/s (OH), about 5.6% and 4.0% below Cantera. Continued relaxation is visible;
no steady point is accepted. The confirmed cache defect still requires an isolated
fixed-versus-original run before assigning it any flame-speed error.
