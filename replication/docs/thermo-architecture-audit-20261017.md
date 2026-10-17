# Thermophysical architecture audit, 2026-10-17

Scope: static inspection of upstream source commit `48506de20ce67f35279c5347b09dcd86865a4c39`, the source pin used by the qualified build. Paper evidence is the supplied 2022 CPC 108264 PDF (Sections 3–4, Figures 4–5) and 2025 CPC 109600 PDF (Section 3.3, Figure 5). The relevant original figure crops were also inspected visually. This audit establishes source correspondence, not convergence or numerical validation.

## Finding

The tested thermophysical stack implements the 2022 architecture, and its shared temperature inversion already incorporates the Newton–bisection algorithm described in 2025. The current counterflow executable is nevertheless `realFluidReactingFoam`, not the 2025 turbulent solver `realFluidFoam`. Sharing this library does not make the two solver algorithms identical. Several inversion details differ from the 2025 flowchart and deserve explicit qualification.

## 2022 Figures 4 and 5: implementation mapping

The counterflow generator selects `hePsiThermo / SRKchungTakaMixture / chungTaka / rfJanaf / sensibleEnthalpy / soaveRedlichKwong / rfSpecie` (local `replication/validation/flames/generate_counterflow.py`, lines 47–48).

| Paper element | Pinned implementation | Assessment |
| --- | --- | --- |
| Figure 4: mass-fraction weighted ideal thermodynamics followed by model-specific parameter updates | `SRKchungTakaMixture::cellMixture` first uses `*` and `+=`, converts mass to mole fractions, evaluates mixing parameters, then invokes `updateEoS` and `updateTRANS` | Direct architectural match. The paper does **not** remove all overloaded operators: they remain for the ideal thermodynamic portion. |
| Figure 4: separate EoS and transport mixing rules | EoS update receives `bM, coef1, coef2, coef3`; transport receives Chung parameters, composition, and binary diffusion arrays | Direct match, with implementation-specific argument decomposition. |
| Figure 5: composed species → EoS → thermo → energy mapping → transport stack | `forSRKchungTakaGases.H` combines `rfSpecie`, `soaveRedlichKwong`, `rfJanafThermo`, sensible enthalpy/internal energy and `chungTakaTransport` | Direct class-composition match. Current cases exercise the sensible-enthalpy selection only. |
| Real-fluid JANAF model | `rfJanafThermo::Cp` and `Ha` add EoS departure contributions; `Hs=Ha-Hf` | Corresponds to Section 4.1. |
| Mixture-averaged diffusion | `hePsiThermo::calculate` obtains each species' `Dimix` from the mixture transport object | Matches the added diffusion interface; this is active in the tested psi thermo path. |

Sources: [mixture update sequence, lines 366–455](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/reactionThermo/mixtures/SRKchungTakaMixture/SRKchungTakaMixture.C#L366-L455), [type composition, lines 30–53](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/include/forSRKchungTakaGases.H#L30-L53), [JANAF properties, lines 170–235](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/thermo/rfJanaf/rfJanafThermoI.H#L170-L235), [property and diffusion update, lines 31–63](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/basic/psiThermo/hePsiThermo.C#L31-L63).

Boundary mixtures repeat the EoS and transport updates (`patchFaceMixture`, lines 461–551). This matters because the architecture covers inlet/outlet faces as well as interior cells. The mixture constructor precomputes species-pair coefficients; the per-cell routine updates composition-dependent coefficients. No comparison here establishes that all twenty combinations mentioned in the 2022 paper have been exercised.

## Actual temperature-retrieval call path

Both solver `createFields.H` files instantiate `psiReactionThermo::New(mesh)`. Both energy equations invoke `thermo.correct()` after solving energy. For our selected `hePsiThermo` and `sensibleEnthalpy`, the path is:

```text
EEqn.H: thermo.correct()
  hePsiThermo::correct() -> calculate()
    cellMixture(celli) -> mixture_.THE(h,p,T_previous)
      species::thermo::THE -> sensibleEnthalpy::THE
        thermo.THs -> species::thermo::T(Hs,dHsdT,limit)
          Newton iteration; bisection fallback
```

Sources: [reacting energy call, line 43](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidReactingFoam/EEqn.H#L43), [turbulent solver energy call, line 32](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/applications/solvers/realFluidFoam/EEqn.H#L32), [hePsiThermo correction, lines 200–210](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/basic/psiThermo/hePsiThermo.C#L200-L210), [sensible enthalpy dispatch, lines 107–115](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/thermo/sensibleEnthalpy/sensibleEnthalpy.H#L107-L115), [THE and THs, lines 432–460](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/thermo/thermo/thermoI.H#L432-L460).

`rfJanafThermo::dHsdT` evaluates the ideal JANAF polynomial plus `EquationOfState::dHdT`. SRK supplies that departure derivative, so the sensible-enthalpy path does use the paper's changed derivative rather than its ordinary `Cp` callback. The alternative absolute-enthalpy `THa` and internal-energy `TEs/TEa` paths still pass `Cp` or `Cv`; these are not the active counterflow energy choice. [Derivative implementation](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/thermo/rfJanaf/rfJanafThermoI.H#L225-L235), [SRK derivative](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/equationOfState/soaveRedlichKwong/soaveRedlichKwongI.H#L149-L155), [other energy paths](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/thermo/thermo/thermoI.H#L464-L520).

## 2025 Figure 5: exact correspondence and differences

| Detail | Figure 5 / Section 3.3 | Pinned implementation |
| --- | --- | --- |
| Newton start and stopping tolerance | Previous temperature; epsilon = T0 × 1e-4 | Matches. This is an iterate-change test, not an enthalpy residual test. |
| Maximum iterations | 50 | `maxIter_ = 100`; the break is tested after increment with `iter > maxIter_`, so it can perform 101 Newton updates. |
| Successful Newton output | Return the latest `Tnew` | If change is strictly below tolerance, code assigns `Tnew = Test`, returning the previous iterate. This is a substantive discrepancy. |
| Equality at tolerance | Flowchart accepts change <= epsilon | Loop stops at equality but subsequent strict `<` check fails, sending that edge case to bisection. |
| Newton range constraint | Constrain temperature to thermo range | Matches via `limit`; rfJanaf clamps to Tlow/Thigh and warns. |
| Bisection bounds and stopping width | 50 K, 4000 K, width 1e-3 K | Matches. |
| Bisection constraint and counter | Figure draws a range-constraint block and an iteration counter | Code uses a fresh counter `n=0` and no `limit` call in the bisection loop. The figure's right-side constraint text refers to `Tnew`, so its intent is not completely clear. |
| Final fallback output | Midpoint of final bracket | Matches. |

Sources: [inversion implementation, lines 54–180](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/thermo/thermo/thermoI.H#L54-L180), [constants, lines 30–34](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/thermo/thermo/thermo.C#L30-L34), [temperature limit, lines 110–129](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/thermo/rfJanaf/rfJanafThermoI.H#L110-L129).

Neither the drawn fallback nor this implementation verifies an initial sign-changing bracket or tests final enthalpy residual. The code also lacks an explicit finite-value check in this routine. Therefore, the paper's broad convergence wording should not be treated as a mathematical guarantee for arbitrary states. In particular, a shrinking interval alone does not certify a root when the target enthalpy is outside the bracket's range.

At T0=1800 K, the Newton iterate-change threshold is 0.18 K. Returning the preceding iterate can therefore matter to strict inversion checks even when the solver's own test passes. This is consistent with the already recorded strict thermodynamic inversion qualification, but this static audit does not quantify the effect on the counterflow results.

## Consequence for replication

Describe these runs as a replication attempt of the 2022 cases using the pinned OpenFOAM-8 port and its newer shared thermophysical library. Do not describe the executable as an untouched 2022 release or infer that successful counterflows validate the 2025 modified PIMPLE/turbulence solver. Preserve the current source baseline while measuring convergence. Any later change to inversion tolerance, returned iterate, bracket checks or solver coupling should be a separately versioned sensitivity study.
