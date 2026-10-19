# Overnight qualification, 20 October 2026

Observed at 02:01 Asia/Shanghai. Work continues toward the owner's 08:00 cutoff.
Cases 2–4 have completed all 13 pressure-chemistry sweep conditions. Case 5
remains under investigation; neither its transport implementation nor the
transient CFD flames are accepted as a replication.

## Domain and numerical guess

At phi=1.10, 100 atm and 298 K, doubling the 4-mm steady-flame domain and
shifting the numerical profile by 0.5 mm while increasing its velocity guess by
25% produce the following speeds. These are independent steady FreeFlame
initial guesses, not CFD restarts. Model inputs and mesh criteria are unchanged.

| Case | Extended domain (cm/s) | Shifted guess (cm/s) | Jobs, respectively |
|---|---:|---:|---|
| 1 | 7.46193337 | 7.46193181 | 124943363 / 124943370 |
| 2 | 7.47885491 | 7.47885663 | 124943365 / 124943371 |
| 3 | 7.05995414 | 7.05993608 | 124943367 / 124943373 |
| 4 | 7.13344813 | 7.13341533 | 124943368 / 124943375 |

Differences between these two perturbations are below 0.00004 cm/s. This is
evidence against domain size or initial guess explaining the discrepancy at
this condition; it does not qualify every equivalence ratio. Case 5 jobs
124943369 and 124943376 were still running at collection. Input preparation is
commit 1dcbd82; model executable is build 124940280, source 8a0c8d0.

## Energy-flux reconstruction

Audit 124943832 used the hash-verified energy probe from build 124940280 and
the strict metadata checks in d8fec1a. The first attempted manifest was rejected
because legacy profiles lacked model metadata; it was not submitted. The
replacement manifest explicitly identifies the four profiles below.

| Profile | Model | Flux range (W/m2) | Range / peak conduction |
|---|---|---:|---:|
| 124934682 | Ideal, finer grid | 4630.27 | 0.00035581 |
| 124934683 | Original SRK calorics, finer grid | 26544.94 | 0.00215727 |
| 124939652 | Smooth SRK + pressure chemistry | 2496.59 | 0.00020071 |
| 124941217 | Smooth SRK + pressure chemistry, finer grid | 3727.95 | 0.00029976 |

The smooth model reduces the reconstructed imbalance to the ideal control's
order of magnitude. Its residual increases on refinement, so this is not proof
of energy convergence. The reconstruction is a continuous face-flux diagnostic,
not the exact discrete Flow1D residual. Fine smooth-SRK speed is 7.01949702 cm/s;
its last refinement changes speed by 0.1136%. The high-temperature extension is
still a labelled physical-model alternative, not a verified Liang implementation.

## Remaining Case 5 test

Frozen probe 124944368, source c8136d2 and build 124944309, removes only the
Takahashi upper reduced-temperature clamp while retaining its lower clamp and
the primary Table 2 correction. Hot-gas H2 and OH diffusivities change by less
than 0.8% at the sampled phi=1.10 and 1.40 states. The primary data mainly cover
Tr=0.95–5; extending beyond that range remains unqualified extrapolation.
Independent flame pilots 124944787 / 124944789 / 124944790 cover phi=1.00 / 1.10 /
1.40. They must not replace the bounded control curve merely because they fit
the paper better.

## CFD heat release

The read-only monitor in 3f29cb3 was exercised on two completed and three active
jobs. All five first tracking times are zero, and all saved Qdot snapshots read
successfully. The integral is over the full 4-mm uniform mesh, including both
flame fronts; it is heat release per cross-sectional area, not a speed estimate.

| Job | Family | Latest tracking time (us) | Qdot snapshot (us) | Peak Qdot (W/m3) | Integral (W/m2) |
|---|---|---:|---:|---:|---:|
| 124916221 | Native, completed | 200.018 | 200.018 | 2.31359e12 | 4.25730e7 |
| 124916226 | Energy correction, completed | 200.021 | 200.021 | 2.38654e12 | 4.36885e7 |
| 124939663 | Native, active | 48.418 | 40.018 | 1.81677e12 | 3.55894e7 |
| 124939611 | Energy correction, active | 48.921 | 40.021 | 1.77738e12 | 3.51019e7 |
| 124942608 | Cantera transport, active | 19.442 | 9.992 | 1.71141e12 | 3.03165e7 |

Different snapshot times cannot establish a family-to-family heat-release
difference. The completed 200-us controls are comparable in time; the active
runs remain transient. Their source/build/initial-field identities are retained
in the fresh-start and Cantera-bridge qualification records. No saved transient
state was relabelled or reused as a new zero-time state.

Raw evidence remains under the contained project workspace: local
`state/cantera-liang-20261019/{all-sweeps-0203.json,energy-refinement-result.txt,
heat-release-0207.txt,high-t-pilots-submission.txt}` and remote per-job outputs.
Filenames are receipt identifiers; timestamps inside the records are authoritative.
