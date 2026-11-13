# Maders paper-aligned development —13November2026

The owner requested alignment of boundaries, spatial discretization, startup and
manifold coverage while retaining the developed solver's absolute-enthalpy coupling.
All cases start at timezero. Baseline job127882841 and its mismatches remain retained.

## Implemented protocol

- Maders Fig1 outer free-slip velocity and zero-gradient velocity outlet. Inlets
  remain parabolic fuel Umax0.23m/s, uniform air0.23m/s,298K, atmospheric pressure,
  methane/nitrogen55/45 by mole. No speculative doubling of fuel flow.
- Limited second-order spatial convection. Euler time integration remains necessary
  for the qualified split-source integrator. This is not a second-order time claim.
-120000 structured wedge cells,60micrometres radial spacing at r6–12mm,200micrometres
  axial. Actual blockMesh/checkMesh passed. A400080-cell approximately60micrometre
  axial option is prepared but not executed. Neither is the unavailable author mesh.
- Cold air at timezero, cold streams at inlets, chemistry suppressed during flow
  development. At0.9s, set progress to its local table-source maximum near Zst in
  the first4mm of the burner. One continuous process, no imported evolved fields.
  Fifty-millisecond global Z/U changes are measured. Scheduled0.9s is not itself
  proof of a steady cold solution; use the measured changes when interpreting it.
- Existing absolute-Ha, Smooke, ideal-gas DRM19 and unity-Le coupling retained.
  Ignition changes composition/progress; thermo refresh retains specific Ha and
  logs the density/mass jump. No total-energy-conservation claim for this artificial
  numerical ignition event follows from maxDeltaHa=0.
- Reacting temporal screen is shifted to the ignition time: earliest eligibility
  approximately1.770s. Cold profiles cannot trigger premature graceful completion.

## Actual qualification and jobs

Job127906458,32ranks/64GiB,7h limit, compiled solver source
be68879e2bcea11fa62fc54c6129b6563d2b6037. Exact executable SHA256
595e45364403324f8ea660c93b3bb39944f809175324855f7197b0a1836ade1c.
Unchanged combustion and Smooke libraries are hash-bound to the previous build.
The new executable compiled/linked and the32-rank MPI interface reported sum496.

Its separate fresh qualification case ended normally at0.015s. C/source remained
zero during cold flow. Exactly one ignition at0.0101s selected183cells and reported
maxDeltaHa=0,Tmax1899.76K. Domain mass changed from3.8875768e-6 to3.8868336e-6kg
at ignition; this is retained as initialization accounting, not hidden.
The full separate fresh case started15:22:59Shanghai and is running. Its table is
still the frozen baseline6504370969a49553c1467bf3feb5ed9ba399058f31c8dd6155f2abe60a4da16f.
This isolates the combined case/numerics changes before the table replacement.

Job127906796 completed in405seconds,exit0:0. Source
d6fe12ea9b8f7f350d2e843bb42399c82e254576 computes actual Spitfire201-point
unity-Le/Peters-chi flamelets with Cantera3.2 DRM19 rates and diagnostics. It produced
27finite profiles:16residual-qualified steady states, one steady chi80 attempt
that missed the residual criterion, and10transient quenching snapshots. The seed
chi60 burning profile had Tmax1832.30K. At increased chi120 the transient reached
Tmax298.00092K at10ms. All27raw-profile hashes/finite arrays were independently
checked after retrieval. These are1D flamelet calculations, not27coflow CFD runs.
The original chi80 residual failure is preserved; it is excluded from table training.

The new exporter retains chi5/10 as held-out steady states and consumes qualified
steady members plus actual transient snapshots, with explicit cold/equilibrium
bounds. It keeps the original frozen258-query comparison reference. The baseline
exported-table diagnostic gave full coverage,T RMS14.2554K and source RMS3.63037
kg/m3/s. This differs slightly from raw-family lookup metrics because the actual
regular exported table introduces another interpolation stage.

Job127908321 is admitted for export, fixed held-out metrics, actual C++ node parity,
a fresh staged-ignition qualification, then a second full clean-start CFD case.
It reuses the exact solver be68879 executable without mutating the active build.
Its case/table source is045bebf3927bb54e896e9cab48ea61dbe5a7d775. Export/parity and
full CFD start must be confirmed from actual outputs; allocationRUNNING alone is
not evidence those stages passed. This case differs from127906458 by the physical
table, not the enthalpy coupling. No automatic table changes reach the first case.

## Retention and limits

FlamePilot adapter source0d2a63b546e180facdb6f1c736077517daa5c78c, environment
f46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793,
binding8e158ebd26a0a8699ce24c074540333755abce62495b54e1cb0d9d58073ea1ee.
All admissions use the retained adapter. Existing deadline23:06:41Shanghai and
prior usage remain unchanged. No unrelated jobs or external software were modified.

Operator manifests, scripts, identities, requests, receipts, known JobIDs and
physical data are in state/maders-coflow-20261112; raw cases/results remain in
the registered SCNet project trial. Famou remains deferred. CFD comparisons are
pending; no independent code/science approval, human acceptance or public result
publication is implied. The local ladder retains the last completed comparison.

## Export/parity follow-up

Job127908321 exported the201x201 candidate table successfully, SHA256
35a6b46b5a56d2831a598acb7810119b6bc27ced27d90d217d2258514295c1cc.
It uses14qualified steady training members and10physical transient snapshots,
with chi5/10 withheld and chi80 excluded for its residual failure. Exact C++
reader parity passed36physical table nodes,21species, worst scaled error5.65e-14.

Against the unchanged258-query held-out reference (all covered), exported-table
T RMS improved14.2554 to3.03392K; source RMS3.63037 to0.797688kg/m3/s and maximum
source error17.0594 to3.67275kg/m3/s. There are0nontrivial source-sign errors.
These are interpolation checks, not literature coflow agreement or independent
scientific approval. Both raw and exported interpolation stages remain identified.
The numerical table/source family remains a Peters-chi reconstruction, not a
resolved-strain CHEM1D reproduction. Full startup/reacting execution is tracked
separately in the operator record.

## Full-run follow-up —15:40Shanghai

Job127908321 passed the separate15ms startup qualification (exit0), selected183
cells at ignition0.0101s, maximum specific-Ha change0 and peak1818.23K at that
instant. The kernel subsequently cooled rapidly. This proves runtime plumbing,
not stable-flame physics; full cold-flow preparation may change establishment,
and any subsequent extinction must remain a reported outcome rather than a pass.
The full independent fresh case started15:38:20Shanghai. Job127906458's full
cold-flow case is also active; no unknown operation was resubmitted. Both full
cases begin at0, hold chemistry off until scheduled0.9s, target2s with temporal
screening after ignition, and retain the same enthalpy coupling.
All original usage/deadlines remain. Jobs have7h limits from admission, ending
before the existing23:06:41Shanghai operator deadline. New CFD agreement is pending.

## Status checkpoint —13November2026,17:20Shanghai

The two paper-aligned cases have different physical outcomes. Job127906458
(previous sparse table) is burning but still transient: at0.973355s,73.355ms after
ignition, global Tmax2105.91K and diagnostic heat release about10.57W. The retained
0.969988s profiles give temperature RMS300.97/654.33K and CO RMS0.01241/0.02290 at
H10/H40. Those values are not settled comparisons with the earlier baseline.
Its transient heat release also cannot be equated to steady inlet-supported burning.

Job127908321 (physical quenching table) ignited at0.9s with peak1817.79K, then
extinguished. At1.149s, global Tmax302.85K, meanT298.08K, diagnostic heat release
approximately1.24e-6W. Retained1.145s plane maxima are298.0004/298.0295K.
This is a failed flame-replication result, despite improved held-out interpolation.
No infrastructure crash or source-bound abort was observed.

After preserving snapshots, the operator requested stopAt writeNow only for this
extinguished case. The original/modified control dictionary hashes and reason are
in extinction-stop-receipt-1715.json. It ended normally at1.2368s, solverexit0,
SlurmCOMPLETED/0:0,elapsed6541s. Reconstructed last fields and all raw histories are
retained. No restart, new job, table alteration or enthalpy-coupling change occurred.
The burning127906458 continues under its original limits.

The better table lookup metrics do not establish flame stability. Candidate leads
are the low-progress source surface/branch construction and ignition-kernel behavior.
These remain hypotheses: this checkpoint did not establish one root cause or modify
physics to force burning. Before another run, inspect transient C/source/thermal
profiles and compare the two source curves in the states the CFD actually visited.

Profile archiveSHA256 values:
- r13:905c6444245eb654a845ffd82fe1a785c21d564eebab6eb35d83b864fcca4084
- r14:39a6bcbc4279231b296ec01b834ed0507ec8d25ca3bf7946628e9a6b6559ae85

The local ladder now retains7views: both new comparisons/histories, the completed
baseline/historical trajectory and the previous failed strict case. All71targets,
12papers and original captions remain. Both actual PNGs were visually inspected.
All7view images passed HTTP/content-hash verification; history and comparison RMS
values agree. The r13 H40 CO maximum0.04648 exceeds the original paper axis ceiling;
the fixed paper limits remain, and raw maxima/errors are retained without clipping
in the metrics. The figure is a transient snapshot, not an accepted match.
Source provenance and science verdicts are unchanged by this display update.
