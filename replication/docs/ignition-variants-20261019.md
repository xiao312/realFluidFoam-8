# Initialization sensitivity at phi=1.10

19 October 2026, Asia/Shanghai. The owner requested a cooler fresh hot spot and
an equilibrium-products initialization while retaining both current production
runs, 124862517 and 124863132. Neither prior job or case is modified.

Draft `draft/premixed-ignition` is based on paper-draft f020edc, with integration
ancestor 99d64f7. Runnable source: `9a02703215334ddc4b9b4fa85dc6d6ea86eb6931`.
Library build 124657926 and the pinned OF8 image remain unchanged. The diagnostic
solver sources, equations and chemistry are identical to the first paper draft.

| Initialization | Temperature and composition | Common controls |
| --- | --- | --- |
| Existing fresh hot spot | 1800-K compact cosine; fresh mixture everywhere | Existing jobs retained |
| `phi110-cool1400` | Same cosine and fresh composition, peak reduced to 1400 K | 4 mm, 8,000 cells, central width 0.2 mm, zero initial U, two waveTransmissive pressure outlets |
| `phi110-equilibrium` | Uniform central products slab, 2229.48898 K, all 53 species from the prior HP seed; fresh gas outside | Same geometry, width, velocity and outlets; abrupt products interfaces |

Both additions use phi=1.10 CH4/air, 100 atm, fresh T=298 K, maxCo=.1 and
maxDeltaT=1e-7 s. They retain both-front, three-OH-level, two-stage in-situ Eq.40
histories. The first full interval is 0.2 ms, eight ranks, at most 24 hours per
run. Maximum additional reservation: 384 core-hours for production and 16 for
the two startup allocations. There is no automatic extension or acceptance.

The products seed is reused exactly from the prior inlet campaign at phi=1.10:
`674b5e289e707918843ea7038b03af2f38170b09`,
`replication/development/premixed-inlet/seeds/phi-110-liang.json`.
SHA-256: `bc520c67cc881cc21a5845b69184456ff422d97ab5e28225835bd0d78e159f02`.
It is ideal-gas Cantera 3.2.0 HP equilibrium using the pinned author NASA7 data.
The initial products are not asserted to be SRK equilibrium or to conserve the
fresh state's real-fluid enthalpy. The new solver run relaxes this approximation.

Lowering the fresh hot spot reduces the imposed sensible-energy perturbation.
The products seed replaces much of the reactive inventory in the hot region.
It also changes the interface shape, so differences between these two recipes
cannot be attributed to temperature alone. Neither variant changes the library's
temperature range to conceal a hot transient. Delayed ignition or extinction in
the cooler case is a possible result, not proof that its initialized state failed.

Local generated-field checks passed: all 53 species are nonnegative, normalized
and symmetric; both domain ends remain fresh at 298 K. Each variant changes
400 central cells and leaves 7,600 fresh cells. The cooler field peaks at
1399.98301 K because cell centers do not lie exactly at the domain midpoint.
The products plateau is exactly 2229.48898 K. Seed pressure, phi, fresh composition
and NASA7 hash are checked before creating the case. Existing module tests,
shell syntax and Git whitespace checks passed.

Startup jobs: 124864532 (cooler), 124864535 (products). Each must pass compilation,
manufactured sampling tests, mesh checks, finite normalized endpoint checks and
numerical field equality with diagnostics on/off before its production submission.
These checks establish a runnable experiment, not a relaxed flame or paper agreement.
