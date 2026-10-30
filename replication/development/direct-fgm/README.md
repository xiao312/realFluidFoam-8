# Direct FGM development checkpoint

The current branch is `draft/direct-fgm-20261031`, based on
`a73a6caa7b54ca32e112cd79adac1f7d36d875f6`. It combines the reacting solver,
physical flamelet/table tools and comparison evaluators. This is a source
checkpoint; reacting MASCOTTE agreement and scientific acceptance remain pending.

## Current progression

| Stage | Retained evidence | Remaining qualification |
| --- | --- | --- |
| Thermophysical library | Full fork built; SRK O2 density at 85 K/5.61 MPa is 1181.227 kg/m3 versus the paper's 1177.2. Compiled PR Cp-Cv repair passed four pure-fluid regressions in job 126415466. | PR density discrepancy and low-temperature NASA extrapolation remain. Pure-fluid checks do not validate reacting mixtures. |
| Physical CH4/O2 flamelets | Müller Fig. 2 temperature RMS difference 23.28 K; at strain 575000/s, peak T is 3126.0 K versus about 3126.7 K in Fig. 3. | Strict steady-residual criteria failed; high-strain extinction still occurs earlier. Approximate matches support further diagnostics, not acceptance. |
| Physical table | Cold 129-node transient through 1 ms; 66 training/16 held-out profiles; maximum held-out T error 20.1 K and progress-source error 1.87% of global peak. | Ideal-gas chemistry, one trajectory family and two coordinates; no enthalpy-coordinate/PDF closure. |
| Source/energy coupling | Job 126421653 passed 12 fresh 0D/1D cases and 14 timestep/outer-iteration comparisons. Maximum energy error/chemical change 0.1632%; mass drift 1.15e-13. | Larger timestep and full-SRK source-on coupling require separate evidence. The explicit-source control failed its energy criterion. |
| Cost reduction | Job 126418954 gave identical six property/inversion pairs and source-off full-SRK CFD results. Thermo corrections ran 4.03–4.63 times faster. | Source-on equivalence and larger-flow cost remain separate checks. |
| Reacting G2 | Job 126424490 was admitted with exact-source build, source-on parity and a fresh 100 microsecond pilot behind mesh/coupling checks. | Admission is not execution. Developed profiles and morphology are not yet demonstrated. |

Independent DOP853 analysis agrees with all six uniform CFD histories within
7.13e-10 of the progress-variable span. Its Windows environment is NumPy
2.2.6/SciPy 1.15.3; the allocated Linux repetition is separate. Both the loose
reference's failed self-refinement and the tighter result are retained. No CFD
acceptance limit was changed. Useful approximate agreement can justify the next
independent experiment while failed criteria remain failed.

## Code and execution boundaries

The [solver](../../../applications/solvers/reactingFoamSolveZ/README.md) transports
raw `C=Y_CO2+Y_CO` and mixture fraction Z. Optional source-stage integration
preserves oldTime, repeats the second half from each fresh transport solve,
and uses absolute Ha without adding formation heat twice. The
[table model](../../../src/combustionModels/fgmTable/README.md) owns interpolation
and coverage events. Default explicit integration remains available.

The [flamelet module](../../fgm/direct-flamelet/README.md) uses pinned Spitfire
revision `735711dc4a426cc7504747d732f2e7fcc3db2c23`. Its retained fixes address
interior-node energy indexing and cryogenic reverse-rate overflow. Excluded
multivalued progress states and numerical-species projections are reported.
The [source-coupling checks](../../validation/fgm-source-split/README.md) exercise
actual OF8 equations; their independent reference does not call the C++ source
integrator. Python/SciPy never enter the CFD solver.

The [diffusivity optimization](../../validation/realfluid-g2-thermo/diffusion-performance/README.md)
is opt-in and restricted to the qualified FGM/laminar/Fourier/absolute-Ha path;
attempted access to skipped Dimix fields fails. Executing-thermo h(p,T,Y) is
checked after each energy inversion. Successful summaries may be sparse;
checking is independent of output cadence. A separate non-mutating post-pressure
witness measures coupling drift. NASA range extensions retain coefficients and
identify extrapolation.

## Geometry and observables

The canonical 200622-cell wedge places the injector exit at raw x=10 mm. Its
upstream O2 inlet radius is 1.6 mm; the exit radius is 2.5 mm. These are distinct
areas and origins. The [paper-exit coarse mesh](../../validation/mascotte-g2/paper-exit-wedge/README.md)
uses co-planar exits at x=0 with O2 radius 2.5 mm, a 0.3 mm lip, and methane radii
2.8–5 mm. Original meshes remain unchanged. This partial geometry still omits
upstream ducts, square chamber corners and 3D turbulence.

At the retained SRK densities, 44.4 g/s O2 and 143.1 g/s methane give exit
velocities about 1.914 and 63.568 m/s and momentum-flux ratio 38.98. A 100
microsecond startup cannot establish developed 15/45/70 mm profiles. Longer fresh
stages follow measured cost, conservation and coverage; no evolved restart is implied.

[G2 inputs](../../validation/mascotte-g2/direct-fgm/README.md) record source,
table, thermo, mesh, initialization and sampling controls. Instantaneous profiles
remain separate from time means and RMS. Original figures/captions and comparison
contracts are prepared by [mascotte-review](../../validation/mascotte-review/README.md)
and [g2-review](../../validation/g2-review/README.md).

[Conservation auditing](../../validation/mascotte-g2/conservation/README.md) uses
actual inventories, assembled operators and boundary flux histories. It separates
pressure/enthalpy staging from equation residuals and reports missing steps. Its
reconstructed kinetic boundary flux is explicitly an estimate. The
[308 nm LTE proxy](../../validation/oh-lte-proxy/README.md) transforms instantaneous
T/rho/OH before optional averaging. Ordinary OH, thermal OH* population, calibrated
emission and line-of-sight intensity remain distinct quantities.

## Reproducible source and artifacts

Job 126424490 uses source `f368f8bf894dceff3e9a781d108a3f6a133e8928` and overlay
archive `5277f09dd78a6b4830af43d1e6d3e9a56c93343dcba9c612657a5cf368e99d06`.
All 174 files were compared with actual Git objects before admission. The runtime
retains 14 libraries with individual ce76/282 source identities and rebuilds
combustion/solver/probe. The separately compiled PR repair is not in those inherited
thermo libraries and is not claimed as executing in this SRK run.

Build on a case-sensitive Linux filesystem. Freeze Windows archives with explicit
`git -c core.autocrlf=false -c core.eol=lf archive`, then compare each member with
actual Git objects. A blob-shaped hash computed from archive bytes does not prove
Git identity. The retained source-split archive had 99 CRLF-only conversions,
eight literal matches and no other changes. Its executed archive/binary hashes
remain authoritative, with the provenance correction retained separately.

Raw fields, physical tables, plots, PDFs, private paths and credentials stay outside
Git. The optical and conservation modules retain source selections from `c7de56b`
and `a4c504a`; neither changes a live solver. A source checkpoint does not update
a running job or constitute independent code/science approval or human acceptance.

Module READMEs define dry-run commands and affected checks. Compile and solve
through the qualified FlamePilot Slurm adapter; every CFD starts at zero. Preserve
errors and receipts, check product identities before reuse, and keep failures
distinct from current qualified results. The fixed figure catalogue and its
publication boundaries remain intact.
