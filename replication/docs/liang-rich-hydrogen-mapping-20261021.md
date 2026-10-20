# Liang rich-hydrogen conductivity mapping search, 21 October 2026

**Investigated; exact modification still unidentified.** No inspected source
supplies equations or coefficients for Liang's stated rich-H2 mixing and
conformal-mapping modification. Two specific thesis leads were recovered, and
a later primary paper explicitly disputes the hydrogen conductivity trend.
Neither finding authorizes changing our model to force the paper curve.

This source audit was completed at 00:52 Asia/Shanghai against documentation
revision `a21f8b1532e5bc4b3248fcec96dd876ccd234e0b`. No solver, property model,
mechanism, job, or baseline was changed. It extends the
[conductivity audit](liang-hydrogen-conductivity-audit-20261020.md); the original
Ely–Hanley/TRAPP derivation and frozen-mixture tests were not repeated.

## What remains missing

[Liang, Li and Law (2019), Section 2](https://doi.org/10.1016/j.proci.2018.06.070)
names Ely–Hanley and explains that its light-hydrogen behavior required modified
mixing and conformal mapping. The supplied seven-page article contains no
replacement equations, constants, implementation link, or separate reference
attached to that modification. Its reference 18 is Ely and Hanley (1983),
*Industrial & Engineering Chemistry Fundamentals* 22, 90,
[DOI 10.1021/i100009a016](https://doi.org/10.1021/i100009a016).
The text also does not identify whether the change affects only the dilute
mixture, the dense increment, the effective molecular weight, the reference
fluid state, or several of those terms.

The publisher page was inaccessible to direct retrieval in this session
(HTTP 403). Searches using the title, DOI, PII `S1540748918302530`, and transport
phrases did not locate a supplemental file. The
[Princeton publication record](https://collaborate.princeton.edu/en/publications/laminar-flame-propagation-in-supercritical-hydrogenair-and-methan/)
provides article metadata and the abstract, not an implementation or attachment.
Thus **no supplement was located**, rather than a verified assertion that no
supplement exists.

## Better targeted thesis leads

| Source | Verified information | What was actually read |
| --- | --- | --- |
| [Princeton MAE 2017–18 annual report, printed p. 23](https://mae.princeton.edu/document/41) | Wenkai Liang, PhD, adviser Chung K. Law; thesis *Theoretical Studies on Combustion Chemistry and Waves* | Official report text; no thesis PDF recovered |
| [Weiyu Li's Princeton general-exam abstract](https://mae.princeton.edu/sites/default/files/Weiyu%20Li%20-%20abstract%20-Flame%20dynamics%20in%20supercritical%20condition.pdf) | *Flame Dynamics in Supercritical Condition*, 10 November 2017, adviser Chung K. Law | Downloaded both pages; staged H2/air and CH4/air real-fluid flame calculations and stretched flames, but no transport equations |
| [Princeton 2019 graduate introduction](https://mae.princeton.edu/sites/g/files/toruqf7696/files/2019%20-%20Class%20Day%20-%20Introduction%20of%20Graduates.pdf) | Weiyu Li, MSE; *Flame Dynamics in Supercritical Conditions*, April 2019; adviser listed as Yiguang Ju | Downloaded four-page record; no thesis attached |

The 2017 abstract closely follows the article's staged conclusions and adds
spherical-flame/stretch work. It is therefore a particularly relevant
implementation-lineage lead. This relationship does not establish that its
unavailable full thesis contains the missing conductivity rule.

For library retrieval, a
[Kaya University catalog record](https://lib.kaya.ac.kr/search/detail/CATSAZ000000333219)
identifies Liang's dissertation as 211 pages, ProQuest, 2018,
ISBN `9780438047808`; it links to RISS record `T14998128`.
These are catalog locators, not evidence for model equations. The catalog's
truncated abstract describes three parts covering explosion limits,
low-temperature chemistry and laminar flame propagation. It is insufficient
to determine whether the supercritical-flame work appears in the full text.

Direct Princeton DataSpace search returned HTTP 401; Princeton's catalog
retrieval failed with a TLS connection error. Exact-title/author/ISBN searches
did not yield a public full-text dissertation. No institutional authentication
or author contact was attempted.

The [Tsinghua faculty profile](https://www.cce.tsinghua.edu.cn/en/info/1005/2826.htm)
confirms Liang's Princeton education and lists later work, but supplies no
transport implementation. His later
[2021 theory paper](https://doi.org/10.1080/13647830.2021.1919319) has an
[official Princeton record](https://collaborate.princeton.edu/en/publications/theory-of-supercritical-flames-with-real-fluid-equations-of-state/)
describing Van der Waals/Redlich–Kwong flame and radiation theory; that metadata
does not expose the rich-H2 mixing rule. Its full text was not retrieved, so
absence of the rule from that article has not been established.

## Later literature changes the interpretation of the mismatch

[Bai, Zhang and Zhao (2025)](https://doi.org/10.1016/j.combustflame.2025.114144),
*Combustion and Flame* 276, 114144, directly compares a Virial–Enskog model with
an RK–Ely–Hanley/Takahashi model. The publisher's indexed abstract and
introduction state that the latter overpredicts hydrogen flame speeds through
its mixture conductivity treatment. The introduction specifically challenges
Liang's reduced hydrogen flame speed after the conductivity correction, arguing
that its sign conflicts with their interpretation of NIST transport evidence.
The [publisher entry](https://www.sciencedirect.com/science/article/abs/pii/S0010218025001828)
was read through search-index text; direct retrieval returned 403 and a full
author manuscript was not recovered.

This is a published scientific disagreement, not confirmation of an error in
Liang's code. The available abstract does not prove that Bai reproduced
Liang's undocumented modification, nor does a pure-species positive density
increment establish the sign for every reacting mixture. It makes independent
mixture-property validation particularly important before treating Figure 6
as a model-development target.

A separate
[HiPrFlame author preprint](https://arxiv.org/html/2509.06717v1) discusses
Liang but does not supply his modified mapping. Its reference 23 is Ely's
1981 **viscosity** correction,
[DOI 10.6028/jres.086.028](https://doi.org/10.6028/jres.086.028), whereas Liang
cites the 1983 thermal-conductivity paper. The same viscosity reference appears
as reference 25 in the indexed
[2026 published PDF](https://ira.lib.polyu.edu.hk/bitstream/10397/118868/1/1-s2.0-S0010218026002403-main.pdf).
This citation difference does not identify an undocumented conductivity
algorithm. Do not use it as evidence that Liang applied the viscosity
correction. The downloaded preprint instead adopts Virial/Enskog transport and
its authors' own mixing framework, a different model lineage.

The existing review of references 5–8 and 10 remains applicable:
[Pons (2009)](https://doi.org/10.1080/13647830802368821) provides EH lineage;
[Huo (2014)](https://doi.org/10.1016/j.combustflame.2014.06.005),
[Juanos and Sirignano (2017)](https://doi.org/10.1016/j.combustflame.2017.01.030)
and [Giovangigli et al. (2011)](https://doi.org/10.1080/13647830.2010.527016)
use Chung formulations; the inspected
[Wang (2015)](https://doi.org/10.1080/00102202.2014.973955) formulation does not
identify Liang's change. No new appendix or source implementation linking
these works to the missing H2 rule was found.

## Consequence for the replication campaign

Keep the source-qualified EH reconstruction, the current dense-increment
diagnostic and any independently qualified alternative as explicitly different
models. None should be relabeled as Liang's exact rich-H2 implementation.
The open information gap requires at least:

1. The modified component/mixture shape functions and effective molecular
   weight definition, including units and any binary parameters.
2. The reference EOS, methane constants, derivative constraints and clipping.
3. The dilute-mixture rule and whether it is replaced, rescaled or subtracted.
4. A frozen-state check at specified H2/O2/N2 composition, temperature and
   pressure, preferably including internal and translational conductivity.

The most useful document retrievals are Weiyu Li's April 2019 MSE thesis,
Liang's identified 2018 dissertation, and Bai's 2025 full article/supplement.
Until those resolve the equations, the existing Figure 3/6 comparison should
retain its explicit implementation-identity limitation. Matching a black
paper curve by rescaling conductivity would not resolve it.

Raw evidence is outside Git under
`state/liang-hydrogen-20261020/rich-hydrogen-sources/` in the outer project.
The directory has download receipts, hashes, the two Princeton PDFs and
their text, HTML metadata, and a search-coverage record. It preserves failed
retrievals. Original article SHA-256:
`24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe`.
