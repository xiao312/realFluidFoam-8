# Inlet-resolved G2 and Maders development — 16 November 2026

Checkpoint at 15:15 Asia/Shanghai. Development is authorized until 19:00;
this is not a terminal report or scientific acceptance.

## Geometry and reference definition

The new G2 mesh contains the oxygen passage, tapered post, separator lip,
methane annulus and chamber. It has 10,720 cells and a 5-degree axisymmetric
wedge. It replaces the earlier exit-only rectangle for these experiments.
Sharma Figure 3 and Table II provide the dimensions in
[the supplied paper](https://arxiv.org/pdf/2311.15034), PDF page 9.
The reconstructed taper length is 3.969897 mm from the 3.6/5.0 mm diameters
and a 10-degree angle interpreted relative to the axis. Methane diameters
are 5.6/10 mm; the chamber is 200 mm long with 25 mm equivalent radius.
The finite tip, unreported upstream duct lengths and square-to-axisymmetric
chamber approximation remain explicit assumptions, not experimental CAD.

Executing SRK inlet initialization gives oxygen density 1181.22680227 kg/m3
and upstream bulk velocity 3.69279156 m/s. Methane gives 41.7577500455 kg/m3
and 63.56753740 m/s. The full-annulus mass flows are 0.0444 and 0.1431 kg/s,
respectively. The actual planar-wedge volume fraction uses sin(5 degrees)/(2π).

The current physical FGM uses the deposited Kong 23-species/51-reaction
mechanism, Spitfire trajectories and a 201-by-101 Z/local-progress table.
It is one high-dissipation quench family, not the complete multi-dissipation
manifold or presumed-PDF LES described by Sharma. CFD owns SRK temperature,
density and absolute enthalpy; table temperature is diagnostic. Every case
starts from original time zero. Initial hot kernels are numerical ignition
recipes, not reconstructions of an experimental torch or developed RANS field.

## Executed results

| Experiment | Slurm job | Observed result |
| --- | --- | --- |
| GRI53 inlet baseline | 128171032 | Cold case completed 50 μs; independent hot case failed at 77.40795 μs |
| Kong23 inlet baseline | 128172483 | Hot case failed at 25.9 μs |
| New inner/source controls | 128175800 prelude | Default-off energy states identical; inner-four minus inner-two mean temperature 3.15e-8 K; old-time anchors unchanged |
| Coupled Kong pilot, maximum step 0.1 μs | 128175800 | Failed at 28.4 μs, oxygen passage pressure 0.75943 MPa |
| Independent Kong case, maximum step 0.5 μs | 128176759 | Failed at 146.49813 μs, oxygen-rich mixed cell pressure 5.24727 MPa |
| Actual conserved-state replay | 128178421 | Delivered normally; both physical recovery queries failed their original state criteria |
| Matched cold RANS, new coupling | 128178755 | Admitted 15:04:48; actual physical result pending at this checkpoint |

The coupled app/probe source is 30a102b831b4ee30bb48ebb67231832fd7742755;
case generator is de68c5ff3e0c2eb3199300400f38a9c0e22a7d60. Its build receipt
SHA256 is 391bd0ae6015b1e3f0992ad32c597f1b2bda25a85fa3199a3aef798fc7e7729b.
All 15 custom DSOs retain the B04c identities. Kong table SHA256 is
7bd5d213aad69ae50e4b15af161d81bc8d34269b47cdc96ec2283c1064193ac8.
The pinned FlamePilot adapter source is 0d2a63b546e180facdb6f1c736077517daa5c78c,
OF8 profile f46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793.
Build qualification is distinct from physical qualification.

The original zero-flow checker still fails its assembled-residual and duplicate
identity criteria. Their measured absolute errors are below a separately
recorded floating-point arithmetic bound. We retain the failed checker verdict;
the independent source-iteration comparison does not convert it into a pass.

### What the recovery queries establish

An earlier captured Kong state at 25.9 μs admitted a stable rho/Ha recovery
at 5.71049 MPa and 160.29412 K. That scalar result motivated the coupling
experiment, but did not qualify the coupled algorithm.

The newer pilot state is pure oxygen with transported density 1174.85954306
kg/m3. Fixed-rho/Ha recovery converges to 84.08951 K and 0.75952 MPa, but the
library's selected root differs by 94.81% in density. It remains rejected.
The adaptive case gives 161.76528 K and 5.247365 MPa, with isothermal pressure
derivative -39.95044 Pa/(kg/m3). It is mechanically unstable and remains rejected.
More enthalpy-inversion iterations cannot establish an admissible homogeneous
state in either query. These are property replays, never CFD restarts.

## Table-versus-CFD thermal-state diagnostic

The new internal-cell auditor excludes stale derived boundary values, verifies
all field and partition hashes and integrates actual wedge polygons. Its
summed volume, 5.451009351254e-6 m3, agrees with the executing energy-state
volume to 8e-12 relative. Independent CSV sums agree; unbound-temperature and
wrong-angle negative controls fail before writing outputs.

| Snapshot | Volume RMS temperature difference | Absolute-source weighted mean absolute difference | Absolute-source fraction with difference above 100 K |
| --- | --- | --- | --- |
| Pilot, 25 μs | 1.5565 K | 57.6992 K | 13.4214% |
| Adaptive, 100 μs | 1.5741 K | 22.4899 K | 5.3594% |

Small volume norms hide localized reacting-cell departures. Conversely, these
snapshots do not support claiming that the source is broadly evaluated at
thousands of kelvin away from its table state. No temperature scaling, chemistry
fit, table correction or acceptance change has been applied.

## Maders: new finer profiles

Fine run 128163193 (240,000 cells) remains active. At 0.964994457858 s, 65 ms
after ignition, temperature RMS errors against the retained digitized paper
points are 247.72 K at 10 mm and 381.36 K at 40 mm. CO RMS errors are 0.007808
and 0.003319 mass fraction. Peak temperatures are 2003.56/2052.82 K.
The upper-plane CO shape agrees substantially better than previous startup
results; its temperature outer tail is still too broad.

Coarse run 128169871 (96,000 cells) is independently advancing. At 1.06000004 s,
the two temperature RMS errors are 376.63/264.21 K and CO errors 0.013187/0.013677.
Neither later time nor peak agreement alone establishes stationarity.
Both use no-slip outer walls, original-zero cases, source f6e2ae8, compiled
solver ea2a4046ab239ae4fdb1197cd65fd83ebc933785 and the unchanged physical table
35a6b46b5a56d2831a598acb7810119b6bc27ced27d90d217d2258514295c1cc.
Local Forge has the finer comparison as primary, with coarse and earlier
results/history retained. No independent review or publication is claimed.

## Research leads and implications

[Ma, Lv and Ihme's 2017 numerical work](https://arxiv.org/abs/1704.02637)
addresses spurious pressure oscillations at transcritical material interfaces
using locally frozen thermodynamics and double energy fluxes. This suggests
testing interface pressure equilibrium and energy defects directly rather than
assuming a smaller time step repairs the coupling. Its explicit algorithm is
not a drop-in PIMPLE replacement.

[Loci-Stream's pressure-based double-flux guide](https://streamline-numerics-inc-loci-stream.readthedocs-hosted.com/en/stable/theory/appendices/appendix_double_flux.html)
requires compatible row-local energy fluxes and a frozen pressure-density
closure, followed by true-EOS synchronization. Merely changing a pressure
derivative is not that complete method. Energy quasi-conservation must be
measured explicitly. Documentation is a design reference; no matching
production implementation has been qualified in this project.

[Mafakhery and Shafaee's October 2026 deposited G2 cold-flow data](https://data.mendeley.com/datasets/9phmmxy9gv/1)
describe axisymmetric Fluent RANS with volume-translated PR. Their associated
paper is submitted, not established peer-reviewed validation. They predict a
two-phase boundary near 5.22–5.34 MPa and explicitly distinguish model outputs
from absent cold-flow measurements. This is relevant to the 5.247 MPa failed
mixed state, but a different EOS cannot diagnose our exact state by itself.
The file API returned HTTP403; no deposited raw file has yet been downloaded.

The next algorithm question is whether strict caloric enforcement inside an
unfinished pressure/energy iteration prevents a legitimate next coupled
correction. Any deferred trial audit must retain finite/positive-state guards,
log failed trials and enforce the original closure criterion before accepting
a completed timestep. This is a proposed experiment, not an implemented fix
or a reason to accept the current failures.

Raw receipts, retained collections and operator records are under the configured
day project directory, `state/g2-inlet-fgm-20261116/`, outside Git. The fixed
75-target/12-paper local ladder retains all captions and prior results.

## 17:05 — inlet priming resolves the tested startup failure

The completed original-zero B21/128182289 reached 300 microseconds in652
physical steps. It uses the same coupled30a solver, Kong23 table and center
kernel as B15, but initializes mass-consistent velocity inside both actual
inlet passages. The chamber still starts at rest. This changed initial condition
is not a developed precursor, and its effect must not be attributed to chemistry
or a new EOS. Final caloric relative residual2.82e-9 remains below the original
1e-8 limit. Actual species and raw-progress consistency errors are~1e-12;
elemental mixing-line error is below7.3e-12. No normalization was applied.

The accepted-state equation budget, independently reproduced using Python
compensated sums, gives a boundary mass residual3.16e-17kg. Its Ha state/equation
residual is0.003458J over5.7987J absolute assembled terms. This checks the Ha
operator and state record; it is not an independent total-energy proof. Actual
cell temperature spans84.986–3386.697K. At15/45/70mm, temperature profiles remain
largely cold at300us. They are visibly poor comparisons with developed paper
means and are displayed as such, using paper lines and CFD markers.

B22/128183633 rebuilt all15 libraries and both applications from30968b8;
compilation/link identity succeeded, but a wrapper passed a table file where a
directory was required. The preserved batch failed before CFD. B22b/128185960
reused these exact compiled products, completed its physical controls, and
passed all15 field and8 property comparisons exactly. Both variants took one
fresh1ns step. Three actual forbidden-Dimix access controls failed as expected.
Full/optimized elapsed time was11.26/6.31s; this short control does not establish
sustained speed. No precision or acceptance criterion was changed.

B23/128184868 is a separate fresh-zero3ms laminar run with a1us cap; B24/128186968
is an independently admitted fresh-zero kEpsilon mean-Z/C diagnostic with an
annular kernel, initialized inlet velocities and the qualified30968b8 optimized
runtime. They are different turbulence/ignition experiments, not a matched
single-variable comparison. Both are bounded by the unchanged19:00 owner
deadline. No developed mean or scientific approval is inferred.

Maders fineA03 at1.040005s has temperature RMS343/545K and CO RMS0.0103/0.0189;
coarseA04 at1.280008s has temperature RMS934/771K. Later time alone has not
improved the comparison. Histories show oscillating peak location/axis heating,
particularly on the coarse grid. Keep the earlier65ms fine view as the best
retained snapshot, display these later failures too, and do not cherry-pick a
transient minimum as steady validation.

## 17:30 — source departure and RANS failure isolation

A pointwise, no-integration Cantera3.2.0 audit uses the exact author mechanism
9942d75e and all23 captured species from B21. It preserves unnormalized mass
fractions. Rates are ideal-gas concentration chemistry at specified T/p, as in
the manifold producer, not a separate real-fluid kinetic model. The CO+CO2
source is kg/m3/s. Stored-source absolute integral is5.76655e-5kg/s. Relative
volume-integrated L1 differences are7.758% at stored table T/reference p,
168.575% at actual T/reference p, and174.278% at actual T/actual p. Hot cells
T>500K retain177.790% discrepancy. The largest integrated discrepancy is near
x3.5mm/r1.719mm: actualT3386.70K versus tableT3451.83K, stored source21512
versus pointwise actual-T/p405100kg/m3/s. Net reversible rates near equilibrium
are sensitive; this is not an Arrhenius multiplier or a source calibration.
Stored source may also be a captured-stage diagnostic, so its difference from
final-state chemistry must not be assigned solely to interpolation. An
independent stoichiometric net-rate-of-progress projection reproduces the worst
pointwise difference. A changed input-audit hash is refused before writing.
No CFD field or source is altered by this analysis.

B23 at the common300us shows whole-volume T RMS difference5.04K for0.5/1us
caps, but167.18K over the hot-cell union (0.0901% of total volume), with local
maximum2116.90K atx1.5mm. The cold chamber must not conceal hot-front error.
No temporal-convergence qualification follows. This points to joint timestep,
near-field resolution and thermochemical-manifold work, rather than plotting
polish or a fitted source factor.

B24/128186968 failed174s before CFD because the operator wrapper placed RANS
configuration after the initializer. B24b/128187542 corrected the ordering and
ran physical steps, then failed201s at86.4206ns. Worst stored state is nearly
pure methane inside its passage, p1000Pa/T60K andrho8.9041kg/m3; the caloric
residual97306J/kg remains a failure. B25/128188830 is an independently admitted
three-control delivery: annular laminar, center-kernel RANS and cold source-paused
RANS, all originalzero, same qualified309 runtime and primed passages. Each
runs in its own strict-Bash child and preserves actual exit separately; a
successful delivery envelope will not imply physical success. No gates changed.

The predeclared coarse Maders saved-time mean over1.0–1.25s gives T RMS292/469K
and CO RMS0.00864/0.01626. It does not remove the narrow upper-plane flame
or establish statistical convergence. Mean/std use actual irregular time intervals
and unchanged radial coordinates. A closed-form irregular-time linear/constant
control exposed cancellation in the first variance implementation; the retained
v1 was replaced by a stable centered-moment integration and verified before
use of v2. Prior instantaneous/better/worse snapshots remain visible. This is
additional finite-window evidence, not the paper's steady solution or acceptance.
