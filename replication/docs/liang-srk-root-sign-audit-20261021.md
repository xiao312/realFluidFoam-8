# SRK mixture temperature-factor sign audit

2026-10-21, Asia/Shanghai. Read-only source inspection and frozen-profile analysis.

The pinned OF6 and OF8 implementations retain the signed Soave temperature
factor when constructing mixture attraction. Our Cantera extension takes its
absolute value. These expressions coincide before any participating species
crosses zero and for pure fluids, but can differ in hot mixtures. Liang's
reference 10 explicitly discusses the absolute-value interpretation and positive
alternatives; it does not justify signed continuation as Liang's implementation.
A signed-factor control would therefore test an observed upstream-code
difference, not correct an established error in the Liang reconstruction.

## What the sources specify

Define \(c_i=\sqrt{a_{c,i}}\) and
\(f_i(T)=1+m_i(1-\sqrt{T/T_{c,i}})\). The pure-fluid parameter is
\(a_i=c_i^2 f_i^2\). Its principal square root is \(c_i|f_i|\).
Liang's Eq. (2), read literally with principal square roots, gives

\[
a_{\rm principal}=\left(\sum_i X_i c_i |f_i|\right)^2.
\]

The article states the critical-state and radical-LJ parameter sources but does
not give its implementation of the temperature-factor crossing. It does not
publish a signed continuation or a temperature clamp. This limits what can be
identified from its displayed equations. [Liang et al., Section 2](https://doi.org/10.1016/j.proci.2018.06.070)

Giovangigli et al., reference 10, Section 3.1, Eq. (40) and the paragraph after
Eq. (42), explicitly use \(\sqrt{\alpha_i}=|f_i|\) for the original Soave form.
Eq. (41) truncates the factor to zero after its crossing. Eq. (43) instead uses
\(1+\tanh[m_i(1-\sqrt{T/T_{c,i}})]\) above \(T_{c,i}\), retaining the original
factor below it. The text identifies derivative jumps at the crossings as a
possible numerical problem. None of these choices extends the square root
through negative values. The manuscript's printed Eq. (42) is
\(m_i=0.48508+1.5517\omega_i-0.151613\omega_i^2\), visually checked against the
PDF; it is recorded as printed, not silently corrected. [Author manuscript,
printed pages 10–11](https://www.cmap.polytechnique.fr/~giovangi/688.pdf)

The previously tested C4 continuation is a separate later model. It does not
test the signed polynomial found in the upstream code.

## What the upstream code actually evaluates

The audited versions are:

| Repository | Pinned commit |
|---|---|
| realFluidFoam-8 | `48506de20ce67f35279c5347b09dcd86865a4c39` |
| realFluidFoam-6 | `3cc6aaca8e792c03c57011172092103b258f941c` |
| realFluidThermophysicalModels-6 | `61f86014ef3f4277d04a348c83777d6a20d24cf3` |

Both `SRKchungTakaMixture` and `SRKchungKineticMixture` precompute three
coefficients per species pair:

\[
\begin{aligned}
C_{1,ij}&=c_i c_j(1+m_i)(1+m_j),\\
C_{2,ij}&=c_i c_j\left[(1+m_j)m_i/\sqrt{T_{c,i}}
 +(1+m_i)m_j/\sqrt{T_{c,j}}\right],\\
C_{3,ij}&=c_i c_j m_i m_j/\sqrt{T_{c,i}T_{c,j}}.
\end{aligned}
\]

Each mixture coefficient is the double mole-fraction sum of its pair
coefficients. The EOS then evaluates \(a=C_1-C_2\sqrt T+C_3T\). Expanding this
expression gives

\[
a_{\rm signed}=\left(\sum_i X_i c_i f_i\right)^2.
\]

This is an algebraic inference from the source, not a comment naming the model.
When two species have opposite signs of \(f_i\), their cross term is negative;
the complete mixture attraction remains a square. There is no current-temperature
absolute value, truncation, or tanh correction in these audited coefficient and
EOS evaluation paths. OF6 reacting-mixture constructors delegate to these same
base mixture classes. [OF8 coefficient construction](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/reactionThermo/mixtures/SRKchungTakaMixture/SRKchungTakaMixture.C#L276),
[OF8 EOS](https://github.com/danhnam11/realFluidFoam-8/blob/48506de20ce67f35279c5347b09dcd86865a4c39/src/thermophysicalModels/specie/equationOfState/soaveRedlichKwong/soaveRedlichKwongI.H#L136),
[OF6 solver-family mixture](https://github.com/danhnam11/realFluidFoam-6/blob/3cc6aaca8e792c03c57011172092103b258f941c/src/thermophysicalModels/reactionThermo/mixtures/SRKchungTakaMixture/SRKchungTakaMixture.C#L228),
[OF6 library mixture](https://github.com/danhnam11/realFluidThermophysicalModels-6/blob/61f86014ef3f4277d04a348c83777d6a20d24cf3/src/thermophysicalModels/reactionThermo/mixtures/SRKchungTakaMixture/SRKchungTakaMixture.C#L228)

The upstream coefficient is
\(m_i=0.48508+1.5517\omega_i-0.15613\omega_i^2\), while our current
`SrkKernel.h` uses \(0.48+1.574\omega_i-0.176\omega_i^2\).
Changing the sign convention and these coefficients together would confound two
independent choices. The following comparison holds the current coefficients
fixed and changes only the sign convention. A second recorded calculation
holds the upstream coefficients fixed on both sides.

## Frozen hydrogen-profile measurements

All calculations use the existing critical table and completed original-alpha,
LJ-transport Case 3 profiles at 100 atm. Temperature, pressure, and composition
are frozen at every saved point. No species or energy equation is solved again.
Differences below are signed minus principal.

| φ | Job | Product Δh, J/kg | Product Δρ, % | Largest density decrease anywhere, % | Largest total Cp increase, % |
|---|---|---:|---:|---:|---:|
| 1.10 | `125071829` | +4096.15 | −0.02506 | −0.13348 | +0.86206 |
| 1.30 | `125071904` | +3875.67 | −0.03986 | −0.12322 | +0.78718 |
| 1.40 | `125069094` | +3741.18 | −0.04601 | −0.11925 | +0.75714 |

The maximum Cp differences occur just above the N2 factor crossing near
1023.56 K. The largest density changes occur around 1596–1605 K.
At the products, attraction changes by −23.97%, −40.45%, and −47.89%;
these percentages describe a small attractive contribution at flame temperature,
not comparable percentage changes in density or flame speed.

At all three inlets the difference is zero. Dividing the product enthalpy
offset by product Cp gives an approximate fixed-composition, constant-enthalpy
temperature shift of −2.31, −2.09, and −1.97 K. This is opposite to the correction
needed for the currently low burned temperatures. It is not an equilibrated
endpoint or a flame-speed prediction. The upstream-coefficient sign-only product
enthalpy differences are +4178.28, +3816.69, and +3635.76 J/kg, respectively.

The signed mixture sum \(q=\sum X_i c_i f_i\) becomes negative in every profile:
its minimum is −184.52, −152.20, and −137.82 in the kernel's molar-SI square-root
attraction units. This matters to a possible implementation: the present
fugacity expression's `q > 0` guard is only valid for the principal-root model.
For signed factors, rewrite its attraction contribution without division by q:

\[
\frac{A}{B}\left(\frac{2s_i}{q}-\frac{b_i}{b}\right)
=\frac{2q s_i-q^2 b_i/b}{bRT}, \qquad s_i=c_i f_i.
\]

This expression also has the correct zero-q limit. A signed-factor diagnostic
must propagate the same factors through attraction, derivatives, partial
enthalpies, and fugacity; changing only `abs` while retaining that guard would
introduce a separate inconsistency. Pure-fluid properties are unchanged by the
sign choice, so a Figure 1 pure-methane test cannot discriminate it.

## Evidence and verification

Local state is `state/liang-hydrogen-20261020/root-sign-audit/` under the project
workspace. `audit.py` reads immutable Git objects and existing profiles, writes
source copies and every frozen state to a new output directory, and rejects an
existing destination. `results-2/audit.json` is the final evidence manifest.
`results/` preserves the first successful calculation before adding a
cancellation-aware polynomial verification metric.

Verification passed:

- Baseline mixture enthalpy reconstructs saved values within \(3.0\times10^{-9}\) J/kg.
- Signed-square and expanded-polynomial attraction agree within
  \(1.93\times10^{-16}\) of the sum of absolute polynomial terms. Relative
  error against the nearly cancelled result alone can reach \(1.80\times10^{-10}\).
- Analytic Cp agrees with a ±0.001 K enthalpy finite difference within
  \(1.49\times10^{-8}\) J/(kg K) at sampled states.
- Pure-fluid attraction, its first two derivatives, departure enthalpy and Cp
  agree exactly for both signs at 298, 800, 1500, 2500 and 3500 K for all 13 species.

Profile SHA-256 values, in table order:

```text
8542778bbbca439a3e172d1ebceb442ad3c37c4f7d6347e304ad44a77b7b6f4d
bb83c6e2ab1d52b98e0ad7d2c26a54b41847130569084617e3a31ad952bcad32
8e76f5711e4a1d63391f7e1318daa57e08f2a41e7a55deaf13d97a9a97e1d79f
```

The source manifest records each repository commit, extracted-file SHA-256 and
relevant line numbers. Reference 10 PDF SHA-256:
`0e93e18d404857f37b49044813dc5adf799781e87735e34f357a3b8171a256c5`.
The comparison supports a named upstream-code sensitivity test. It does not
identify Liang's unpublished implementation or justify replacing the baseline.
