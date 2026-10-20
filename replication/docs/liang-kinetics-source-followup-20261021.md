# Liang Figure 8(b): methane subset source follow-up

21 October 2026, 04:30 Asia/Shanghai. Status: bounded source review completed;
exact Liang methane inputs unresolved. No mechanism, solver or flame job changed.

**No separately identified Liang methane subset or authored correction to
Hashemi reaction 567 was recovered.** The search added a traceable conference
precursor and checked further author archive metadata. It did not produce a
new, justified mechanism control.

## What remains established

[Liang Section 3.2](https://doi.org/10.1016/j.proci.2018.06.070) calls the USC II
and HP inputs methane sub-models, and the Hashemi input a methane
sub-mechanism. Neither the journal nor the previously recovered dissertation
provides a species list, reaction list, extraction rule or input-file hash.
That wording does not establish that a separately reduced file was used;
it can also describe a methane reaction network within a larger mechanism.
This ambiguity must remain explicit.

| Reference | Verified published input | Remaining identity limit |
| --- | --- | --- |
| 14, USC II | May 2007 author release, 111 species / 784 reactions | No separate Liang subset found; original conflicting thermo/transport entries remain documented |
| 15, HP | 2017 publisher supplement, 92 / 615 | Active records exactly match the author-page input; no separate Liang subset or prompt-on/off choice identified |
| 16, Hashemi | 2016 publisher supplement, 68 / 631 | Exact published reaction 567 has a negative aggregate rate in the preheat range; no supported correction found |

The [input inventory](liang-figure8b-mechanisms-20261020.md),
[conversion audit](liang-figure8b-implementation-audit-20261021.md), and
[HP historical comparison](liang-hp-historical-source-audit-20261021.md)
already establish those counts and qualifications. The HP publisher/archive
match closes the simple hypothesis that the current website supplied a
different full release. Downloading that release again would not test a new
kinetic model. A carbon-number truncation remains a diagnostic chosen by us,
not recovered author input.

## New primary-source leads checked

**USC author archive.** The refreshed
[Hai Wang archive page](https://web.stanford.edu/group/haiwanglab/USC%20Mech%20II/USC%20Mech%20II.html)
links the existing full kinetics, thermo and transport files, component-model
references, validation pages and updated diffusion-coefficient notes. Its
explicit download links do not name a separate methane subset. The discovered
legacy [model-release index](http://ignis.usc.edu/Mechanisms/Model%20release.html)
returned HTTP 400. No unavailable legacy page is treated as evidence that a
subset did or did not exist.

**Liang's earlier conference paper.** The official
[2018 ESSCI program](https://bpb-us-e1.wpmucdn.com/sites.psu.edu/dist/f/73916/files/2017/07/2018-ESSCI-Spring-Technical-Meeting-Program-2kmad1m.pdf),
PDF page 5, identifies presentation 1A16 by W. Liang, W. Li and C. K. Law.
The [proceedings contents](https://www.proceedings.com/content/039/039274webtoc.pdf),
PDF page 3, places the same title at printed page 95, with the next paper
starting at 101. The [Princeton publication record](https://collaborate.princeton.edu/en/publications/laminar-flame-propagation-in-supercritical-hydrogenair-and-methan-2/)
confirms the conference precursor. Its full six-page paper and calculation
inputs were not recovered. These metadata do not establish additional
mechanism detail. Liang's [faculty page](https://www.cce.tsinghua.edu.cn/en/info/1005/2826.htm)
supplies a publication-profile link but no identified 2018 input archive.

**Goldsmith author-source route.** The author's public
[RMG-database fork](https://github.com/cfgoldsmith/RMG-database) has a complete,
649-entry [tree at b734a119be1f5edba77d43ab01114edc9e69acea](https://api.github.com/repos/cfgoldsmith/RMG-database/git/trees/b734a119be1f5edba77d43ab01114edc9e69acea?recursive=1).
No path names Goldsmith, Hashemi, C2H3O2 or Princeton. This is only a path
inventory; it does not exclude a rate embedded under another library name.
It supplies no source-authenticated correction for the specified PLOG block.

The newly indexed [ACS article endpoint](https://pubs.acs.org/jpcafh/article/119/28/7766/1502747/Temperature-and-Pressure-Dependent-Rate)
still returned HTTP 403 through normal direct retrieval. Its indexed
supporting-information excerpt exposes molecular geometries and describes
the separate PLOG data, but did not expose the required rate-file bytes.
The exact DOI metadata request failed with a TLS EOF. No source hash or
coefficient comparison is claimed for an unretrieved supporting file.
The earlier [Hashemi source audit](liang-hashemi-source-followup-20261021.md)
records the other public ACS/Figshare attempts and their limits.

## Hashemi decision is unchanged

The published [Hashemi mechanism ZIP](https://ars.els-cdn.com/content/image/1-s2.0-S0010218016301766-mmc2.zip)
contains two 100-atm terms for `CH2CHOO <=> CO2 + CH3`. Their sum is negative
over 488.247846–580.129813 K, with minimum −0.404614 s⁻¹ near 554.47 K.
The [continuous-rate audit](liang-hashemi-rate-audit-20261021.md) and prior
source follow-up have already ruled out a dropped pressure node, matching
positive duplicate, reaction-header addition or implicit collider repair
in this input. The [2019 Cantera issue](https://github.com/Cantera/cantera-website/issues/77)
reports the same channel; its closure is not an author correction.

This follow-up found no published replacement coefficient set or qualified
temperature restriction that resolves that interval. A later model using a
different channel rate would be a different model. Clipping, deleting or
changing the pressure assignment would not recover the published input.

## Reproducible evidence

Ignored evidence is in
`state/liang-hydrogen-20261020/kinetics-source-followup/` relative to the project
root. `acquire.py` defaults to a read-only plan; `--apply` saves only the
listed public metadata files and refuses to overwrite originals.
`retrieval.json` records exact URLs, status, byte counts and SHA-256 values;
`search-receipt.json` records search scope, failed direct requests and limits.
Public availability is not treated as a redistribution license.

| Saved evidence | SHA-256 |
| --- | --- |
| USC release HTML | `18eccd3f213f21caa00d4d3ad772a8314b75d80973e99b74822908262ead6dea` |
| Official ESSCI program PDF | `7f36383aae8183238e6546b4c7a45930a9a9a3d08bdaeff23984a3577b1ebf1c` |
| ESSCI contents PDF | `e764a73e04ccac82102b3c42d0bcd478b6baabc79d3264a4cbb6b5b250c110ff` |
| Liang faculty HTML | `450ae28c23661024450dc78fb083b91c15245fe79b503abee20ca0eb11c38def` |
| Pinned Goldsmith repository tree | `2e32d7dcda661d59b56d21d857d372dbb13f50d1a6add8b5fa02f880634dc3db` |

The unchanged kinetic-file hashes were checked locally again:

- USC `USC_Mech_ver_II.txt`:
  `1f999b6523cb4a7f5790582ce6d85901a70f6b7e2bfa68a32b7becf1340d6f1c`.
- HP extracted `hp-chem.inp`:
  `e9a92c36cbc2c76a1367e69fea07dab0790830b92ebf53676b47f6da1f0d8bf8`.
- Hashemi original `mech.inp`:
  `20996e0d5ac1163fb28d16f7f1e343a55d64f0d7a05e6f4eaeabc40b1a9d3a7f`.

No further mechanism revision is recommended from this evidence. Recovering
an actual Liang input, an authored selection rule, or a positive original
Goldsmith channel fit with its domain would reopen the relevant question.
Current full-mechanism controls remain useful comparisons, with their
identity limits stated; they are not exact recovered Liang subsets.
