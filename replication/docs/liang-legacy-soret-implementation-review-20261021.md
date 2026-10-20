# Legacy light-species Soret implementation review

Research record: 21 October 2026, Asia/Shanghai. State: source review and
offline coefficient evaluation completed; no diagnostic solver implemented
or flame run by this audit.

A separately labelled implementation of the published CHEMKIN light-species
formula is supportable. Calling it an exact reconstruction of historical
PREMIX is not: the recovered TRANFIT 1.9 source has the opposite pair-mass
sign from the published manual, and Wang's modified interpreter is unavailable.
The sign discrepancy is present before any comparison with Liang.

This extends the [Cantera Soret control audit](liang-soret-control-audit-20261021.md).
Its official-manual formula remains correct as transcribed. Its mention of
archived PREMIX does not establish that the archived preprocessor generated
coefficients with that sign.

## The sign conflict survives the full archived call chain

The source artifact is the
[PREMIX repository at d5be29a](https://github.com/kflyfly/PREMIX/tree/d5be29a030ba891d6db1204529932079aa7b04f7).
Its files identify Sandia authors and versions, but this third-party mirror is
not an authenticated Liang or Wang release.

| Stage | Inspected behavior |
|---|---|
| [`THMFIT`, lines 545–578](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/tranfit/tranfit.f#L545) | `J` is the light output species; `K` is its partner. The mass factor is `(WT(K)-WT(J))/(WT(K)+WT(J))`. |
| `THMFIT`, lines 585–602 | Fits that signed pair factor versus actual temperature; stores it at `COFTD(:,K,NLITE)`. |
| `TRANFT`, lines 250–257; [`MCINIT`](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/tranlib.f#L225) | The link-file write/read preserves this pair and light-species ordering. |
| [`MCATDR`, lines 1959–1967](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/tranlib.f#L1959) | Here `K` becomes the listed light species; the stored partner terms are summed with positive `X(K)*X(J)`. |
| [`MTRNPR`, lines 1310–1314](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/premix.f#L1310) | Multiplies the ratio by positive `rho*D*Wk/Wbar`. |
| [`MDIFV`, lines 1456–1478](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/premix.f#L1456) | Subtracts the thermal coefficient times `grad(T)/T`, then applies the common correction velocity. |

There is no compensating sign or index swap in this chain.
The [CHEMKIN 2000 transport manual](https://academicweb.nd.edu/~powers/ame.60636/transport.pdf),
equations 51–53, and the
[2026 theory manual](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/pdf/Ansys_Chemkin_Theory_Manual.pdf),
equations 5.52–5.54, use the light-species mass minus partner mass.
The [official premixed-flame section](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/chemkin_th/pgfId-1072136.html)
also states that this convention moves light species toward hotter gas.
That physical direction is consistent with the published formula for the
binary examples below.

The March 1998 Sandia report was located through its
[indexed copy](https://citeseerx.ist.psu.edu/document?doi=0064c080beadebe49834fc242498acb00e661fb1&repid=rep1&type=pdf);
the full download failed with a transport timeout/EOF. Searches for `THMFIT`,
`WTKJ`, and a TRANFIT sign correction did not recover an authoritative erratum
or later preprocessor source. The cause of the mirror/manual difference
therefore remains unresolved. Do not silently reverse the published formula
to reproduce that mirror.

## Formula and flux contract

Use \(k\) for the output species, \(j\) for its partner, and define
\[
F_{kj}=\frac{15}{2}
\frac{(2A^*_{kj}+5)(6C^*_{kj}-5)}
{A^*_{kj}(16A^*_{kj}-12B^*_{kj}+55)},\qquad
q_{kj}=F_{kj}\frac{W_k-W_j}{W_k+W_j}.
\]
For the published light-species approximation,
\[
\theta_k=X_k\sum_{j\ne k}X_jq_{kj},\qquad
U_k=\rho D_{km}\frac{W_k}{\bar W}\theta_k,\qquad
D^T_k=U_k-Y_k\sum_iU_i,\qquad
j_k^T=-D^T_k\nabla\log T.
\]
Set direct \(\theta_k=0\) for species outside the light set. The correction
generally gives those heavier species nonzero final \(D^T_k\).
Use the mole-gradient mixture coefficient
\[
D_{km}=\frac{1-Y_k}{\sum_{j\ne k}X_j/D_{kj}}.
\]
The ratios \(F,q,\theta\) are dimensionless; \(D_{km}\) is m²/s, \(\rho\) is
kg/m³, \(D^T\) is kg/(m s), and \(j^T\) is kg/(m² s). There is no additional
density multiplier when supplying \(D^T\) to Cantera's Flow1D flux.
The expression for \(U\) avoids division by \(X_k\) when a species is absent.

The manual specifies \(W_k<5\); the recovered preprocessor uses \(W_k\le5\).
Both select exactly `H`, `H2`, `HE` in the Burke mechanism. Select by the
documented molecular-weight rule and record the resulting names. The archived
`MCATDR` comment saying the opposite weight selection is inconsistent with
its executable light-species loop.

Collision data are symmetric in the species pair. The mass factor makes
\(q_{jk}=-q_{kj}\), and self-pair terms vanish. Store author data by an unordered
pair key, then form the signed ratio for each requested output species.
Do not copy a light-species ratio into a heavy-species direct coefficient.
Two light partners each get their own oppositely signed pair term.

For a PREMIX-style discretization, the correction uses midpoint mass fractions
for the combined ordinary and thermal flux. Cantera Flow1D uses left-node mass
fractions for the ordinary correction and midpoint state for the thermal
coefficient. Implementing only the coefficient formula retains that documented
stencil difference; it is not a complete historical solver reconstruction.
See the prior audit for the energy-flux path.

## Numerical sign check with the complete collision factor

These are algebraic checks, not experimental validation. Each binary state has
1% light species and 99% N₂ by mole, 1000 K, 101325 Pa, and
\(\nabla T=+1000\) K/m. The heavy species has no direct light-species term,
but participates in the zero-total-mass-flux correction.

| Pair/data | \(6C^*-5\) | \(A^*(16A^*-12B^*+55)\) | \(q_{\mathrm{light,N2}}\), manual sign | Corrected light flux, kg/(m² s) |
|---|---:|---:|---:|---:|
| H/N₂, author fits | 0.4485566171 | 72.05026395 | −0.3218028820 | +3.92643617e−8 |
| H/N₂, stock THMFIT collision fits | 0.6686667718 | 65.88635456 | −0.5106601704 | +6.07745374e−8 |
| H₂/N₂, author fits | 0.5832513209 | 69.54934020 | −0.3986995321 | +5.88940756e−8 |
| H₂/N₂, stock THMFIT collision fits | 0.6772658633 | 66.90531279 | −0.4759004493 | +6.83081336e−8 |

All collision numerators and denominators are positive here. For the author
H₂/N₂ example, \(A^*=1.1610624993\), \(B^*=1.1396282365\),
\(C^*=0.9305418868\), \(D_{12}=6.0212143026\,10^{-4}\) m²/s,
and \(D^T_{\mathrm{H2}}=-5.8894075622\,10^{-8}\) kg/(m s).
The positive light flux goes toward hotter gas. Replacing only the mass-factor
ordering by the archived convention reverses every listed flux.

The stock rows use the exact archived collision polynomials and a positive
Cantera LJ binary diffusivity for the dimensional example. They do not claim
byte equality with historical TRANFIT's separately fitted binary diffusivity.
The author rows use the appended author diffusivity. The evidence includes
298 and 3000 K checks with the same sign outcome. These evaluate the continuum
formula before TRANFIT's additional cubic fit in actual temperature.
No assumption that all possible collision brackets have the same sign is needed.

## Author fits and the fallback are distinct inputs

[Burke's downloadable transport file](https://burke.me.columbia.edu/sites/default/files/content/tran.txt)
and [Wang's FFCM raw file](https://web.stanford.edu/group/haiwanglab/FFCM1/download/trandat-d)
have numerically identical appended blocks: 12 pair records, each with four
rows of four coefficients. Ten pairs exist in the 13-species Burke mechanism;
the two involving atomic N cannot be used there.

The first row fits \(\log D_{ij}\); the next rows fit \(A^*,B^*,C^*\) directly.
Coefficients are in ascending powers of natural \(\log(T/\mathrm{K})\).
Only the diffusion row is exponentiated:
\[
D_{ij}[\mathrm{m^2/s}]
=10^{-4}\exp\!\left(\sum_{n=0}^3d_n\log(T)^n\right)
\frac{101325}{p[\mathrm{Pa}]}.
\]
For each collision ratio use \(\sum_{n=0}^3c_n\log(T)^n\), with actual temperature,
not reduced temperature. These conventions follow the
[author's transport documentation](https://web.stanford.edu/group/haiwanglab/FFCM1/pages/transport.html).

The seven directly relevant heteropairs are H–He, H–H₂, H₂–He, H–Ar,
H–O₂, H–N₂, and H₂–N₂. O–O₂ is heavy/heavy. H₂–H₂ and N₂–N₂ have
zero self-pair mass factors. The latter records remain part of the transport
provenance even though their direct light-species Soret terms vanish.

Use the raw files, not the rounded HTML coefficient table. Its H–N₂
\(C^*\) row repeats the N₂–N₂ values. The matching raw files instead give:
`[1.27615648812, -0.22593374251, 0.04641828877, -0.00310151225]`.
At 1000 K this changes the manual H–N₂ pair factor from −0.321802882
to −0.447476034 if the HTML values are used, a 39.05% increase in magnitude.
The evidence also records the errors at 298 and 3000 K.

For pairs without author data, the recovered `THMFIT` uses its three fixed
degree-six polynomials at \(z=\log(T/E_{kj})\). Their exact coefficients are
preserved in `soret-audit/pair-formula-review.json`. Its effective well depth,
in kelvin, is
\[
E_{kj}=\xi^2\sqrt{\epsilon_k\epsilon_j},\quad
\xi=1+\tfrac14
\frac{\alpha_k}{\sigma_k^3}
\frac{\mu_j^2}{k_B\epsilon_j\sigma_j^3}
\sqrt{\frac{\epsilon_j}{\epsilon_k}},
\]
where \(k\) is the nonpolar light species. Use one consistent electrostatic
unit convention: the archived source converts polarizability to cm³, diameter
to cm, dipole to esu cm, and well energy to erg. In SI the dipole square has
the additional \(1/(4\pi\epsilon_0)\) factor. For H/H₂/He with nonpolar
partners, \(\xi=1\).

This legacy fallback uses the fixed zero-dipole collision-ratio fits plus the
effective-well-depth correction; it is not automatically identical to
Cantera's default degree-eight, pair-dependent collision fitting.
Missing author pairs such as H₂–O₂ or H–H₂O must not receive zero Soret.
The author's public description supports selective replacement of conventional
transport data. Exact fallback and refitting behavior of the modified
Wang interpreter cannot be verified because its source is not publicly supplied.

The archived fitter uses 50 equally spaced temperatures, a cubic fit of the
pair ratio versus actual \(T\), and the intersection of all species'
thermochemical ranges. For this mechanism that intersection is 300–3500 K.
This preprocessing interval does **not** establish the physical validity of
the author's actual-\(\log T\) fits, whose interval is undeclared. Evaluating
298 K is also slightly outside that legacy refitting interval.

## What this would establish

A diagnostic should identify itself as the published manual light-species
formula, with the author pair block and explicit legacy fallback when selected.
Direct evaluation of \(F\) avoids introducing an undocumented refit; record that
difference from the archived preprocessor. Required property checks include pair
permutation, self and absent-species limits, summed \(D^T=0\), gradient reversal,
and the frozen binary signs above. Coefficients and raw \(U\) must be saved so
projection errors can be distinguished from pair-model changes.

Cantera 3.2's `MixTransport` uses an all-species Chapman–Cowling approximation
with viscosity and \(C^*\), not this \(A^*,B^*,C^*\) light-species formula.
Its actual-temperature polynomial flag is not honored in that path.
The [previous audit](liang-soret-control-audit-20261021.md) covers this API trap
and the effect of Case 5's virtual mixture-diffusivity dispatch.
A legacy coefficient implementation must explicitly choose whether it uses
dilute or Takahashi-corrected \(D_{km}\) and real or ideal density. The dense
combination is a declared sensitivity closure; the ordinary Takahashi model
does not validate dense thermal diffusion.

Finally, [Burke's manuscript](https://burke.me.columbia.edu/sites/default/files/content/Burke_et_al-H2_Model_Revised_Manuscript_Submitted_7-25-11.pdf),
pages 29–31, states that its flames used the updated transport database,
modified PREMIX, multicomponent transport, and Soret. That supports the origin
of the appended data. It does not identify Liang's unstated Soret setting,
nor make a mixture-averaged diagnostic a replication of Burke's flame solver.

## Reproducible evidence

Ignored project state: `state/liang-hydrogen-20261020/soret-audit/`.
Run `review-pair-formula.py` for its read-only plan, then add `--apply` to
regenerate `pair-formula-review.json`; it performs only property/algebra checks.
The evidence uses local Cantera 3.2.0 and records mechanism/input hashes.
No source coefficients were fitted to Liang, no files outside this research
state were downloaded, and no author was contacted.

| Artifact | SHA-256 |
|---|---|
| `tranfit-mirror.f` | `5b8e217f77b7fb1bb8125db0a717ebbe681ee2acc68d7bfd1ee56ad95a48a424` |
| Burke `tran.dat` | `35c110cd2275845c4f4e4d57325cb59e4065ac7403b641cbd1cb7a3e1f6ca783` |
| FFCM `trandat-d` | `aaa4fd0f7f7af89be1f1a83b08fc6f58fe4d7fc550096ae384469d9f62460455` |
| `review-pair-formula.py` | `3aa941ee79084154ead40866021fe3243c5ee1944fefe3742514f7aaae6f4fc7` |
| `pair-formula-review.json` | `0ae6d16bb822a20d9f054efbac8a4124aaa167b3c97d85c1d5e77ac9b162328f` |

The prior audit records the unchanged archived PREMIX/TRANLIB and official
manual hashes. Repository verification for this note: UTF-8/LF and
`git diff --check`; numerical evidence exits successfully and finds all 12
raw author pair blocks equal. No scientific flame result is accepted by
these checks.
