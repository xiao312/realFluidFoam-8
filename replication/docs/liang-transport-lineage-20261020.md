# Liang transport implementation lineage

Research record: 20 October 2026, Asia/Shanghai. State: investigated; no model
change or scientific result accepted. This follows the
[conductivity audit](liang-hydrogen-conductivity-audit-20261020.md).

Liang's planar flames used PREMIX from CHEMKIN. The ordinary mixture diffusion
formula agrees with Cantera's current mole-gradient, mass-flux path. The search
found no accessible release of Liang's modified PREMIX source, exact hydrogen
conductivity modification, or Figure 6 property evaluation code. HiPrFlame's
published supplement is accessible and useful, but describes a different
implementation and contains a demonstrable table inconsistency.

## PREMIX provenance and diffusion convention

Liang et al., DOI [10.1016/j.proci.2018.06.070](https://doi.org/10.1016/j.proci.2018.06.070),
names PREMIX in its numerical-method section and cites Kee et al.,
SAND85-8249. ASURF is not the stated solver. The supplied article contains no
source-code URL or attached algorithm listing. The publisher page was not
accessible in this search, so this does not prove that no external supplement
exists.

The official [CHEMKIN theory manual, section 13.2](https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/chemkin_th/pgfId-1072136.html)
defines the ordinary mixture-averaged diffusion velocity through

\[
D_{km}=\frac{1-Y_k}{\sum_{j\ne k}X_j/D_{kj}},\qquad
V_k^{\,o}=-\frac{D_{km}}{X_k}\nabla X_k .
\]

With thermal diffusion disabled, the mass flux is

\[
j_k^*=-\rho\frac{W_k}{\overline W}D_{km}\nabla X_k,\qquad
j_k=j_k^*-Y_k\sum_i j_i^* .
\]

Here \(X,Y\) are mole and mass fractions, respectively; \(W_k/\overline W\)
is dimensionless, \(D\) has dimensions of area/time, and \(j\) is mass/area/time.
The correction enforces zero net diffusive mass flux. Thermal diffusion is a
separate contribution.

An inspectable [PREMIX source mirror](https://github.com/kflyfly/PREMIX/tree/d5be29a030ba891d6db1204529932079aa7b04f7/premix)
contains files identifying themselves as Sandia PREMIX 2.5b, dated 4 December
1992. It is a third-party hosting of an original-source artifact, not an
authenticated release of Liang's modified solver:

- [`tranlib.f`, `MCADIF`/`MCEDIF`](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/tranlib.f#L856):
  lines 983–1001 evaluate
  \(\sum_{j\ne k}X_jW_j/[\overline W\sum_{j\ne k}X_j/D_{kj}]\);
  lines 905–906 apply reference-pressure/pressure. The documented units are
  cm²/s and dyn/cm². A small composition floor handles pure-species limits.
- [`premix.f`, `MTRNPR` and `MDIFV`](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/premix.f#L1292):
  face properties use averaged temperature and mass fractions, then convert
  those mass fractions to mole fractions. Lines 1450–1478 form the flux above
  and add its correction.
- [`RDKEY` defaults](https://github.com/kflyfly/PREMIX/blob/d5be29a030ba891d6db1204529932079aa7b04f7/premix/premix.f#L2331):
  mixture averaging and correction are on; thermal diffusion is off. A
  `TDIF` input enables thermal diffusion. These defaults do not establish
  Liang's actual input keywords.

Cantera 3.2
[`GasTransport::getMixDiffCoeffs`](https://github.com/Cantera/cantera/blob/v3.2.0/src/transport/GasTransport.cpp#L167)
has the same \(1-Y_k\) numerator.
[`Flow1D`](https://github.com/Cantera/cantera/blob/v3.2.0/src/oneD/Flow1D.cpp#L444)
uses this function for its mole-gradient path, multiplies by
\(\rho W_k/\overline W\), differences \(X_k\), then corrects the net mass flux.
`getMixDiffCoeffsMole`, with numerator \(1-X_k\), is a different API and is
not called by that path. The mass-gradient path calls
`getMixDiffCoeffsMass`, whose formula is also different; replacing only the
gradient or numerator is not an equivalent transformation.

Two discrete differences remain in these inspected versions:

1. PREMIX weights its correction by the face-averaged \(Y_k\); Cantera
   `Flow1D.cpp` lines 503–505 use the left-node \(Y_k\), although transport
   properties use midpoint values. This suggests a mesh-sensitive comparison,
   not a different continuum diffusion model.
2. PREMIX adds thermal diffusion before its correction; Cantera adds its Soret
   term afterward. This distinction is inactive when Soret is disabled.

At identical \(T,p,X\), changing \(1-Y_k\) to \(1-X_k\) cannot alter the ratio
of real to ideal \(D_{km}\): the shared numerator cancels. It can change a
flame solution and therefore the states sampled along that flame. This
algebraic distinction prevents mistaking a frozen-property ratio problem for
a flux-convention fix.

## Liang author records and source access

Princeton's [2017–2018 MAE annual report](https://mae.princeton.edu/document/41)
identifies Wenkai Liang's 2018 dissertation as *Theoretical Studies on
Combustion Chemistry and Waves*, supervised by Chung K. Law. The
[Tsinghua faculty page](https://www.cce.tsinghua.edu.cn/en/info/1005/2826.htm)
confirms his Princeton doctorate. Exact-title searches found catalog records,
but no accessible original dissertation file. Princeton DataSpace returned an
authorization error; the catalog request failed. No thesis equations are
therefore attributed or reconstructed here.

Authenticated GitHub code searches for `proci.2018.06.070`, the article's
title phrase, and `HiPrFlame`, plus repository searches for HiPrFlame and
Wenkai Liang, returned no matching source release. A known Cantera
`Takahashi` query returned source, checking that search itself worked.
These are bounded search results, not proof of nonexistence.

## What HiPrFlame actually provides

The final [HiPrFlame I article](https://ira.lib.polyu.edu.hk/bitstream/10397/118868/1/1-s2.0-S0010218026002403-main.pdf),
DOI [10.1016/j.combustflame.2026.115004](https://doi.org/10.1016/j.combustflame.2026.115004),
has an accessible [supplementary DOCX](https://ars.els-cdn.com/content/image/1-s2.0-S0010218026002403-mmc1.docx).
Its sections S2–S4 provide these implementation details:

| Item | Published description | Consequence for this replication |
|---|---|---|
| Empirical comparator | Peng–Robinson departures, Chung conductivity/viscosity, Takahashi diffusivity | Does not reveal Liang's modified Ely–Hanley rule |
| Chemistry | Ó Conaire 2004 hydrogen mechanism | Different from Liang's Burke mechanism |
| Property implementation | ANN with enthalpy, pressure and nine species fractions as inputs; 23 property outputs | No weights or training dataset obtained |
| Chemistry integration | ODE implementation based on DeepFlame v1.5 | Independent later solver lineage |
| Coupling | `thermoCorrectByTorch.H` after PIMPLE loops; `rhoCorrectByTorch.H` each time step | Algorithm outline, not executable source |
| Flame configuration | 0.56 m, 17,000 cells, refined near maximum temperature gradient; hot O₂/N₂ downstream | Different from PREMIX's steady boundary-value calculation |
| Flame speed | Front motion based on maximum temperature gradient, minus inlet velocity | Requires matching sign and frame conventions |

Supplement S12 uses a mass-gradient flux,
\[
V_i=-D_i^{mix}\nabla Y_i+Y_i\sum_jD_j^{mix}\nabla Y_j .
\]
S11 places \(\rho V_i\) directly in the species equation, while S15 writes
the enthalpy-diffusion contribution with another \(Y_i\), as
\(\rho\sum_i h_iY_iV_i\). This is an apparent notation inconsistency:
S12 already contains the mass-fraction weighting appropriate to a flux per
density. S15 also uses \(-(\lambda/C_p)\nabla h\), which needs care at varying
composition. Without source, these printed expressions cannot establish the
actual discrete energy implementation or justify copying it.

There is a directly verified input-table problem. S1 and S3 list LJ well
depths that disagree with their linked
[official Galway transport file](https://www.universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/mechanismdownloads/hydrogen/H2_transport_v1a.dat):

| Species | Supplement ε/k, K | Galway ε/k, K |
|---|---:|---:|
| N₂ | 136.5 | 97.53 |
| O | 97.53 | 80 |
| O₂ | 80 | 107.4 |
| OH | 107.4 | 80 |
| H₂O | 80 | 572.4 |
| H₂O₂ | 572.4 | 107.4 |
| H | 107.4 | 145 |
| H₂ | 145 | 38 |
| HO₂ | 38 | 107.4 |

The supplement omits the transport file's initial Ar row but retains that
row's ε/k as the first value; subsequent ε/k values are displaced by one
species. Its diameter column remains species-aligned. Both DOCX table XML
and the official input were checked. This proves a table inconsistency,
not that the calculations used these erroneous assignments.

The [arXiv source archive](https://arxiv.org/src/2509.06717) contains manuscript
TeX, bibliography and figures, not solver source or ANN weights. Its preprint
abstract reports a different enhancement magnitude from the final article;
the final article and supplement are the evidence baseline here. The
[PolyU repository record](https://ira.lib.polyu.edu.hk/handle/10397/118868?mode=simple)
lists the article PDF. The authors' [publications page](https://uhpc-lab.org/publications-2/)
did not provide implementation files. The institutional
[HiPrFlame II record](https://research.polyu.edu.hk/en/publications/hiprflame-an-ab-initio-based-real-fluid-modeling-approach-for-hig-2/)
describes a later alkane extension, DOI 10.1016/j.combustflame.2026.115264;
only its abstract was accessible, with no source obtained.

## Other public implementation and stopping point

[RGP-13-GPU at commit 5c386016](https://github.com/sunkim252/RGP-13-GPU/tree/5c386016c741e58d03c38651e5574362f5ba21ab)
provides concrete SRK, Ely–Hanley and Fuller–Takahashi code. Its
[`elyHanleyTransportI.H`](https://github.com/sunkim252/RGP-13-GPU/blob/5c386016c741e58d03c38651e5574362f5ba21ab/src/elyHanleyTransport/elyHanleyTransportI.H)
uses a Pedersen–Fredenslund mapping. No Liang lineage was established from
the inspected README and implementation. It is an independent comparison
candidate, not evidence for substituting that mapping into this replication.

The paper, author/thesis, later-paper/supplement and public-code lead families
have now been checked. No recovered source identifies Liang's hydrogen
conductivity modification or the species/composition used for Figure 6's
diffusion ratio. Further fitting to those curves would add assumptions.
The useful next evidence is a reproducible property-state definition or
the actual author implementation. No author contact was made.

## Reproduction evidence

Downloads remain outside Git under
`state/liang-hydrogen-20261020/conductivity-sources/lineage/`.
SHA-256 fingerprints of the principal files:

| File | SHA-256 |
|---|---|
| `chemkin-theory.pdf` | `4f3597887c815538e431b0bc139bb47b02a7410c55f5d41e8126ab728ae0b3d5` |
| `premix-mirror.f` | `23295a68f98327493d64a743d379e72e91b4e2a42a85825c56be24d5614efd67` |
| `tranlib-mirror.f` | `3ea19e78d037b6c5b2cb228988c5093b708f3277374071bdc24441775fff3377` |
| `Cantera-3.2-GasTransport.cpp` | `b39aa31f7b7eae7871202701392bb55c7721335ed554662a691ef5494b264cab` |
| `Cantera-3.2-Flow1D.cpp` | `a29a13580704348db06a5316d4c23e2748e4c47db4190dd2b5cdd36961936602` |
| `hiprflame-supplement.docx` | `c456750447f5e697866ca4660673e71a91349a315c872d9dabe189dac33cef97` |
| `hiprflame-arxiv-source.tar` | `d36167bc300a275db9d04887e902e60d689cf7b73dfe1ee6f1f308fd99ac6b98` |
| `galway-H2_transport_v1a.dat` | `c6474db109a027e45ce366a8d6fe5fe38cc8a029ff485e35c3e994a412958f8e` |

The full official manual was retrieved from the
[Ansys v261 PDF](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/pdf/Ansys_Chemkin_Theory_Manual.pdf).
PDF text, DOCX XML and original source were inspected; no downloaded solver
was executed. No remote jobs, commits or model-source changes were made for
this research. Verification for the note is UTF-8/LF and whitespace checking.
