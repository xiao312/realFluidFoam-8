# Parallel Schmitt / G2 baseline, 14 November 2026

All five requested targets were attempted. The first physical batch failed
before paper comparison times; this report does not claim figure agreement.
Separate fresh100us laminar G2 controls passed, but fresh longer cases failed
at115.09us (Cavalieri/Sharma) and130.04us (Schmitt). All six contact conditions,
and their separate first-order controls, failed the existing caloric check.

## Setup and evidence

The run matrix records source, exact frozen environment binding, batch resource
limits, JobIDs and script hashes. The full raw cases, failed states, immutable
input packets and build products remain in its SCNet data_root; no bulk logs or
fields were transferred to ECS. Runtime buildr5 uses15 identified retained full
libraries and a rebuilt f19bff9 solver; case scripts are source5e3a0a2. Instrumented
buildr9 compiles2082a38 against those same libraries and retains both helpers.
The actual r9 build-qualification.json identifies every product and linkage.

Contacts use p6MPa,U10m/s,dx10mm and exact paper erf profiles: oxygen density
1000 to100kg/m3 for nx2/4/6; H2/O2 composition with100K for nx1e-5/2/4. Target
sampling time20ms was not reached. Initialization inverts the executing SRK
thermo, with maximum initial density relative error5.25e-13. Domain[-2,2]m and
waveTransmissive boundaries approximate the paper's nonreflecting treatment.
Our conservative pressure-based solver does not implement AVBP's artificial
viscosity/nonconservative correction. Cryogenic NASA extrapolation is explicit.

Sharma/Cavalieri use5.61MPa,85K O2/288K CH4,44.4/143.1g/s and a200mm10000-cell
wedge. Schmitt uses5.6MPa,83/300K and a400mm20000-cell wedge. Both retain the
5mm O2 exit,0.3mm lip and5.6/10mm CH4 annulus. Upstream taper, square corners,
3D LES, PDF closures and paper grid resolutions remain unmatched. Sampling
includes centreline-near T/U/O2 and radial planes15/45/70mm. These are reduced
fixed-chi100000/s steady-flamelet diagnostics, not complete paper FGM/LES.
Both physical table inputs retain failed strict steady-RHS qualification; no
species, EOS coefficient or reaction rate was fitted to the paper.

## Actual failure and development loop

Tightening contact maxdt50us to5us and using three fixed-h thermo corrections
did not fix the instability. First-order advection was also insufficient. The
instrumented solver preserves the unchanged1e-8 caloric threshold and writes
failed T,p,h,Y states at their actual times. They are diagnostic records, never
CFD restart inputs. Successful compilation is separate from physical validity.

At0.516782ms the oxygen nx2 failure cell was p1.841099MPa,T115.235229K,
storedh=-361413.917J/kg, evaluatedh=-211103.218J/kg,Cp=6083536.558J/(kgK).
The initial pressure was6MPa. This supports investigating pressure-equilibrium
loss and thermodynamic branch/inversion behavior together. It does not establish
that a particular pressure-equation change is correct. A separate point probe
compares the captured states against6MPa; its per-point numerical verdicts remain
independent of process completion and scientific agreement.

The next loop is: preserve baseline failures; isolate the failing state; test a
supported numerical/source correction; rerun all six fresh contacts and both
fresh G2 condition sets; compare finite profiles, conservation, timing and actual
paper-window statistics. No threshold change, evolved start or chemistry fitting.
Only developed data may be used for paper means/RMS. The intended40-100ms G2
window remains unavailable. Do not invent a completion ETA from startup speed.

Infrastructure setup failures and operator wrapper defects remain separately
recorded in OPERATOR.md. The corrected long-mesh internal-face count is39550;
actual blockMesh/checkMesh and geometry/area audits passed. Frozen mass-diffusion
suppression requires runTimeModifiable no; external timeouts retain periodic
output but do not guarantee a final write. All compute uses FlamePilot Slurm.

## Follow-up controls

Source6a08b85 exposes the existing continuity re-solve to non-tabulated contacts
through an opt-in control; original defaults and tabulated guards remain. Job
128012872 compiled/linked it and ran all six fresh contacts. All still failed.
The oxygen failure time/pressure were essentially unchanged. This experiment
is retained on the draft branch and must not be presented as a solved defect.

Point diagnostic128012177 completed all four local round-trip checks. Its raw
queries nevertheless reveal the oxygen density jump988.08 to131.12kg/m3 over
115.235000 to115.235229K at the captured1.841099MPa. The corresponding enthalpy
jump brackets the failed CFD stored value. A generated-target round-trip test
alone is insufficient. Both exact CSVs and diagnostic plots are retained.

Instrumented G2r11 replays were rejected before CFD because the operator
shortened endTime below the unchanged observation interval. Correctedr13 keeps
the original0.1s endpoint/observations with an external1200s runtime cap. The
actual observation/decomposition loader passed both corrected configurations
and rejected the old short endpoint. Preserve these setup failures separately.

## Captured-target thermodynamic diagnosis

Both instrumented G2 replays are now terminal physical failures, not startup
qualification:128013575 failed at115.091648809555us and128013758 at
130.040656590024us. No developed paper-window mean/RMS exists from these runs.
The exact rank0 cell0 snapshots were retained, including all53 mass fractions.

Jobs128016838/128018627 compiled the captured-target probe against the frozen
15-library runtime and completed six property-query deliveries each. These
queries take zero CFD steps; captured fields must never become CFD restarts.
The source revisions are83bb516 and10ffd2d. All12 corresponding numeric CSVs
are bitwise identical, confirming that coefficient export did not alter results.
A generated-target roundtrip is insufficient: fixed captured enthalpy failed
from all six starting temperatures after12 correction passes, with residuals
8375.2575J/kg for Cavalieri and4572.8538J/kg for Schmitt. The forward h(T)
curve jumps across each transported target within1e-5K. Additional correction
passes do not repair this gap. At original pressures the G2 residual floors are
only0.01364/0.00340J/kg and pass the unchanged production Cp*T-scaled audit;
separate stricter h-relative diagnostic criteria fail. Preserve this distinction.

Independent polynomial root enumeration used exported actual W/RR/b/coefficient
values. At each gap the SRK cubic changes from one real root to three, and the
library switches to the largest root. Returned densities satisfy the cubic to
about1e-17 absolute polynomial residual. This is not evidence that arbitrary
root replacement, tolerance relaxation or chemistry fitting is appropriate.
The pressure-equilibrium failure and thermodynamic root policy remain coupled.

Linux case-sensitive extraction and an independent archive-member reader agree
on all56 raw field hashes. An ordinary Windows extraction collided enthalpy h
with radical H; that fixture is invalid and retained only as a negative control.
The extraction helper now checks FoamFile object identity and refuses the
collision. No CFD or successful property query used that contaminated fixture.

## Isolated contact algorithm experiment

The double-flux application in validation/schmitt-contact/double-flux is an
experimental1D nonreacting OpenFOAM/SRK application, not a production reacting
G2 implementation. It measures pressure/velocity equilibrium, actual EOS closure,
mass balance and explicit quasi-conservative energy defects. Uniform and short
interface controls precede six independent time-zero20ms cases. No evolved starts.
It uses common HLLC mass/momentum/species fluxes, receiving-cell frozen energy
tangents and SSP-RK3. Its first-order inviscid discretization differs from the
paper's AVBP TTGC/nonconservative artificial viscosity; pressure flatness alone
cannot establish paper agreement or exact energy conservation.

The first compilation128020156 exposed an output-stream API error before any
CFD. Correction b61f889 uses Info().precision. Compilation and all physical
qualification remain pending for this corrected candidate at this checkpoint.
Failed source/job identities are retained; no main-branch promotion is claimed.

The local Forge now exposes captured-state diagnostics under Sharma4b,
Cavalieri6 and Schmitt21, with raw property/target CSVs and source/library hashes.
They are labeled as failed-state diagnostics, not developed-paper profiles.
All originals/captions and71targets/12papers remain. Independent scientific
review and human acceptance remain separate and unassigned.

## 18:12 contact results and supported EOS numerical correction

Job128021342 (case sourced96555f, compiled applicationd9d7eb5) passed the
fresh100us uniform and1ms oxygen-interface controls. Six full20ms contacts
then ran independently from zero. Only oxygen nx4 and H2/O2 nx4 completed;
the batch itself FAILED231s/8cores. Four other widths stopped on literal-EOS
versus transported density mismatch (1.10e-8,1.27e-8,2.23e-8,1.68e-6 relative).
Their failed states/results remain retained. Do not replace absent20ms data
with earlier fields or call all six complete.

Completed oxygen/mixed cases preserve pressure to4.9e-12/8.3e-12 relative and
velocity to3.2e-11/3.8e-11. Their measured quasi-conservative energy defects are
0.427%/0.527% of initial absolute-energy magnitude. Balance residuals include
those defects and are about2e-13/4e-13 relative; this is not exact energy
conservation. Oxygen took41solver-wall-seconds. Both interface profiles are too
diffuse with first-order reconstruction. Compared with graphical paper traces,
density RMS errors are78.21/90.30kg/m3 and temperature RMS22.10/8.14K. Mixed
peakT is130.31K. These are development results, not scientific acceptance.

The paper's continuous nonconservative traces were extracted from PDF vector
filled-stroke envelopes, with path/frame calibration, source hash and graphical
half-width retained. Paper lines and our raw cell markers use matching2x2
layouts/axis limits. All-width and nx4-only views are present in local Forge;
failed widths are explicit. Fig6 pressure/velocity reference extends beyond our
x=2m boundary; comparison metrics use overlap only, without extrapolation.

Independent reproduction identifies cancellation in the historical one-real-root
Cardano formula: at6MPa/163.64244606263K it returns274.913430489kg/m3 versus
274.913427476 from stable evaluation and independent polynomial roots. The
transported target is274.913427475. Candidatec6d486e computes the larger radical
and recovers the other through S*Tl=-Q. It preserves EOS parameters, chemistry,
three-root branch/root policy and acceptance limits. This does not solve the
separate captured reacting-G2 enthalpy branch gap.

Adapter job128022863, admitted18:09:41 with16cores32GiB/10800s, freezes c6d486e.
It rebuilds all15 custom libraries plus four dependent applications from source,
verifies linkage/product hashes, repeats six zero-CFD-step captured-state queries,
then runs new uniform/short/six-full contacts. No old thermodynamic binaries or
CFD states are reused. Compilation/physical qualification is pending at this
checkpoint. The source remains a draft; no production merge or science approval.

## Completed stable-SRK contact rerun

Job128022863 completed in1345s with16allocated CPUs. All15 libraries/fourapps
were freshly rebuilt and hash/linkage-qualified; all six fresh20ms contacts
passed unchanged numerical checks. The recorded EOS-closure stops are resolved.
`follow-up-r20.json` retains source/product identities, six-case numerical
metrics, comparison errors and independent field diagnostics. These remain
unaccepted scientific comparisons, not a reactingG2 qualification.

Mass-field integrals and gradient centroids independently confirm the prescribed
0.2m translation. Measured numerical diffusivity is0.05m2/s, equal toU*dx/2:
first-order advection explains the overly broad density/temperature profiles.
Energy defects remain0.378–0.587% of initial absoluteenergy magnitude, explicitly
accounted. Solver walltimes were38–56s per contact, concurrently executed;
the allocation's22m25s includes full compilation/environment preparation.
Paper lines/our raw markers and individual-width views are now in localForge.
The plot contract records PDF hash/vector paths/calibration and actual style.

The remaining captured reactingG2 enthalpy gaps were reproduced by the new
runtime's zero-CFD-step queries; delivery completion does not imply convergence.
Matched fresh G2 r21 replays were admitted through FlamePilot:128024791
(Cavalieri/Sharma condition) and128024867(Schmitt condition),32cores each.
Each schedules a new100us laminar control and then an independently generated
full case from time0. Runtime c6d486e is reused as compiled software only.
Their laminar/fixed-chi closure and approximate tables remain explicit
limitations. Read actual runtime receipts before claiming control/full results.


## Reacting replay and coupling experiments, 2026-11-14 19:50 Shanghai

R21 jobs128024791/128024867 failed after separate fresh100us controls passed.
The independently generated full cases stopped at115.252/129.975us, with
caloric mismatches7.703/7.135kJ/kg. Neither supplies developed paper means.
The stable Cardano evaluation fixed the six isolated double-flux contacts;
it did not resolve these coupled pressure/enthalpy failures.

The upstream realFluidFoam pressure equation at674468c uses an explicit density
time correction, with Y/energy inside pressure correctors. Opt-in draft controls
now isolate these differences; defaults and caloric acceptance are unchanged.
Pressure-term-only source1ef8d92 job128026118 compiled but all four contact
controls failed. Inner-order source6398a14 job128028121 compiled, but its enabled
cases stopped before CFD on a runtime-type guard. Its wrapper also wrote malformed
JSON targetTime:.001; preserve those original receipts as invalid, not successful.
Sourcef457906 fixes dictionary-model selection and wrapper numeric serialization.

Job128029180/sourcef457906 compiled, linked and executed four fresh1ms contacts;
all failed. Enabled oxygen stopped456.012us (default515.900us), gap1019.329J/kg;
enabled mixture261.374us, gap171410.245J/kg. No20ms candidate cases were admitted.
Solver binarySHA25689e28f5917befb35e7f91a62aa77dcfa247022595f79ec8bc2aaed6dd91ece44;
parent C6 runtime manifestc2d8c7e3f6128da51ca5e3e5fd682ff086ccca46c872197ab97d86beb17b3b25.

Source inspection confirms psiThermo::rho returns cached p*psi, and SRKpsi is
1/(ZRT), rather than the literal differential compressibility. Restoring density
through an additional continuity solve is another difference from the author
loop. The next prepared R25 experiment isolates that setting with both author
coupling switches enabled and reuses this exact binary/library identity.
Preparation is not execution; actual admission and terminal receipts are required.
No chemistry fitting, evolved starts, threshold relaxation or scientific acceptance.


R25 job128030125 FAILED164s after reusing the qualifiedf457906 solver, with no
rebuild. Both author coupling switches were enabled; only additional continuity
restoration differed across four fresh1ms cases. Neither survived longer:
oxygen456.012us, mixture261.374us. Last complete energy-state histories nearly
overlap. Mean pressure near6MPa conceals failed-cell pressures1.27–1.84MPa.
The two new failed-history views in localForge retain this negative result.
Energy integral changes are explicitly not boundary-flux-corrected residuals.

The original-author-loop control is now independently admitted as128030606,
source624c743 (new audit/preparation module; upstream equations unchanged),4cores,
8GiB,1800s. It builds an isolated realFluidFoamAudited against the C6 parent
libraries, adds the existing caloric check and state witnesses, and preserves
one original thermo.correct call. Two independent fresh1ms cases are requested.
No CFD result is claimed yet. Exact patch hashes, binary linkage and terminal
receipts remain required. This compares solver ordering with a shared rebuilt
runtime; it is not a reconstruction of the entire historical paper environment.
