# Liang hydrogen conductivity audit, 20 October 2026

**Status: investigated; reconstruction not accepted.** The cited literature does
not supply Liang's stated modification for rich hydrogen mixtures. Two differences
from the original Ely–Hanley implementation are identifiable: our component
mapping uses SRK partial molar volumes, and our translational conductivity omits
the noncorrespondence correction. Neither is established as the cause of the
Figure 6 discrepancy. A simple change to viscosity-weighted dilute mixing actually
moves conductivity in the wrong direction in a frozen-composition check.

This audit concerns [Liang, Li and Law (2019)](https://doi.org/10.1016/j.proci.2018.06.070),
Section 2 and Figures 3/6. No solver source was changed, no flame was run, and no
paper curve was fitted. The inspected source revision was
`50566574c293abb8eaa82778d22eba82ecd08864`; the inspected files were
`liang-properties/ElyHanley.H` and `cantera-liang/StagedTransport.h`.
Paths below are relative to the outer realfluidfoam project, unless stated.

## Evidence and remaining uncertainty

Liang explicitly identifies Ely–Hanley, then says that modified mixing and
conformal mapping avoid overprediction for rich H2/air even at normal pressure.
The article supplies neither the altered equations nor constants or a distinct
reference for that alteration. The public publisher entry and searches using
the author, title and distinctive transport phrases did not reveal author
implementation files. This is a search result, not proof that no files exist.

The figure itself was checked in the supplied PDF. Figure 6 labels the black
curve `lambda_ideal/lambda_real`, and the red curve `(PD)_real/(PD)_ideal`.
The black curve is above one in the cold/preheat region. Its red curve does not
identify a species or binary pair. Thus a named H2 mixture diffusivity or H2–N2
binary coefficient cannot be silently treated as the unique paper quantity.
The current job `125069072` snapshot has a conductivity ratio of
0.85739687 at 298 K, opposite to the plotted paper trend. This value comes from
`state/liang-hydrogen-20261020/snapshot-2309/jobs/125069072/result/transport.csv`.

| Liang reference | What its primary text provides | Consequence |
| --- | --- | --- |
| [5, Pons et al. (2009)](https://doi.org/10.1080/13647830802368821), Appendix A.2 | Ely–Hanley internal/translational split and mapping; original 1981/1983 citations | Useful lineage, but no identified rich-H2 modification |
| [6, Huo et al. (2014)](https://doi.org/10.1016/j.combustflame.2014.06.005), Section 2.2 | Chung viscosity/conductivity and Takahashi diffusion | Does not specify Liang's modified Ely–Hanley model |
| [7, Wang et al. (2015)](https://doi.org/10.1080/00102202.2014.973955), formulation | Property method through Yang's general-fluid framework | No explicit H2 mapping correction found |
| [8, Juanos and Sirignano (2017)](https://doi.org/10.1016/j.combustflame.2017.01.030) | Chung conductivity/viscosity | Independent implementation, not the missing Ely–Hanley equations |
| [10, Giovangigli et al. (2011)](https://doi.org/10.1080/13647830.2010.527016), Section 3.3 and Appendix B | Chung dense conductivity, written as dilute conductivity times a correction plus a dense term; mentions comparable Ely–Hanley predictions | Provides an alternative comparison, not Liang's precise implementation |
| [18, Ely and Hanley (1983)](https://doi.org/10.1021/i100009a016) | Original corresponding-states thermal-conductivity model | Model fidelity can be checked independently of Liang's unpublished modification |

Pons's displayed mass scaling should also be treated cautiously: its expression
is not a safe substitute for the original conductivity implementation's
`sqrt(M_reference/M_effective)` direction. The original NBS program below is the
stronger authority for that implementation.

## Original mapping and derivative

[NBS Technical Note 1039](https://nvlpubs.nist.gov/nistpubs/Legacy/TN/nbstechnicalnote1039.pdf)
contains the authors' TRAPP Fortran. Printed pages 46–49 contain `DCST/ECSTX`,
and pages 58–61 contain `TCOND/THERMC`. This is an earlier complete executable
specification, not proof of which release Liang used.

With mole fractions \(x_i\), mixture molar volume \(v\), and methane reference
subscript 0, its fixed-point map is

\[
h_{ij}=\tfrac18(h_i^{1/3}+h_j^{1/3})^3,\qquad
f_{ij}=\sqrt{f_i f_j},\qquad
h_m=\sum_{ij}x_i x_j h_{ij},\quad
f_m=\frac{\sum_{ij}x_i x_j f_{ij}h_{ij}}{h_m}.
\]

Binary interaction factors exist in the original program; the equations here
show their unit-factor form. Component reduced states are

\[
t_i=\frac{f_i T}{f_m T_{c,i}},\qquad
w_i=\frac{h_i v}{h_m v_{c,i}},
\quad
f_i=\frac{T_{c,i}}{T_{c,0}}\theta(t_i,w_i),\quad
h_i=\frac{v_{c,i}}{v_{c,0}}\varphi(t_i,w_i).
\]

These are coupled conformal component states. They are not \(T/T_{c,i}\) and
the SRK partial molar volume divided by \(v_{c,i}\). `DCST` caps \(t_i\) at 2
and confines \(w_i\) to [0.5, 2]. Its displayed code does not impose our
additional 0.5 lower-temperature bound. A fixed-pressure `DCST` call also solves
the methane reference EOS at \(T_0=T/f_m,\ p_0=p h_m/f_m\); prescribing an SRK
mixture volume instead is a distinct hybrid, which should be named.

For the existing shape functions, use \(q_i=\omega_i-\omega_0\):

\[
\theta=1+q_i[0.090569-0.862762\ln t+
(0.316636-0.465684/t)(w-0.5)],
\]
\[
\varphi=\frac{Z_{c,0}}{Z_{c,i}}
\{1+q_i[0.394901(w-1.023545)
-0.932813(w-0.754639)\ln t]\}.
\]

`ECSTX` differentiates the coupled map at **fixed mixture volume and
composition**. A numerical reference should converge that map at
\((T+\delta T,v,x)\) and \((T-\delta T,v,x)\), then differentiate \(f_m\).
Holding pressure fixed produces a different derivative. Holding every SRK
partial molar volume fixed is not the fixed-mixture-volume derivative either.

An independent analytic implementation can solve the following linear system.
Define \(F_i=d\ln f_i/d\ln T,\ H_i=d\ln h_i/d\ln T\),
and analogous mixture derivatives \(F_m,H_m\). Let
\(A_i=\partial\ln\theta/\partial\ln t,\ B_i=\partial\ln\theta/\partial\ln w\),
\(C_i=\partial\ln\varphi/\partial\ln t,\ D_i=\partial\ln\varphi/\partial\ln w\).
Then

\[
(1-A_i)F_i-B_iH_i=A_i(1-F_m)-B_iH_m,
\]
\[
-C_iF_i+(1-D_i)H_i=C_i(1-F_m)-D_iH_m.
\]

Close this system by differentiating the two mixture sums above. In particular,
write \(g_i=h_i^{1/3}\),
\(H_{ij}=(g_iH_i+g_jH_j)/(g_i+g_j)\), and use

\[
H_m=\sum_{ij}\frac{x_ix_jh_{ij}}{h_m}H_{ij},\qquad
F_m=\sum_{ij}\frac{x_ix_jf_{ij}h_{ij}}{f_mh_m}
[\tfrac12(F_i+F_j)+H_{ij}]-H_m .
\]

Set the relevant logarithmic derivatives to zero when their reduced variable
is clipped. Finally \(df_m/dT=f_mF_m/T\). This system is a derivation from the
published map, not transcribed Fortran. Check it against converged central
differences, including points on either side of clipping thresholds.

The original `TCOND` multiplies the entire translational contribution by

\[
C_\lambda=
\left[
\left(1-\frac{T}{f_m}
\min\{0,(\partial f_m/\partial T)_{v,x}\}\right)
\frac{Z_{c,0}}{\sum_i x_i Z_{c,i}}
\right]^{3/2}.
\]

The original code has `PSI=1` and explicitly clamps the derivative nonpositive.
The internal contribution is not multiplied by this factor. Our implementation
omits it. A raw unbounded derivative formula is therefore not identical to the
original executable algorithm.

Do not combine reference constants from different versions without recording it:

| Constant | Current simplified implementation | TN 1039 `LIBSET` |
| --- | ---: | ---: |
| Methane \(T_c\), K | 190.4 | 190.555 |
| Methane \(v_c\), m3/kmol | 0.0986 | \(1/10.23=0.0977517107\) |
| Methane \(Z_c\) | 0.288 | 0.283742 |
| Methane acentric factor | 0.011 | 0.01131 |
| Methane molecular weight, kg/kmol | 16.04 | 16.043 |

For fresh stoichiometric H2/O2/N2 = 2/1/3.76, our species table gives
\(\sum x_iZ_{c,i}=0.2943338815\). With the current reference \(Z_c\), the
nonpositive-derivative clamp implies \(C_\lambda\ge0.9678952\).
It can reduce the translational term by at most 3.21% at that composition;
the reduction of total conductivity is smaller. Using TN 1039's reference
\(Z_c\) makes the corresponding bound approximately 0.9465. Neither bound can
alone explain the observed 0.8574 ratio versus a paper ratio above 1.05.

## Reference density and dilute baseline

The reference density is

\[
\rho_{0,\mathrm{mass}}
=M_0h_m/v
=\rho_{\mathrm{mix,mass}}h_m M_0/\overline M .
\]

This is a molar-volume mapping followed by conversion with **methane's**
molecular weight. The extra factor \(10^{-3}\) in our code converts kg/m3 to
g/cm3 for the methane correlation. Using \(\rho_{\rm mix}h_m\) without the
molecular-weight ratio is a different model, not an alternate unit convention.
`TCOND` explicitly computes its reference mass density with `CMWO`.

The current hydrogen dense-increment variant is

\[
\lambda_{\rm current}
=\lambda_{\rm Cantera,mix}
+\lambda_{\rm EH}(T,\rho,x)-\lambda_{\rm EH}(T,\rho_{\rm dilute},x).
\]

This diagnostic preserves the Cantera dilute baseline. Liang's stated need to
change predictions even at normal pressure means that this cancellation may
remove exactly the part of the model he changed. That is a reason to test
the dilute mixture independently; it does not identify his replacement.

## What a different mixing rule does

[NISTIR 6650](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir6650.pdf),
Eqs. 37–45, separates dilute and residual conductivity and applies
corresponding states only to the residual. Its dilute expression has the
Wassiljewa form
\(\lambda_m^0=\sum_j x_j\lambda_j^0/\sum_i x_i\phi_{ji}\).
Its residual model also uses fitted pure-fluid functions and interaction
parameters. Merely replacing our dilute sum is not a REFPROP reconstruction.

There is an equation-indexing ambiguity to preserve in implementation notes.
Eq. 40 prints

\[
\phi_{ji}=(1-k_{ij,\lambda})
\frac{[1+\sqrt{\eta_j^0/\eta_i^0}(M_j/M_i)^{1/4}]^2}
{\sqrt{8(1+M_j/M_i)}}.
\]

The numerator mass ratio is opposite to the usual Wilke viscosity interaction
factor, whose source implementation can be checked in
[Cantera 3.2 GasTransport.cpp](https://cantera.org/3.2/cxx/d5/de4/GasTransport_8cpp_source.html).
The monatomic relation \(\lambda_{\rm tr}\propto\eta/M\) explains why swapping
conductivity for viscosity in a Mason-type expression requires reversing that
mass factor. Do not silently "correct" the NIST expression while claiming to
implement it literally, or reuse NIST's viscosity interaction coefficients as
conductivity coefficients.

A local property-only probe held every pure-species conductivity and viscosity
fixed to the author Burke mechanism in Cantera 3.2. It set all empirical
interaction coefficients to zero. The compositions are unburnt, at 1 atm,
without chemical equilibration.

| T, K | phi | Cantera lambda, W/(m K) | Viscosity-weighted Wilke / Cantera | Literal NIST Eq. 40 / Cantera |
| --- | ---: | ---: | ---: | ---: |
| 300 | 1.0 | 0.05470295 | 1.054883 | 1.678640 |
| 300 | 1.4 | 0.06234042 | 1.076729 | 1.686990 |
| 800 | 1.0 | 0.11285708 | 1.059589 | 1.627019 |
| 800 | 1.4 | 0.12776195 | 1.080035 | 1.636648 |

The arithmetic/harmonic Mathur expression reconstructed Cantera conductivity
to relative error \(2.3\times10^{-16}\). The viscosity-weighted alternative
increases conductivity and therefore does not explain the required decrease.
These frozen-mixture results do not predict a flame-speed change quantitatively.
Evidence and exact rerun script are
`state/liang-hydrogen-20261020/conductivity-sources/mixing-probe.json` and
`mixing-probe.py`; the JSON records the mechanism hash and Cantera version.

## Hydrogen-specific reference checks

[Assael et al. (2011), DOI 10.1063/1.3606499](https://www.nist.gov/system/files/documents/srd/jpcrd402011Corr.pdf)
provides a much stronger pure-H2 check than a methane conformal extrapolation.
It distinguishes normal hydrogen (75% ortho, 25% para, the equilibrium
room-temperature composition) from pure parahydrogen. Its dilute correlation
uses quantum-mechanical calculations; its dense term is fitted to assessed
experimental data. This does not establish a Liang-specific quantum correction.
The Burke appended pair-diffusion fits are also not a conductivity model.

The normal-H2 dilute expression is
\(\lambda^0=\sum_{i=0}^{6}A_{1i}(T/T_c)^i/
\sum_{i=0}^{3}A_{2i}(T/T_c)^i\), in W/(m K), with \(T_c=33.145\) K:

```text
A1 = [-0.340976, 4.58820, -1.45080, 0.326394,
       0.00316939, 0.000190592, -0.00000113900]
A2 = [138.497, -22.1878, 4.57151, 1.0]
```

Its excess term is
\(\Delta\lambda=\sum_{i=1}^5[B_{1i}+B_{2i}T/T_c](\rho/\rho_c)^i\),
where \(\rho_c=31.262\) kg/m3:

```text
B1 = [0.0363081, -0.0207629, 0.0314810, -0.0143097, 0.00174980]
B2 = [0.00183370, -0.00886716, 0.0158260, -0.0106283, 0.00280673]
```

The full reference includes a separate critical-enhancement contribution.
The declared correlation range is from the triple point to 1000 K and up to
100 MPa. The dilute theoretical tabulation reaches 2000 K, with larger
high-temperature uncertainty; that does not extend the qualified dense range.
Table 7 gives normal-H2 checks at 298.15 K:
0.18567 W/(m K) at zero density, 0.18697 at 0.80844 kg/m3, and 0.20135 at
14.4813 kg/m3. Its pure-H2 density correction is positive at those points;
this is not evidence that an H2/air mixture's conductivity correction must
have the same sign.

Direct evaluation of the coefficients above, omitting the negligible critical
term at 298.15 K, gave 0.18567113, 0.18697235 and 0.20135443 W/(m K), consistent
with the rounded verification values. The author Burke input in stock Cantera
3.2 gave pure-H2 conductivity 0.18595621 W/(m K) at 298.15 K and 1 atm,
only 0.154% above that dilute reference. This check does not support a large
missing cold pure-H2 quantum correction in the current ideal baseline.

## Next discriminating checks

1. Compare pure H2 dilute and dense predictions with the Assael verification
   points before altering mixture rules. Separately check O2, N2 and H2O.
2. Evaluate the original coupled component mapping, the current partial-volume
   map, and each with/without the declared noncorrespondence correction at
   identical frozen \(T,p,x\). Record reference temperature/density, internal
   and translational contributions, every clipped variable, and derivative.
3. Check a 1-atm H2/air composition sweep first. A correction intended to repair
   rich hydrogen at normal pressure must be evaluated there as well as at
   100 atm. Do not tune factors to match Figure 6.
4. Only after property qualification, run the same stoichiometric and rich
   flames with one change at a time. Keep energy, kinetics, diffusion and
   flame-grid tolerances fixed. Retain the previous variant as a control.
5. Continue to label the exact rich-H2 modification and Figure 6 diffusivity
   definition unresolved. Matching a flame-speed point does not resolve them.

Local downloaded sources and rendered pages remain under
`state/liang-hydrogen-20261020/conductivity-sources/`. SHA-256:

```text
nist-tn1039.pdf
c3ea0e04a074c312f3c4852a02f5a691c3a92bde4e269691afef1fe47db6cbfa
nist-ir6650.pdf
f7fc9a9dac09a3efc34795b71680bfd50d8d8dad20421a713e7283b626c0e8e5
assael-2011-hydrogen.pdf
016a52b03aab4307fcd6c10fbc235e8250819bcb694b5648d39c7d650834ddfa
```

References 5–8/10 were read from existing local source copies, whose download
provenance is in `liang-diffusion-sources-20261020.json` and the prior diffusivity
audit. No downloaded paper or generated property data was added to Git.
