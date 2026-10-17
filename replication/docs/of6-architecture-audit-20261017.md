# OpenFOAM-6 source architecture audit, 2026-10-17

This is a static source audit of the two author-owned OF6 repositories against the supplied 2022 and 2025 papers and our OF8 source pin. No solver was changed or run for this audit. All source was read from Git objects in bare clones; no full Windows checkout was needed.

## Source pins and history

| Repository | Audited HEAD | Meaning |
| --- | --- | --- |
| `danhnam11/realFluidThermophysicalModels-6` | `61f86014ef3f4277d04a348c83777d6a20d24cf3` | Historical 2022 library/reacting solver family. |
| `danhnam11/realFluidFoam-6` | `3cc6aaca8e792c03c57011172092103b258f941c` | Later turbulent solver family, including the older reacting executable. |
| `danhnam11/realFluidFoam-8` | `48506de20ce67f35279c5347b09dcd86865a4c39` | Port used in our current qualified build. |

The historical repository's inversion and reacting-solver implementation date to [0571455, 2021-10-25, “revised to submit CPC”](https://github.com/danhnam11/realFluidThermophysicalModels-6/commit/0571455066c97a80b21c1fb1c7fbb1f529b8b08f). Its later history includes a [2022-07-01 PR EoS correction to the M expression in Cp/CpMCv](https://github.com/danhnam11/realFluidThermophysicalModels-6/commit/8e608e6be686d18e4771e1e6caced3c8b4d6627b), guide replacement in August 2022, input-data spreadsheets/documentation in March 2024, and an OF8 README in November 2024. Thus HEAD is not an untouched publication-time archive, although the relevant Newton-only implementation remains unchanged from 2021.

The later OF6 repository begins with [98200a7, 2024-07-03](https://github.com/danhnam11/realFluidFoam-6/commit/98200a713d88ef449284a039058fedd73e029469). The three subsequent commits shown by its complete local log change README material, most recently June 2026. Its substantive solver/library code is already present in the 2024 initial snapshot. These dates establish available Git provenance; they do not establish which exact commit generated either paper's figures.

## Architecture and equations

The historical OF6 library implements the 2022 Figures 4–5 architecture: composition mixing plus `updateEoS` and `updateTRANS` in `SRKchungTakaMixture`. Both OF6 families retain that structure. This agrees with the detailed OF8 mapping in [the thermophysical audit](thermo-architecture-audit-20261017.md).

All three versions of `realFluidReactingFoam` retain the 2022 ordering: momentum, species and energy in the outer PIMPLE loop, followed by the pressure-corrector loop. The OF6 sources select a separate `pcEqn.H` when `pimple.consistent()` is enabled; OF8 handles consistency within its combined pressure implementation. The current OF8 executable therefore preserves the reacting solver's broad architecture but includes OF-version API and pressure-equation implementation differences. [Historical OF6 main loop, lines 94–123](https://github.com/danhnam11/realFluidThermophysicalModels-6/blob/61f86014ef3f4277d04a348c83777d6a20d24cf3/applications/solvers/realFluidReactingFoam/realFluidReactingFoam.C#L94-L123), [OF8 reacting loop](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidReactingFoam/realFluidReactingFoam.C#L89-L112).

The later OF6 `realFluidFoam` moves species and energy into the pressure-corrector loop, matching the structural change in the 2025 modified-PIMPLE flowchart. OF8 does the same. However, **the OF6 density correction depends on the pressure branch**:

- In OF6 `realFluidFoam/pEqn.H`, the nontransonic branch includes `fvc::ddt(rho) - fvc::ddt(psi,p) + fvm::ddt(psi,p)` (lines 68–70).
- The transonic branch of that file still uses only `fvm::ddt(psi,p)` (line 33).
- With `pimple.consistent()`, OF6 instead selects `pcEqn.H`, whose two branches lack the added explicit density correction (lines 44 and 85).
- OF8 `realFluidFoam/pEqn.H` includes the real-density correction in both transonic and nontransonic branches and handles consistency in the same file.

Sources: [later OF6 main loop and branch choice](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/applications/solvers/realFluidFoam/realFluidFoam.C#L99-L125), [OF6 pEqn](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/applications/solvers/realFluidFoam/pEqn.H#L29-L75), [OF6 consistent pEqn](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/applications/solvers/realFluidFoam/pcEqn.H#L40-L90), [OF8 pEqn](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidFoam/pEqn.H#L57-L99).

This branch difference does not establish that the published 2025 LES used an affected configuration. It does mean that the statement “OF6 and OF8 implement exactly the same pressure algorithm” is too broad.

## Transport distinction remains important

The OF6 reacting solver explicitly uses species-dependent `rho*Dimix[i]`, molecular-weight-gradient terms and diffusion-flux corrections in `YEqn.H`; its energy equation includes `kappa/Cp` conduction and species enthalpy diffusion. These are the detailed transport features relevant to the 2022 laminar-flame paper and remain recognizable in the OF8 reacting implementation. [Historical species equation](https://github.com/danhnam11/realFluidThermophysicalModels-6/blob/61f86014ef3f4277d04a348c83777d6a20d24cf3/applications/solvers/realFluidReactingFoam/YEqn.H#L21-L69), [historical energy equation](https://github.com/danhnam11/realFluidThermophysicalModels-6/blob/61f86014ef3f4277d04a348c83777d6a20d24cf3/applications/solvers/realFluidReactingFoam/EEqn.H#L4-L42).

The later OF6 turbulent `realFluidFoam` instead uses `turbulence->muEff()` for species diffusion and `turbulence->alphaEff()` for energy transport. OF8 delegates those terms to `thermophysicalTransport->divj(Yi)` and `divq(he)`, making selected transport-model configuration part of the comparison. It is incorrect to infer identical species-diffusion physics merely because the same thermophysical library is linked. [OF6 turbulent species equation](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/applications/solvers/realFluidFoam/YEqn.H#L23-L30), [OF6 turbulent energy equation](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/applications/solvers/realFluidFoam/EEqn.H#L6-L21), [OF8 turbulent species equation](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidFoam/YEqn.H#L24-L29).

## Temperature inversion: three distinct implementations

| Detail | Historical OF6 library | Later OF6 solver family | Tested OF8 family |
| --- | --- | --- | --- |
| Method | Newton only | Newton, then bisection | Newton, then bisection |
| Sensible-enthalpy derivative callback | `Cp` | `dHsdT` | `dHsdT` |
| Maximum-iteration constant | 100 | 50 | 100 |
| Newton iterate-change tolerance | T0 × 1e-4 | T0 × 1e-4 | T0 × 1e-4 |
| Successful Newton return | Latest iterate | Previous iterate (`Tnew=Test`) | Previous iterate (`Tnew=Test`) |
| Fallback bracket / width | None | 50–4000 K / 1e-3 K | 50–4000 K / 1e-3 K |
| Final result clamp | Newton updates are clamped | Final `limit(Tnew)` in addition to Newton limits | No final clamp after bisection |

Sources: [historical Newton implementation](https://github.com/danhnam11/realFluidThermophysicalModels-6/blob/61f86014ef3f4277d04a348c83777d6a20d24cf3/src/thermophysicalModels/specie/thermo/thermo/thermoI.H#L41-L80), [historical derivative dispatch](https://github.com/danhnam11/realFluidThermophysicalModels-6/blob/61f86014ef3f4277d04a348c83777d6a20d24cf3/src/thermophysicalModels/specie/thermo/thermo/thermoI.H#L368-L384), [later OF6 inversion](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/src/thermophysicalModels/specie/thermo/thermo/thermoI.H#L59-L112), [later OF6 derivative dispatch](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/src/thermophysicalModels/specie/thermo/thermo/thermoI.H#L403-L419), [later OF6 constants](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/src/thermophysicalModels/specie/thermo/thermo/thermo.C#L30-L34). OF8 evidence and numerical consequences are documented in the companion audit.

The 2025 Figure 5 maximum of 50 matches the later OF6 constant, not OF8. The figure's latest-iterate output does not match either later code family's successful-Newton assignment. Therefore that discrepancy is not unique to the OF8 port. The newer method is shared by both executables within the later OF6 package, just as it is in OF8; invoking `realFluidReactingFoam` in the newer package does not restore historical 2022 inversion behavior.

## Replication implication

For a historically closer 2022 control, the old `realFluidThermophysicalModels-6` source family is the relevant comparison, with its post-publication PR correction explicitly identified. For the current OF8 campaign, retain the pinned baseline and describe it accurately as a port with later inversion changes. A separate OF6 control or isolated inversion sensitivity study could distinguish numerical-port effects from mesh, initialization and convergence effects. This audit alone does not justify switching a running campaign or declaring either version more accurate.
