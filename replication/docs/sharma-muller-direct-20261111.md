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
