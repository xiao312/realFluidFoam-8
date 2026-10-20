# Liang Figure 8(b): reference readings and mechanism lineage

Research snapshot: 2026-10-21 00:45 Asia/Shanghai. Figure 8(b)'s eight curves are
now sampled from the original embedded image, with reading allowances. The public
USC-II and HP-May2017 inputs are traceable author releases, but their identity to
Liang's unspecified methane sub-models remains unverified. USC's transport file
is byte-identical to the Burke transport file already audited; eight of its
twelve appended diffusion pairs exist in USC's species set.

This note records source reading and local analysis. It does not report a new
flame solve, change a solver or select a preferred duplicate thermo record.

## Figure source and extraction

Source: [Liang et al., Figure 8(b)](https://doi.org/10.1016/j.proci.2018.06.070),
the owner's `1-s2.0-S1540748918302530-main.pdf`.
The PDF SHA256 is
`24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe`.
PDF page 6 contains no vector drawing paths for this figure. Figure 8 is image
xref 88, a 777-by-1490 JPEG, occupying PDF rectangle
`[34.614, 54.36, 221.094, 411.96]`. Its original bytes were extracted without
resampling; SHA256:
`9cc0ec5d994f528f4e1dc5bf32a47542867a1130d171b086692b04c02472d0b0`.

Evidence root, outside Git:
`state/liang-hydrogen-20261020/figure8b-reference/`.

- `figure8-native.jpg`: original embedded image, both panels.
- `extract.py`: hash-pinned, raster-only extraction.
- `digitized/reference.json`: native pixels, calibration, samples and limitations.
- `digitized/samples.csv`: sampled curve values and reading allowances.
- `digitized/overlay.png`: eight source-image overlays, one curve per panel.
- `verification.json`: inspected artifact identities and source checks.
- `usc-transport-lineage.json`: exact pair membership, coefficients and provenance.

The horizontal calibration uses pixel centers 76, 290, 504 and 718 for
equivalence ratios 0.8, 1.0, 1.2 and 1.4. Thus
`phi = 0.000934579439252336*x_px + 0.7289719626168228`.
The vertical calibration uses pixels 796, 902, 1008, 1114, 1219.5, 1325 and
1431 for 8, 7, 6, 5, 4, 3 and 2 cm/s. Thus
`SL_cm_s = -0.009451468447135701*y_px + 15.52556032566376`.
The largest vertical tick-fit residual is 0.3572 pixel.

RGB masks locate actual curve pixels. Manually read bands separate curves with
the same color; those bands supply no reported speed values. The reading
allowance combines the visible half-width, 1.5 vertical pixels and one horizontal
pixel propagated through the local slope. Interpolation across a dash gap is
labelled, includes the endpoint spread, and is allowed only for gaps no wider
than 20 pixels. This is a conservative geometric reading allowance, not a
statistical confidence interval or an allowance for errors in the paper.

The eight overlays were visually inspected: extracted points follow their
legend-assigned curves, without taking legend pixels. Occluded or missing
samples remain absent. In particular, USC Case 3 at phi 1.00 and 1.10 is
omitted, rather than inferred from the nearby black Hashemi curve. Both USC
curves have no qualified sample at phi 0.85. The other output samples span
phi 0.85-1.40 in increments of 0.05.

Representative speeds and reading allowances, in cm/s:

| Original curve | phi 1.00 | phi 1.10 | phi 1.30 |
| --- | ---: | ---: | ---: |
| GRI Case 1 | 6.887 +/- 0.043 | 7.459 +/- 0.038 | 6.622 +/- 0.043 |
| GRI Case 3 | 6.532 +/- 0.047 | 7.071 +/- 0.043 | 6.221 +/- 0.043 |
| USC Case 1 | 3.409 +/- 0.085 | 3.716 +/- 0.038 | 3.437 +/- 0.033 |
| USC Case 3 | Omitted | Omitted | 3.248 +/- 0.033 |
| HP Case 1 | 2.913 +/- 0.038 | 2.922 +/- 0.047 | 2.624 +/- 0.033 |
| HP Case 3 | 2.757 +/- 0.046 | 2.752 +/- 0.047 | 2.459 +/- 0.038 |
| Hashemi Case 1 | 3.467 +/- 0.057 | 3.551 +/- 0.033 | 3.087 +/- 0.033 |
| Hashemi Case 3 | 3.255 +/- 0.047 | 3.338 +/- 0.038 | 2.894 +/- 0.038 |

Use the CSV's method field to distinguish native-pixel interpolation from
interpolation across dashes. Case 3 here is the paper's nonideal thermodynamics
case; it is not Case 5 and must not be labelled as the full transport update.

Reproduction, with the analysis Python environment and a fresh output directory:

```text
python -B extract.py plan figure8-native.jpg new-digitized
python -B extract.py apply figure8-native.jpg new-digitized
```

The script SHA256 is
`08c795256677de5fd19b75c66249e620140cc962e4f110a78da229652ac26763`.
`reference.json` SHA256 is
`0d5e7d49c16b22046f35dd9120cf61d9960a6fba4565f216b3db30b2dde14ade`.
The earlier GRI pilot value supplied by the campaign, 7.46191398 cm/s at
phi 1.10, differs from this independent paper reading by 0.00318 cm/s.
That comparison checks this point only.

## Which methane mechanisms are established

Liang names a USC Mech 2.0 methane sub-model, an HP Mech methane sub-model and
a Hashemi methane sub-mechanism, but supplies no subset files, species counts,
reaction counts or pruning rule. The retrieved public releases therefore support
explicit full-mechanism controls. They do not prove exact paper-input identity.
See [Liang, sections 2 and 3.2](https://doi.org/10.1016/j.proci.2018.06.070).

The [USC author release](http://ignis.usc.edu/Mechanisms/USC-Mech%20II/USC_Mech%20II.htm)
is USC-II, May 2007, with 111 species and 784 reaction records. The downloaded
kinetics, thermochemistry and transport are retained under
`state/liang-hydrogen-20261020/figure8b-sources/`. The raw kinetics SHA256 is
`1f999b6523cb4a7f5790582ce6d85901a70f6b7e2bfa68a32b7becf1340d6f1c`.
This is a C0-C4 mechanism with additional aromatic chemistry, not a supplied
C1-only file. The local Cantera inventory finds 88 species with at least two
carbon atoms and the methane-recombination channel `2 CH3 (+M) <=> C2H6 (+M)`.
Removing everything above C1 would therefore remove an explicit methane
reaction pathway; it is not a justified interpretation of "methane sub-model."

USC's raw thermo has conflicting duplicate entries for `CH2CHCO` and `sC4H9`.
Its molecular transport has differing duplicates for `iC4H5` and `C4H6`
(collision diameter 5.180 versus 5.176 angstrom), and `CH3CHOCH2` (nonlinear
versus linear geometry). `C4H`, `C4H2`, `C4H2OH` and `C5H4OH` repeat identical
numeric transport values. Keep the first-record and last-record variants
distinct, with their input hashes; neither choice is established as Liang's.
`normalization.json` preserves the original text and line numbers.

The [HP author page](https://engine.princeton.edu/mechanisms/hp-mech/) is marked
18 May 2017 and cites
[Zhao, Fu, Haas and Ju, C&F 183 (2017) 253-260](https://doi.org/10.1016/j.combustflame.2017.05.005),
which is Liang's reference 15. The downloaded header cites that paper too.
The full file contains 92 species and 615 reaction records, including larger
fuels. Its raw kinetics SHA256 is
`e9a92c36cbc2c76a1367e69fea07dab0790830b92ebf53676b47f6da1f0d8bf8`.
The local inventory contains 63 C2-or-larger species and the same methyl
recombination channel. No separate author-labelled Liang methane subset was
found in the retrieved pages or files. The author page's later mechanisms are
separate releases and should not silently replace this dated input.

`hp-2017-fixed-100atm.yaml` is an explicitly restricted representation of
the author's signed PLOG terms, not a revised kinetic fit. The campaign's
`hp-fixed-100atm-validation.json` records 92 species, 616 resulting records,
3204 temperature samples over 298-3500 K, maximum rate-constant relative
difference `8.99e-15` and grouped forward-rate difference `1.12e-14`.
It also records positivity certificates for the grouped signed terms.
Its SHA256 is
`cc34fbe54bfe71c79edabc6763934bdfbe4d1046ae5e33f67ca1efae02aa9afb`.
These checks establish that pressure-specific conversion over the stated
temperature interval; they do not qualify extrapolation or exact Liang identity.

The downloaded Hashemi input remains blocked by a negative total PLOG rate
for `CH2CHOO <=> CO2 + CH3` at 100 atm over part of the preheat temperature
range. Keep that failure visible; a clipped rate would be a different model.
The exact terms and interval are in `figure8b-sources/input-validation.json`.

## USC author-pair diffusion: implementation scope

The original USC
[trandat.txt](http://ignis.usc.edu/Mechanisms/USC-Mech%20II/trandat.txt)
and Burke's
[tran.txt](https://burke.me.columbia.edu/sites/default/files/content/tran.txt)
have identical bytes and SHA256
`35c110cd2275845c4f4e4d57325cb59e4065ac7403b641cbd1cb7a3e1f6ca783`.
Thus every appended D, A-star, B-star and C-star coefficient equals the
previous Burke extraction. There is no additional USC-specific multiplier.

The first row of each four-row record supplies d0, d1, d2, d3 in

```text
Dij[m2/s] = 1e-4 * (101325/p[Pa])
           * exp(d0 + d1*ln(T[K]) + d2*ln(T[K])^2 + d3*ln(T[K])^3).
```

The natural-log polynomial gives diffusivity at 1 atm.
[Wang's author documentation](https://web.stanford.edu/group/haiwanglab/FFCM1/pages/transport.html)
states that this row suffices for mixture-averaged diffusion. The next three
rows describe collision-integral ratios for multicomponent/Soret calculations;
their argument is actual T, despite the usual reduced-temperature convention.
The fits already reflect the underlying quantum calculations; that is not
an instruction to apply another quantum factor. Neither the raw block nor
the explanation supplies an extra MIX coefficient or universal validity interval.
The cm2/s source units and inverse-pressure scaling follow the
[TRANSPORT manual, nomenclature and sections 2.5/5](https://academicweb.nd.edu/~powers/ame.60636/transport.pdf).

Exact mapping for the full USC release:

| Source line | Pair | USC treatment | Burke treatment |
| --- | --- | --- | --- |
| 178 | H-HE | Omit: HE absent | Present |
| 182 | H-H2 | Present | Present |
| 186 | H2-HE | Omit: HE absent | Present |
| 190 | H-AR | Present | Present |
| 194 | N-H2 | Omit: N absent | Omit |
| 198 | N-N2 | Omit: N absent | Omit |
| 202 | H-O2 | Present | Present |
| 206 | O-O2 | Present | Present |
| 210 | H-N2 | Present | Present |
| 214 | H2-N2 | Present | Present |
| 218 | N2-N2 | Present: self-diffusion | Present |
| 222 | H2-H2 | Present: self-diffusion | Present |

For an isolated optional diffusion control, map exact species identifiers, replace
both symmetric binary entries, and retain every other pair from the selected
ordinary transport input. Six cross-species pairs affect ordinary non-pure
mixture sums; the two diagonal entries remain relevant to pure-species fallback.
Reconstruct the declared mixture-averaged coefficient from the modified binary
matrix. Do not change the mixture definition or add Soret as part of this control.
The existing Cantera adapter stores pressure-times-diffusivity before dividing
by physical pressure, so its replacement is
`101325*1e-4*exp(polynomial)`, not D with a second pressure division.
See the previously source-audited
[Cantera application path](liang-hydrogen-mechanism-20261020.md#cantera-application-path).

This scope qualifies a named binary-diffusion-only variant. It does not establish
equivalence to every routine in the authors' modified TRANSPORT distribution,
nor justify changing viscosity or conductivity from D coefficients alone.
The first/last molecular-data choice remains part of the variant identity.
The retrieved HP transport has ordinary species rows and no appended pair block.
Applying these coefficients to HP would therefore be a separate cross-mechanism
transport sensitivity, not an established HP-author default.

Before using a generic implementation for flame comparisons, check all eight
USC mappings against the independent polynomial at fixed T and p, matrix
symmetry, the inverse-pressure ratio, an independently reconstructed mixture sum,
unchanged off-list binary pairs, and unchanged viscosity/conductivity.
Retain the original LJ-only result alongside the author-pair variant. The
source identity and formulas justify this diagnostic; only its computed results
can establish whether it improves the Figure 8(b) comparison.
