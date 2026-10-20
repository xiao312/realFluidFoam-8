# Search for Liang's original PREMIX inputs

2026-10-21, 02:20 Asia/Shanghai. No author contact or access-control
workaround was attempted.

No executable modified PREMIX source or exact methane mechanism subset was
recovered in this search. This is a bounded search result, not proof that the
inputs were never published. The strongest new lead is a separate April 2019
master's thesis by coauthor Weiyu Li; its existence is confirmed by Princeton,
but its full text and any attachments remain unrecovered.

## Author and university sources

| Source inspected | What it provides | Result for the requested inputs |
|---|---|---|
| [Weiyu Li's UW–Madison publications page](https://less.engr.wisc.edu/publications/) | An entry for the exact 2019 Liang/Li/Law paper and an author-hosted article PDF | That entry links the article, not an input or code archive |
| [Author-hosted article](https://less.engr.wisc.edu/wp-content/uploads/sites/908/2024/09/1-s2.0-S1540748918302530-main-2.pdf) | Seven-page journal article | An openly accessible copy of the paper; no recovered executable input |
| [Wenkai Liang's Tsinghua faculty page](https://www.cce.tsinghua.edu.cn/en/info/1005/2826.htm) | Biography, research areas and publications | No code or mechanism-subset download link in the inspected page |
| [C. K. Law's Princeton kinetic database](https://www.princeton.edu/~cklaw/kinetics/) | Five entries for papers from 1998; page labels its update April 1999 | Genuine author-hosted kinetic resources, but no entry for this 2019 paper |
| [Princeton's 2019 graduates list](https://mae.princeton.edu/sites/g/files/toruqf7696/files/2019%20-%20Class%20Day%20-%20Introduction%20of%20Graduates.pdf) | Weiyu Li, MSE, thesis *Flame Dynamics in Supercritical Conditions*, April 2019 | Confirms a distinct thesis lead; no thesis or supplement download accompanies the entry |
| [Weiyu Li's general-exam abstract](https://mae.princeton.edu/sites/default/files/Weiyu%20Li%20-%20abstract%20-Flame%20dynamics%20in%20supercritical%20condition.pdf) | Two-page abstract dated 10 November 2017, advisor C. K. Law | Describes related planar/spherical supercritical-flame work, but contains no source or input files; it is not the 2019 thesis |

The graduate-list advisor is Yiguang Ju, whereas the earlier exam abstract names
C. K. Law. These are the records' respective statements; the search does not
infer a change in code ownership or authorship from them. Search-engine crawl
dates were not treated as publication dates.

## Public registries and code-host metadata

Read-only HTTP responses were recorded directly from the services at
2026-10-20 18:19:23–18:19:32 UTC:

| Search | Recorded outcome | Scope of the finding |
|---|---|---|
| DataCite, quoted DOI `10.1016/j.proci.2018.06.070` | HTTP 200, `meta.total=0` | No indexed record returned by that query |
| DataCite, exact article title in `titles.title` | HTTP 200, `meta.total=0` | No indexed title match returned |
| DataCite, `creators.name:"Liang, Wenkai"` | HTTP 200, five records | Two versions of a different combustion supplement and three records on other topics; none identifies this paper's inputs |
| GitHub repository search, `"Laminar flame propagation" supercritical` | HTTP 200, `total_count=0` | Repository metadata search only |
| GitHub repository search, `PREMIX supercritical` | HTTP 200, `total_count=0` | Repository metadata search only |
| GitHub repository search, `"Wenkai Liang"` | HTTP 200, `total_count=0` | Does not establish that the author has no GitHub account |

The relevant but different DataCite hit is
[a supplement for *Consolidated Description of Explosion Limits and Ignition
Delays: Hydrogen and C1–C7 N-Alkanes*](https://doi.org/10.6084/m9.figshare.27242171),
by Liu, Liang and Law. Its metadata does not connect it to the present
supercritical-flame implementation. No files from it were substituted for the
missing PREMIX inputs.

Searches combining the exact paper title/DOI with GitHub, Zenodo, Mendeley Data,
supplementary material, and PREMIX did not expose an additional matching
author archive. Unauthenticated GitHub code-content search was not performed;
the successful API checks above cannot exclude code inside an otherwise
unmatched repository.

## Access limits and reproducibility

- The [publisher article page](https://www.sciencedirect.com/science/article/pii/S1540748918302530)
  returned HTTP 403. Publisher supporting-file availability is therefore
  unresolved; no guessed supplement filename was treated as evidence.
- Princeton DataSpace searches for Wenkai Liang and the Li thesis title returned
  HTTP 401. No protected thesis or attachment was accessed.
- Direct Zenodo API requests for the DOI and exact title failed with a TLS
  unexpected-EOF error. The Crossref article-metadata request failed similarly.
  These are request failures, not zero-result searches.
- The old Princeton Law homepage's laboratory link returned 404. Its accessible
  kinetic database was inspected separately as recorded above.

The query script, raw successful/error HTTP bodies, exact URLs, response hashes
and timestamps are in
`state/liang-hydrogen-20261020/public-input-search/results/`.
`manifest.json` records each request's outcome. `search.py --plan` lists requests
without issuing them; retrieval requires a new output directory and uses no
credentials. The repository note contains no downloaded article or private data.

The unresolved source request is concrete: original modified PREMIX Fortran and
build instructions, the actual CHEMKIN input/thermo/transport files used for
Figures 3–8, and especially the USC-II and HP methane-submodel species/reaction
lists. The public full mechanisms and our explicitly labelled truncation
diagnostics remain reproducible alternatives, not authenticated author inputs.
