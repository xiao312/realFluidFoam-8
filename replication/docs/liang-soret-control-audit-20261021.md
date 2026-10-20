# Soret control for Liang methane flames

Research record: 21 October 2026, Asia/Shanghai. State: source audited;
control not implemented or run. No flame, solver, library or input was changed.

A methane-only Soret sensitivity control is useful, provided it is labelled
as an additional approximate closure. It cannot establish Liang's PREMIX
settings. Two implementation details must be handled before a staged flame:
Cantera 3.2 rejects the `liang-staged` transport identifier when Soret is
enabled; its inherited thermal-diffusion calculation also receives the
Takahashi-corrected mixture diffusivity in Case 5 while retaining dilute
binary coefficients elsewhere in that calculation.

The journal article and dissertation Chapter 8 do not state a Soret/TDIF
setting. Text checks of the local article and PDF pages 173–188 of the
dissertation found no such declaration. Chapter 9 discusses Soret for a
different problem; those settings cannot be assigned to Chapter 8.
The article is [Liang et al., 2019](https://doi.org/10.1016/j.proci.2018.06.070).

## What Cantera 3.2 computes

The pinned source is Cantera tag `v3.2.0`, commit
`4a8358eb80cfeb50474386b5f9ec0b3a83519889`.
[`MixTransport.h`](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/transport/MixTransport.h#L45)
identifies the Chapman–Cowling approximation and its assessment by
[Zirwes and Kronenburg, 2025](https://doi.org/10.1007/s10494-025-00680-5).
That assessment concerns approximate models for hydrogen and ammonia
combustion, rather than dense methane validation. Its comparison includes
the distinct Hirschfelder–Warnatz approximation used by CHEMKIN.

The following is an algebraic transcription of the inspected
[`MixTransport.cpp`, lines 49–118](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/MixTransport.cpp#L49).
Use normalized, nonnegative physical composition for verification.
Let \(W_k\) be molecular weight in kg/kmol,
\(\bar W\) its mixture value, \(\mu_k\) species viscosity in Pa s, and
\(D^0_{kj}=B_{kj}/p\), where \(B=\mathtt{m\_bdiff}\) has units Pa m²/s.

\[
A_k=
\frac{(15/4)\mu_k/W_k}
 {1+1.065\sum_{j\ne k}X_j\phi_{kj}/X_k},
\]
\[
Q_k=\sum_{j\ne k}
 \frac{1.2C^*_{kj}-1}{D^0_{kj}(W_k+W_j)}
 (Y_kA_j-Y_jA_k),
\]
\[
U_k=D_{km}W_k\bar W Q_k,\qquad
D^T_k=U_k-Y_k\sum_iU_i.
\]

For effectively absent species the implementation sets \(A_k=0\).
The matrix \(\phi\) is the stored Wilke factor from
[`GasTransport::updateViscosity_T`](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/GasTransport.cpp#L84):

\[
\phi_{kj}=
\frac{\left[1+\sqrt{\mu_k/\mu_j}(W_j/W_k)^{1/4}\right]^2}
 {\sqrt{8(1+W_k/W_j)}}.
\]

This definition includes the factor \(1/\sqrt8\); it avoids confusing the
stored matrix with the differently normalized Wilke operator in some printed
equations. \(C^*\) uses the collision polynomial at
\(\log(k_BT/\epsilon_{kj})\). \(D^T\) has units kg/(m s), and its sum is zero.
The algorithm does not call mixture `thermalConductivity()`.

For the mole-gradient path, the ordinary coefficient is
\[
D_{km}=\frac{1-Y_k}{\sum_{j\ne k}X_j/D_{kj}}.
\]
This is `getMixDiffCoeffs`, not `getMixDiffCoeffsMole` or the mass-gradient API.
Their definitions are separate in
[`GasTransport.cpp`](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/GasTransport.cpp#L167).

## Flux and energy path

[`Flow1D::updateTransport` and `updateDiffFluxes`](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L424)
evaluate properties at arithmetic midpoint temperature and mass fractions.
The ordinary provisional flux is
\[
j_k^o=-\rho\frac{W_k}{\bar W}D_{km}\frac{\Delta X_k}{\Delta x}.
\]
It applies \(j_k^c=j_k^o-Y_{k,\mathrm{left}}\sum_i j_i^o\), then adds
\[
j_k=j_k^c-D^T_k
 \frac{2(T_{\mathrm{right}}-T_{\mathrm{left}})}
 {(T_{\mathrm{right}}+T_{\mathrm{left}})\Delta x}.
\]

All fluxes have units kg/(m² s). The Soret term uses \(D^T\), not
\(\rho D^T\), and already sums to zero at a normalized midpoint state.
Changing to a mass-gradient calculation is a separate control.

The species enthalpy term consumes the resulting total flux in
[`Flow1D::evalEnergy`](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L719).
The project's `TotalEnthalpyFlow.h` likewise includes `m_flux` in its face
enthalpy flux. This would carry Soret species enthalpy automatically; no
additional copy of that enthalpy flux should be added.

`MixTransport::getSpeciesFluxes` does not use its `grad_T` argument in this
version. Calling that API with a temperature gradient is therefore not an
independent check of FreeFlame's Soret flux. Check the explicit Flow1D
formula and its stored coefficient instead.

There is an immediate compatibility restriction:
[`Flow1D::_finalize`, lines 310–320](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L310)
allows Soret only for multicomponent transport or the exact identifiers
`mixture-averaged` / `mixture-averaged-CK`. `liang-staged` fails that check.
Any adaptation needs an explicit compatibility test and must retain the true
custom model identity in manifests and saved results. This audit did not
change or bypass the guard.

## How Case 5 changes the inherited coefficient

In the inspected project header
[`StagedTransport.h`](../development/cantera-liang/StagedTransport.h),
the inheritance is `StagedTransport` → `HighPressureGasTransport` →
`HighPressureGasTransportBase` → `MixTransport`. Neither intermediate class
overrides `getThermalDiffCoeffs`; see the pinned
[high-pressure header](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/transport/HighPressureGasTransport.h).

The inherited call to `getMixDiffCoeffs` is virtual:

| Quantity at the same \(T,p,Y\) | Case 4 | Case 5 |
|---|---|---|
| Pair \(B_{ij}\) inside the Soret sum | Dilute | Dilute |
| Pair \(C^*_{ij}\) | Stock collision fit | Same |
| Species viscosities and Wilke factors | Dilute | Same |
| \(D_{km}\) multiplying \(Q_k\) | Dilute mixture coefficient | Takahashi-corrected mixture coefficient |
| Mixture conductivity | Selected Ely–Hanley variant | Same selected variant |

`updateCorrectionFactors()` writes the separate matrix `m_P_corr_ij`;
it does not overwrite `m_bdiff`. This matches the split between coefficient
storage and corrected APIs in
[`HighPressureGasTransportBase`](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/HighPressureGasTransport.cpp).

Let \(r_k=D_{km,5}/D_{km,4}\). At a frozen state the exact inherited behavior is
\[
D^T_{k,5}=r_kU_{k,4}-Y_k\sum_i r_iU_{i,4}.
\]
Generally it is **not** \(r_kD^T_{k,4}\), because projection couples species.
Thus a Case 4/5 Soret comparison changes both ordinary and thermal diffusion.
The algorithm is computationally defined, but the combination is not
established as a validated dense-fluid Soret closure or Liang's implementation.
Takahashi's ordinary diffusion correlation alone does not establish how to
correct all thermal-diffusion collision terms.

Changing the EH conductivity formula does not directly change this frozen-state
\(D^T\). It can change the solved temperature/composition profiles and therefore
the coefficients and gradients sampled along a flame. A frozen-state property
comparison must be distinguished from that coupled effect.

## PREMIX TDIF is a different approximation

The inspected [PREMIX mirror at commit d5be29a](https://github.com/kflyfly/PREMIX/tree/d5be29a030ba891d6db1204529932079aa7b04f7/premix)
identifies itself as Sandia PREMIX 2.5b. It is an original-source artifact
hosted by a third party, not Liang's modified source release.
`RDKEY` initializes `LTDIF=.FALSE.`; the `TDIF` keyword enables it.
This establishes the archived default only.

[`MCATDR`](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/tranlib.f#L1901)
initializes every ratio to zero, then evaluates fitted pair terms for the
listed light species. Its comment claiming zero for molecular weight *less*
than five is inconsistent with the executable loop and light-species list;
the official manual resolves the intended selection.

The [Ansys theory manual, section 5.6](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/pdf/Ansys_Chemkin_Theory_Manual.pdf),
printed page 74, gives the trace-light approximation for \(W_k<5\):
\[
\theta_k=\sum_{j\ne k}\theta_{kj},\qquad
\theta_{kj}=\frac{15}{2}
\frac{(2A^*_{kj}+5)(6C^*_{kj}-5)}
 {A^*_{kj}(16A^*_{kj}-12B^*_{kj}+55)}
\frac{W_k-W_j}{W_k+W_j}X_kX_j.
\]
Its direct thermal velocity is
\[
V^T_k=-\frac{D_{km}\theta_k}{X_k}\nabla\log T.
\]
The manual describes this as a legacy approximation and recommends
multicomponent thermal diffusion when this effect matters.

[`MTRNPR` and `MDIFV`](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/premix.f#L1309)
convert it to the provisional dimensional coefficient
\[
U^{\mathrm{PREMIX}}_k
=\rho D_{km}\frac{W_k}{\bar W}\theta_k,
\]
then correct the combined ordinary and thermal flux with midpoint \(Y_k\).
The coefficient units implied by that multiplication are g/(cm s) in
this CGS source, equivalent to 0.1 kg/(m s) per CGS unit.

The [official premixed-flame section](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/chemkin_th/pgfId-1072136.html)
identifies H, H₂ and He as the directly treated species. The correction can
still change other species' fluxes. A methane flame contains H/H₂ internally,
so a light-species model need not give zero effect merely because the fuel
is CH₄. Cantera 3.2's all-species Chapman–Cowling model is not this PREMIX
approximation. Enabling a flag cannot establish numerical equivalence.

## Why exclude the Burke hydrogen extension from this first control

[`HydrogenTransport.h`](../development/liang-hydrogen/HydrogenTransport.h)
overrides `updateDiff_T()` with ten author-pair diffusion fits. It does not
install the associated \(A^*,B^*,C^*\) fits. The existing
`mechanism-source/pair-coefficients.json` records those fits in actual
\(\log T\), whereas stock collision fits use reduced temperature.

There is a further pinned-API trap:
[`setCollisionIntegralPolynomial(..., actualT)`](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/GasTransport.cpp#L837)
records `m_star_poly_uses_actualT`.
[`MultiTransport`](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/MultiTransport.cpp#L434)
honors the flag, but the inspected `MixTransport::getThermalDiffCoeffs`
always uses reduced temperature. Merely installing an actual-temperature
author fit through that setter would therefore not implement the intended
mixture Soret coefficient. This is a source-level finding; no new runtime
test was executed. Stock GRI methane transport avoids this additional
author-pair ambiguity.

## Verification and interpretation before a flame control

These are proposed checks, not completed tests or scientific acceptance:

1. Reconstruct \(A,Q,U,D^T\) independently for stock GRI states spanning
   fresh gas, preheat and reaction zones. Compare the API coefficient, units,
   and zero-sum projection. Keep raw \(U\) so the Case 5 relation can be
   checked without incorrectly scaling the already projected coefficient.
2. Verify frozen-state Case 4 equals the dilute calculation, and Case 5
   matches the virtual-dispatch expression above. At fixed composition and
   temperature, dilute \(D^T\) is pressure independent: the \(p\) in \(Q\)
   cancels the \(1/p\) in \(D_{km}\). The Case 5 correction need not cancel.
3. Exercise the actual Flow1D two-node flux: uniform \(T\) gives zero Soret
   contribution; reversing only \(\Delta T\) reverses that contribution;
   summed species mass flux remains zero. Include the custom energy path.
   Do not use `getSpeciesFluxes` as its Soret reference.
4. Preserve no-Soret outputs as the baseline. For one previously computed
   methane condition, compare Case 4 and Case 5 with Soret off/on, using the
   same chemistry, EOS, conductivity, gradient convention and refinement.
   Report \(\Delta S_4\), \(\Delta S_5\), and
   \(\Delta S_5-\Delta S_4\), not only a revised paper overlay.
5. Save coefficient and thermal/ordinary flux profiles. A small effect would
   bound this omitted mechanism for that condition. A large effect would
   justify a separate PREMIX-approximation comparison; neither outcome
   establishes which settings Liang used. Do not choose a closure because
   its flame speed happens to approach the paper.

The source audit supports this bounded methane experiment. It does not
support treating inherited Case 5 Soret as a recovered author model,
changing the production baseline, or extending the control to author-pair
hydrogen without collision-integral verification.

## Evidence identity

Project HEAD at inspection: `615f3f70d1e698cce22b87c719f05fdff8351b2c`.
The inspected Cantera source had no working-tree modifications.
SHA-256 hashes below refer to local bytes, including their existing line endings.

| File | SHA-256 |
|---|---|
| `StagedTransport.h` | `12494025ca98c421f1d945d5e27a05ed2fb6495483ee413ec224f73fdb6aa311` |
| `HydrogenTransport.h` | `0aaa6ca64c942958b2bcda8e7bdeeceb746f83f4b7ab6b7153eb9d8adcb4bde3` |
| Cantera `MixTransport.cpp` | `4288136b44fcf087efe8acfebab209cf421c46eb0e2833f2914d71d0fadff77c` |
| Cantera `Flow1D.cpp` | `c6b16e3dcc46c05738386501cd1fdf3d143c7b0cb7f858f570a291d037b56b79` |
| Cantera `MixTransport.h` | `64445389143fb2fc1f462d2e1b6cdb17b7b2fb73638d1bb85fa89d6991c864be` |
| Archived `premix-mirror.f` | `23295a68f98327493d64a743d379e72e91b4e2a42a85825c56be24d5614efd67` |
| Archived `tranlib-mirror.f` | `3ea19e78d037b6c5b2cb228988c5093b708f3277374071bdc24441775fff3377` |
| Ansys manual PDF | `4f3597887c815538e431b0bc139bb47b02a7410c55f5d41e8126ab728ae0b3d5` |

Manual page renders are under ignored
`state/liang-hydrogen-20261020/soret-audit/`; equation 5.54 was checked visually
on `chemkin-page-90.png`. Primary sources were read locally and checked at
their public URLs. No scheduler work, coefficient fitting, source changes,
author contact, or commits were performed by this audit.
