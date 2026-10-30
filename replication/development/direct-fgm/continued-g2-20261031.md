# G2 and water-progress checkpoint, 31 October 2026, 07:08 Shanghai

The optimized full-SRK steady-flamelet diagnostic reached 100 us. The four
interior water-progress CFD cases also passed their mechanical and timestep
checks. These are bounded development results: developed G2 morphology and a
globally usable transported-progress manifold remain unresolved.

| Job | Executed source | Retained outcome |
| --- | --- | --- |
| 126430921 | `d479bc62125ccd7e2048f38910d13a0e8eb8fc48` | COMPLETED, 1306 s. Six property/setup pairs passed; 250 FGM and 250 steady-case measurements were identical. The matched 5 us G2 comparison had 321 identical measurements. A fresh 100 us hot-fill case passed all 15 mechanical checks. |
| 126431303 | `8f147f3f6d8f18c87c62bb0e2cabc426cb5581d9` | COMPLETED, 403 s. 53 fresh 20 ms chemical tails and a tighter-step witness completed; 76 unaffected branches retained their original identities. |
| 126432991 | `34d59d630e1cef6d7f9bf5559bb79d4e50231e71` | COMPLETED, 330 s. Four fresh 20 ms physical mixing witnesses passed their conservation checks. Missing table coverage persisted. |
| 126431807 | Case source `ef165a27b6922f99e0c0ec89fb654a08e1efdc67`; retained CFD runtime `f368f8bf894dceff3e9a781d108a3f6a133e8928` | All four CFD solves and case checks passed. Both timestep comparisons agreed to roundoff. Two initial DOP853 confidence checks failed; that allocation's failed verdict remains retained. |
| 126433289 | `e8801906c4d6c38e28abff3a7d29aeb4829dc694` | COMPLETED, 319 s. Reference-only refinement qualified all four retained CFD histories without new CFD runs or changing the original 1e-7 confidence limit. |
| 126432193 | Retained runtime `d479bc62125ccd7e2048f38910d13a0e8eb8fc48` | FAILED, 201 s. Fresh pure-CH4 G2 initialization passed, but the first Z update exceeded the strict table endpoint. No completed dynamic timestep. |
| 126433405 | `029c62bbfdbbcc2bc18fa3e98f268195eaafba02` | FAILED, 450 s. Build, endpoint controls and both 250-measurement interior comparisons passed. Strict mode measured a two-epsilon first-update excursion. Optional mode then rejected a 4.65e-9 excursion during the second outer correction. No completed cold-flow timestep. |

The OF8 environment remains
`f46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793`.
Each runtime receipt separately binds rebuilt and retained libraries. The
separate PR heat-capacity repair is not silently included in these SRK binaries.

## What the results establish

The 100 us case took 204 steps and 142.827 s elapsed, about 0.69 s per step.
Property/setup optimization preserved the measured fields and budgets. Its
uniform hot initialization still dominates downstream profiles; it is not a
stationary paper comparison. The longer fresh cold-methane attempt exposed an
endpoint failure before producing useful flow development.

The fixed endpoint candidate defaults to strict lookup. Its optional policy
maps only a local lookup coordinate within 64 double-precision epsilons of an
endpoint, never the transported Z field. Qualification first requires a measured
global excursion within that fixed bound, material-overshoot refusals, exact
interior parity and a fresh 100 us cold case. None follows from compilation alone.
The first measured excursion was 4.440892098500626e-16. The next correction
produced 4.645826390259344e-9, above the fixed 1.421085471520200e-14 bound.
The policy correctly refused that larger value. Equation and local residual
diagnosis precede another cold run; the bound is not widened to accept failure.

The water-progress coordinate is the declared species sum CO2+CO+H2O. Two
uniform states at Z=0.1972101464 and 0.2888410024 ran through 1 us at 10 and 5 ns.
Their maximum timestep differences were 8.69e-15 and 2.08e-15 of the local C span.
The new independent reference's maximum self-refinement difference is 1.262e-9;
the largest CFD-to-reference difference is 2.234e-11. This supports local source
coupling, not global table coverage or full-chemistry equivalence.

Longer physical tails reduced the maximum positive upper-cap source from 601.53
to 7.3722 kg/(m3 s), but 19 training caps remain outward-pointing. The maximum
mixing-coverage gap remains 0.10128 in raw progress. Two rich physical mixing
paths stayed outside the table through 20 ms. A same-Z/C pair evolved on very
different time scales, but its initial enthalpies differ by 786 J/kg; it does
not disprove an enthalpy-augmented closure. Failures remain visible in the
[hybrid review](../../validation/hybrid-water-review/README.md) and
[mixing-witness module](../../fgm/mixing-witness/README.md).

## Source and evidence boundaries

This draft integrates reviewed commits with cherry-pick provenance. Those
integration commits are not ancestors of every executed revision. Exact file
blob comparisons establish which source files agree; they do not make the
combined checkout an executed or scientifically accepted runtime. The coordinator
also audited 334 newly reachable Git objects and published five exact experimental
source references. See [source identities](sources-20261031.json). These tags
preserve successful and failed experiments; they are not accepted releases.
The older paper-sweep branch contains compiled products and was excluded from
this tag publication. Its exact retained source archive remains available.
No main merge or scientific publication is part of this checkpoint.

Only source and these summaries enter Git. Hash-bound raw histories, tables,
figures, failures and per-job accounting remain in the retained project evidence.
The reference recovery summary SHA256 is
`d8660d45235af69e790c86570e4c6f51e8b9f2b91c14a78a5444b45c84760c06`.
All CFD starts at time zero. Independent scientific approval and human acceptance
remain separate, and the fixed figure catalogue is not declared complete.
