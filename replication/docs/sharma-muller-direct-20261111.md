# Direct paper diagnostics, 11 November 2026

Müller Fig. 2(b) now has a computed PR-VTA density reconstruction, displayed in
the local Forge ladder. The 129 retained temperature/composition states come from
Spitfire source ed5bacd073c16d4b00876652b252b477e83053d9, job 126412537. That
earlier run exported approximate profiles while failing its steady residual test.
The reconstruction does not change that verdict.

Density implementation source: 6587fead42ae3995a8b295207863b2f466d17848.
Profile SHA256: 3d8faaf7656e2beb847a1505a72d5f04d7a1466d0745be01df25cd0795cd4435.
The translated oxygen inlet density is 1162.74255 kg/m³ versus approximately
1177.2 kg/m³ in the paper (−1.23%). Methane is 42.38741 versus 42.8 kg/m³
(−0.96%). Maximum PR pressure residual is 1.66e−15 relative. The mixture
pseudocritical closure and minor-species estimates remain engineering assumptions;
these controls establish execution and residual consistency, not acceptance.
The local evidence directory is `state/sharma-muller-direct-20261111/prvta-r2`.
An earlier r1 used an unintended Lennard-Jones fallback for missing O2/H2O database
entries. Its report is retained; r2 supplies explicit stable-species parameters.

Sharma Figs. 1–2 use the author-deposited Zhukov–Kong mechanism from
[Mendeley version 1](https://doi.org/10.17632/rzw5tdbxgs.1), converted with Cantera
3.2 without permissive parsing. Its 51 reaction entries match the printed
appendix equations, Arrhenius, falloff and third-body data in the independent
operator audit. This does not establish identity with Sharma's unavailable Fluent
input file. Thermodynamic and transport files come from that author deposit.

The first isolated job 127665166 failed before environment preparation after four
seconds, exit 2: the operator trial root lacked the envelope's required SCOPE.txt.
No flamelet calculation occurred. The scope marker and preparation recipe were
corrected without changing the execution envelope. Adapter job 127665545 then
started at 20:24 Shanghai with two ranks, 4 GiB and a 1800-second limit. Its
frozen science source remains 6587fea even when plotting documentation advances.
The pinned adapter source is 0d2a63b546e180facdb6f1c736077517daa5c78c; the
cantera32 environment profile digest is
32504fa348f87909807cf2174b7bd015cc3c2bac6c0aaf97dc7fbcaddf8c4065.

The physical experiment independently initializes three equilibrium flamelets at
60 bar and relaxes them at χst = 1e4, 3e5 and 2e6 s⁻¹. The CO2+CO coordinate is
normalized by equilibrium at each mixture fraction. The 85 K/288 K streams,
unity Lewis number, dissipation family and integration settings are reconstruction
choices. Missing table cells stay missing. Temperature ambiguity across paths is
reported. Burnt curves are equilibrium references, not converged steady branches.
Actual execution status, coverage and comparisons must be appended after retrieval;
submission alone does not establish a computed manifold or scientific success.

## Executed outcome, 20:44 Shanghai amendment

Job 127665545 terminated FAILED, exit 1:0, after 276 seconds. Its Python import
could not find SciPy: the operator omitted the original dependency directory while
copying the patched Spitfire packages. No flamelet ran. The separate retry restored
that dependency tree and the original GCC/Cantera library search paths.

Job **127666046** completed exit 0:0 in **381 seconds**, with two allocated CPUs,
306.597 CPU-seconds and 506152 KiB maximum resident batch memory. Container and
content preparation dominated this short experiment. Actual flamelet integration
took 6.736, 7.987 and 10.434 seconds. All three reached the requested 0.001 s.
The compiled Griffon SHA256 is
01a1eb778d4e7200501ccf27e7f247ff562a3fe1c499868fe553b41f78f76d0b.
This is the retained patched runtime, not pristine upstream Spitfire.

| χst (s⁻¹) | Saved frames | Final Tmax (K) | Maximum profile change over final ≈0.1 ms (K) |
| --- | --- | --- | --- |
| 10000 | 259 | 3550.925 | 9.39e−8 |
| 300000 | 277 | 3159.784 | 1.64e−6 |
| 2000000 | 383 | 288.000 | 7.83e−8 |

The last case extinguishes. Small late profile changes are measured stability,
not an equation-residual or grid-refinement qualification. All trajectories began
independently at equilibrium. The maximum mass-sum deviation is 6.66e−16; the
dependent last species reaches a trace minimum −2.43e−10. Spitfire's existing
post-step clipping remains enabled. The runtime also warns about equilibrium
temperature outside the supplied thermodynamic fit range. Cryogenic extension
and high-temperature extrapolation remain explicit limitations.

The initial 100×100 remap covers 95.04% of cells. Its maximum temperature spread
within a 0.01-wide c bin is 567.49 K. Sorting states from several physical paths
creates visible jumps; it does not resolve a single-valued manifold. Therefore the
primary Fig. 2 comparison plots each original time-ordered path separately, with
different line patterns for χ. The mixed remap remains a separate diagnostic view.
No smoothing or parameter fitting was applied. Fig. 1 has both an equilibrium-
normalization/manifold view and a separate actual-final-profile view. The former's
c=1 line must not be mistaken for a converged solved flamelet.

Approximate raster-reference RMS for the mixed remap is 189/261/189/228 K in
temperature and 0.0190/0.0268/0.0138/0.0197 in CO2 mass fraction, at f≈0.1/0.2/0.4/0.6.
These metrics describe an unresolved diagnostic map, not an accepted FGM closure.
The nearest executed Z values are 0.098990, 0.200728, 0.402058 and 0.596628.
Paper curve extraction uses registered axes and colour selection, including a
blue-over-green constraint preventing antialiased red from contaminating pink.
The original first extraction and plots are retained as superseded evidence.

The paper's burnt temperature samples have RMS differences of 142.0 K against
our equilibrium reference and 276.6 K against the lowest-strain final profile.
The peak temperature agrees approximately, but rich-side temperatures and species
do not yet reproduce the paper. The solved low-strain CO peak is around 0.36,
while the paper shows around 0.62; the equilibrium reference is around 0.67.
This difference must be investigated through generator/energy-model and burnt-
state definitions, rather than hidden by choosing the visually closer reference.

The local Forge catalogue now displays both Sharma targets and Müller density,
retaining all 68 target IDs and original images/captions. Twelve targets have
attributable displayed results. Scientific acceptance remains unchanged.
Raw trajectories, receipts and original failed logs are retained under the isolated
SCNet trial and `state/sharma-muller-direct-20261111/` locally. The current result
pointer identifies the actual executed source/job and the independently versioned
renderer; updating a plot never changes the physical source identity.

Next scientific step: generate a deliberately selected flamelet family and
construct a reproducible branch-selection rule; verify energy/enthalpy consistency
and identify the paper's burnt-reference convention. Preserve the present failed
or approximate comparisons while those diagnostics proceed.

An additional independent Cantera final-profile audit found maximum carbon and
oxygen coordinate errors below 1.61e−10 mass fraction. Maximum enthalpy defects
against linear stream mixing were 3345.99/1584.93/697.51 J/kg across the three
branches. These are diagnostics, not a conservation pass: Cantera extrapolates
NASA polynomials while Spitfire has a distinct cold-Cp extension, and Cantera's
TPY setter normalizes/clips the signed trace inputs. The versioned audit verifies
trajectory hashes, retains its output separately and does not modify the fields.
