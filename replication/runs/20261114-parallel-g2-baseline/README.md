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
