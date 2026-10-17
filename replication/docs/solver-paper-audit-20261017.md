# Solver-to-paper audit, 2026-10-17

The running counterflow executable matches the main 2022 reacting-flow/library
architecture. It does not implement the 2025 modified PIMPLE loop: that loop is
in the separate `realFluidFoam` executable. Both executables share a newer
Newton-bisection thermophysical implementation, with some differences from the
2025 flowchart. This is an architecture audit, not proof of equation-by-equation
equivalence or numerical replication.

## What is actually running

- Upstream physics source: `48506de20ce67f35279c5347b09dcd86865a4c39`.
- Qualified build: job `124657926`, source `b1153ea9c64b9abf55f7be6c488549024c081279`.
- Live evidence inspected read-only: job `124668502`; its log explicitly reports
  `Exec : realFluidReactingFoam ... -parallel`, OF8, eight ranks. Its run source
  is `2b10379ecf1751b2d8fdd29c7f39314ef5d47a9a`.
- The job's product verification receipt reports successful build-product hashes;
  its `ldd` record resolves `libspecie.so` from build 124657926's isolated library.
- `git diff 48506de b1153ea -- applications src Allwmake` and
  `git diff 48506de HEAD -- applications src` are empty at this audit checkpoint.
  Our changes are the controlled environment, cases, analysis and records.
- Runtime selection is `hePsiThermo / SRKchungTakaMixture / chungTaka / rfJanaf /
  sensibleEnthalpy / soaveRedlichKwong / rfSpecie`, with laminar combustion and
  flow, GRI30 chemistry and SEULEX. Current development inputs use one outer
  corrector and two pressure correctors.

Local executable authority: [runner](../validation/inside.sh),
[case generator](../validation/flames/generate_counterflow.py), and
[qualified build record](build-qualification-20261017.md).

## Paper-to-source correspondence

| Paper element | Actual code | Finding |
| --- | --- | --- |
| 2022 Figures 1-3 | Baseline class composition and original mixture algorithm | These explain the original framework; the new proposal is Figures 4-5. |
| 2022 Figure 4 | `SRKchungTakaMixture::cellMixture` and boundary counterpart retain weighted thermodynamics, then call `updateEoS` and `updateTRANS` | Architectural match. |
| 2022 Figure 5 | rfSpecie, SRK/PR, rfJanaf, energy mapping, transport, mixture and hePsiThermo layers | Present and selected by our case; not all available combinations have been tested. |
| 2022 Section 4.2, equations 35-39 | `realFluidReactingFoam` has species-dependent diffusion, molecular-weight/correction terms, species enthalpy diffusion in energy and inert-species closure | Main mechanisms present. This audit does not establish equality of every discrete term or historical input. |
| 2025 Figure 4 and Listing 1 | `realFluidFoam` solves species and energy inside each pressure-corrector pass; pressure equation adds explicit density/compressibility correction | Matches the defining algorithm in that executable; absent from the currently tested reacting executable. |
| 2025 Figure 5 | Shared `species::thermo::T` Newton-bisection inversion with real-fluid enthalpy derivative | Present in both active sensible-enthalpy paths, with implementation differences below. |

For the exact class/function mapping and pinned source links, see the
[thermophysical audit](thermo-architecture-audit-20261017.md).

## The two time loops are different

```text
Current realFluidReactingFoam:
time step -> continuity -> outer loop:
    momentum -> species/chemistry -> energy -> thermo.correct()
    pressure loop: pressure -> continuity -> velocity correction
    turbulence/transport correction
-> refresh stored property/diffusion fields -> write

2025 realFluidFoam:
time step -> continuity -> outer loop:
    momentum
    pressure loop:
        species -> energy -> thermo.correct()
        modified pressure -> continuity -> velocity correction
    turbulence/transport correction
-> refresh rho -> write
```

The current reacting solver places `YEqn.H` and `EEqn.H` before the inner loop
([lines 91-106](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidReactingFoam/realFluidReactingFoam.C#L91-L106)).
The turbulent solver puts them inside it
([lines 102-119](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidFoam/realFluidFoam.C#L102-L119)).
The latter's pressure equation contains
`fvc::ddt(rho) - fvc::ddt(psi,p) + fvm::ddt(psi,p)`
([lines 89-102](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidFoam/pEqn.H#L89-L102));
the reacting solver retains only `fvm::ddt(psi,p)` for this part
([lines 87-98](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidReactingFoam/pEqn.H#L87-L98)).

Simply replacing the executable would also change transport. The reacting
solver's [species equation](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidReactingFoam/YEqn.H)
and [energy equation](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidReactingFoam/EEqn.H)
explicitly use `Dimix`, molecular-weight corrections and species enthalpy fluxes.
The corresponding `realFluidFoam` files call the thermophysical transport model's
`divj` and `divq` interfaces. A change of executable therefore requires a separate
physics/settings audit; it is not just turning on the 2025 pressure correction.

## Differences that matter

The shared temperature inversion uses a maximum-iteration constant of 100,
whereas Figure 5 specifies 50. On successful Newton convergence, the source
assigns the preceding iterate to the return value; the flowchart returns the
new iterate. Newton's threshold is `T0*1e-4`, while fallback uses 50-4000 K
bounds and a 0.001 K bracket-width tolerance. The preceding-iterate detail is
consistent with our failed strict inversion tests, but its effect on the flame
results has not been isolated. See the source-linked thermophysical audit and
[existing measured inversion errors](properties-20261017.md).

The 2022 paper describes an OF6 implementation. This pinned OF8 tree was last
committed upstream on 2026-06-22 and includes the later inversion algorithm.
Use the description **2022-case replication on the pinned OF8 port**, rather
than claiming to run the exact 2022 release. Likewise, current flame convergence
would not validate the 2025 turbulent solver or its LES statistics.

## Bundled cases

There are four tracked `system/controlDict` cases: `1D_advection`,
`N2.jet.LES/c3.PR`, `N2.jet.LES/c4.PR`, and `N2.jet.LES/c3.PR.LEMOS`.
The latter three are pure-nitrogen LES setups. No 2022 counterflow/premixed case
or 2025 coaxial N2/H2 D4 case is bundled in this tree.

The [tutorial inventory](tutorial-inventory-20261017.md) records every case,
mesh, model, dependency and source link. Material preparation gaps include:
3.97 versus 3.98 MPa jet pressure; `zeroGradient` versus paper no-slip front wall;
different c3 mesh count; turbulent inlet enabled only in the external-LEMOS
variant; and averaging disabled or scheduled after the configured end time.
All four control dictionaries say `reactingFoam`, while nitrogen instructions
explicitly run `realFluidFoam`. The executable command is authoritative.

## Record and next use

The original supplied PDF pages were read and the relevant diagrams inspected
visually: 2022 pages 7-9 and 2025 pages 4-5. Source was inspected through Git
blobs to avoid Windows case collisions. This audit does not modify or interrupt
the ongoing flame runs. Preserve their baseline; version any later numerical
fix or tutorial reconciliation separately. Record this distinction in the Lark
project log before interpreting any convergence result.
