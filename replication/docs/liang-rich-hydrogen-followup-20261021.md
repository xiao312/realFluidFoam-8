# Rich-hydrogen conductivity source follow-up, 21 October 2026

**No additional equation or source implementation of Liang's rich-H2
modification was recovered.** The follow-up found a public copy of the article
on coauthor Weiyu Li's university website, the cited transport author's software
documentation, and a later high-pressure transport chapter. These sources narrow
the remaining gap; none supplies the missing mixture/conformal correction.

This is a source-retrieval result, not evidence that no implementation exists.
The April 2019 MSE thesis remains uninspected. No numerical model, flame result,
job or baseline was changed. Work used repository revision
`1dfca4b248f5eb4e7cb58beb4488f76ae79e81b7`.
The earlier [conductivity source audit](liang-conductivity-source-audit-20261021.md)
retains the dissertation/journal figure evidence; that analysis is not repeated.

## Coauthor article and MSE thesis

[Weiyu Li's Wisconsin laboratory publication list](https://less.engr.wisc.edu/publications/)
links a [public copy of the 2019 Liang article](https://less.engr.wisc.edu/wp-content/uploads/sites/908/2024/09/1-s2.0-S1540748918302530-main-2.pdf).
The downloaded PDF has seven pages, 1,232,938 bytes and SHA-256
`7d178a554990de8bcf3bc12c750526c9529ea5e1a2bb1bdf17317f551aa9fffc`.
Extracted text matches the owner-provided PDF exactly on every page. Image
counts also match, and this copy has no embedded attachments. Thus this
author-hosted copy does not add the missing formulas or an appendix. The
comparison is recorded in `author-pdf-comparison.json`; exact text identity
does not imply that the complete PDF byte streams are identical.

Princeton's [2019 degree record](https://mae.princeton.edu/sites/g/files/toruqf7696/files/2019%20-%20Class%20Day%20-%20Introduction%20of%20Graduates.pdf)
confirms Weiyu Li's MSE thesis, *Flame Dynamics in Supercritical Conditions*,
dated April 2019, with Yiguang Ju as advisor. The separately available
[November 2017 general-exam abstract](https://mae.princeton.edu/sites/default/files/Weiyu%20Li%20-%20abstract%20-Flame%20dynamics%20in%20supercritical%20condition.pdf)
names Chung K. Law and describes the progressive addition of real-fluid
effects. It is two pages and contains no conductivity equations.
The exam abstract and MSE thesis are separate records; they should not be
treated as the same document.

The current official [Princeton Thesis Central](https://theses-dissertations.princeton.edu/home)
lists master's collections from 2022 onward. That coverage cannot establish
whether a 2019 thesis was deposited or whether its full text is available
elsewhere. Exact-title searches and the author's current publication list
did not yield the full MSE thesis. The general catalog search did not render
successfully in this session. No claim of an exhaustive catalog search is made.

## Giovangigli software and later transport account

[Giovangigli's official homepage](https://www.cmap.polytechnique.fr/~giovangi/)
links [EGLIB](http://www.cmap.polytechnique.fr/www.eglib/home.html).
Its [readme](http://www.cmap.polytechnique.fr/www.eglib/readme.html) distinguishes
two distributions:

| Material | Official distribution description | Result of this retrieval |
| --- | --- | --- |
| Core transport routines | Obtain by emailing the authors; packages named EGFlib, EGMlib and EGSlib | Not requested or acquired |
| Public interface archive | Makefile, preprocessors, example, manual and agreement, via a linked FTP tarball | FTP connection timed out |
| Manual, readme and agreement | Direct web links | Downloaded and hashed |

The public archive is not described as containing the core library.
The [agreement](http://www.cmap.polytechnique.fr/www.eglib/user_ag.html)
also restricts redistribution; nothing from this package was added to the
public source tree. These pages do not establish that EGLIB includes Liang's
later rich-H2 correction.

The cited [2011 primary paper, Section 3.3 and Appendix B](https://www.cmap.polytechnique.fr/~giovangi/688.pdf)
uses a Chung high-pressure conductivity expression:

\[
\lambda=\beta\,\lambda_{\mathrm{dil}}+\lambda_{\mathrm{hp}}.
\]

Its dilute mixture conductivity comes from the kinetic-theory transport
system. It mentions similar results from Ely–Hanley, but does not supply a
hydrogen-specific modified EH mapping. Consequently, recovering that paper's
Fortran would not, by itself, recover Liang's modification.

A further primary source was downloaded from the
[author's publication list](https://www.cmap.polytechnique.fr/~giovangi/biblio_giovangigli.html):
Giovangigli, Matuszewski and Gaillard, *High Pressure Flames with
Multicomponent Transport*, in *High Pressure Flows for Propulsion Applications*
(2020), [DOI 10.2514/5.9781624105814.0485.0530](https://doi.org/10.2514/5.9781624105814.0485.0530).
The [author-hosted preprint](https://www.cmap.polytechnique.fr/~giovangi/hptransport.pdf)
has 29 pages, 849,893 bytes and SHA-256
`c7530afe6a3ce36fc0bba807bbb269d593a5c46c4be40b9df1cbc3e32b809f09`.

Section 2.6, preprint page 6, again names Chung and EH correlations for density
effects on conductivity/viscosity. It develops multicomponent diffusion
elsewhere, but does not give a rich-H2 conformal-mapping replacement.
Searching the complete extracted text found neither a Liang citation nor the
missing modification. This inspected chapter therefore supplies no additional
implementation authority for changing our EH mixture rule.

## Wang and Huo implementation route

The already acquired
[Huo 2014 paper](https://doi.org/10.1016/j.combustflame.2014.06.005)
and [Wang 2015 paper](https://doi.org/10.1080/00102202.2014.973955)
were checked for code/supplement pointers. No public source archive for the
specific property implementation was located. Wang's
[official Tsinghua page](https://www.te.tsinghua.edu.cn/info/1297/2813.htm)
lists the relevant research but supplies no matching software download.
This is a limitation of the inspected sources, not proof of closed-source
status.

An additional thesis lead was identified:
Xingjian Wang, *Swirling Fluid Mixing and Combustion Dynamics at Supercritical
Conditions*, Georgia Tech, August 2016.
The official [repository PDF](https://repository.gatech.edu/bitstreams/9ecf68fa-d183-43ab-80b1-3f78a42b6640/download)
is indexed with the correct author/title and a summary describing extended
corresponding-state transport. The original file could not be acquired:
local retrieval ended in an SSL EOF, and the web service returned HTTP 403.
Only the indexed summary was read. Its chapters, appendices and attachments
remain uninspected, so it cannot support a claim that a correction is absent.

No credentials, author contact or access-control workaround was used.
Searches for the exact modified-mixing/conformal-mapping wording in related
authored papers did not identify a further primary equation.

## Consequence for implementation

The missing information is more specific than the name “Ely–Hanley.” To
implement the asserted correction faithfully, a source must identify:

- The replacement temperature and density mapping, including mass versus
  molar conventions and reference-fluid molecular weight.
- The replacement mixture rule and any altered pair or molecular-weight
  factors.
- Whether the change applies to the internal, translational or full
  conductivity contribution.
- Its activation rule: all mixtures, hydrogen-containing mixtures, or a
  defined rich-mixture range, plus any numerical bounds or coefficients.

This list describes what our current implementation cannot infer from the
publication; it does not assert that the authors changed all four items.
Different rules can satisfy a normal-pressure hydrogen check while producing
different dense-mixture predictions. Matching one plotted flame speed would
therefore not identify the missing rule.

Keep source-supported alternatives as explicitly named diagnostic models.
Neither the recovered EGLIB pages nor the later transport chapter authorizes
renaming a generic EH variant as the exact Liang correction. The two concrete
uninspected leads remain Li's 2019 MSE thesis and Wang's 2016 dissertation.
No further baseline change follows from this retrieval.

## Evidence files

Downloads and retrieval records remain in ignored project state:

```text
state/liang-hydrogen-20261020/conductivity-source-audit-followup/
  receipts-001.json ... receipts-006.json
  author-pdf-comparison.json
  less-liang-2019.pdf
  li-exam-abstract-2017.pdf
  princeton-graduates-2019.pdf
  eglib-*.html
  eglib-manual.ps
  giovangigli-hptransport-2020.pdf
  giovangigli-hptransport-2020.txt
  search-scope.json
  manifest.json
```

The receipts include requested/final URLs, byte counts, hashes and failed
attempts. The manifest covers 30 retrieved/generated evidence files.
No result was promoted to accepted, and no model was fitted to paper curves.
