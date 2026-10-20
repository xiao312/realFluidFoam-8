# Full USC/HP Case 3: critical-property prescription follow-up

21 October 2026, Asia/Shanghai. Source investigation completed; no new
critical table, solver change or flame job.

**The examined sources do not supply a complete, unambiguous Liang
Tc/Pc/omega prescription for the full USC or HP mechanisms.** All author
species have positive Lennard–Jones inputs, so a declared approximate table
is technically possible. Recovering the publication input is a different
task: the major/minor species split, radical acentric factors, some stable
species properties and lumped-species closures remain unspecified.

This follows the [critical-input inventory](liang-mechanism-critical-input-audit-20261021.md).
The [HP publication identity check](liang-hp-historical-source-audit-20261021.md)
is unchanged.

## What the cited sources provide

| Source | Reproducible information | Remaining limit |
|---|---|---|
| Liang, Section 2 | Major-species critical-state construction; LJ estimates for minor species; methane NOx EOS parameters omitted | No complete species table, major/minor membership, radical omega policy or explicit alpha continuation |
| Ref. 5, Pons et al., Sections 2 and appendix | Peng–Robinson equations, alpha expression, and O2/CH4/H2 critical data | A different EOS; no full USC/HP species prescription |
| Ref. 6, Huo et al., Section 2.2 | SRK framework and references to property methods | No per-species radical or acentric-factor table |
| Ref. 7, Wang et al., formulation and Table 1 | Critical properties of O2, H2 and selected n-alkanes | Reactant table only; no complete minor-species inputs |
| Ref. 8, Jordà Juanós and Sirignano, Section 3 | Stable/metastable critical data attributed to Prausnitz et al.; LJ estimates for unstable species; explicit alpha expression | No complete species table or radical omega assignment |
| Ref. 10, Giovangigli et al., Section 3.1 | LJ-derived pseudo-critical scales, attraction and covolume; temperature-factor alternatives | No complete USC/HP table and no numerical omega assignment for every unstable species |

Primary sources:
[Liang](https://doi.org/10.1016/j.proci.2018.06.070);
[Pons, author copy](https://yang.gatech.edu/publications/Journal/CTM%20%28Pons%2C%202009%29.pdf);
[Huo, author copy](https://yang.gatech.edu/publications/Journal/C%26F%20%282014%2C%20Huo%29%20-%20S%20curve.pdf);
[Wang, author copy](https://yang.gatech.edu/publications/Journal/CST%20%282015%2C%20counterflow%20flames%2C%20Wang%29.pdf);
[Jordà Juanós and Sirignano, author copy](https://sirignano.eng.uci.edu/theme/pdfs/39.pdf);
[Giovangigli, author manuscript](https://www.cmap.polytechnique.fr/~giovangi/688.pdf).

These papers do not all use the same thermodynamic model. A citation to this
group therefore cannot select one complete implementation.

## LJ conversion does not close the alpha choice

Using Avogadro's constant N in molecules/kmol, sigma in metres and epsilon
in J/molecule, reference 10's Eqs. 38–39 give the molar central estimates

```text
Tc = 1.316 epsilon/kB
Vc = 3.29 N sigma^3
ac = 5.55 N^2 epsilon sigma^3
b  = 0.855 N sigma^3.
```

These define a temperature scale and two EOS coefficients. They do not
determine a vapor-pressure curve or a unique acentric factor. The existing
inventory already documents the small rounding difference when encoding
these rounded coefficients through a Tc/Pc-only SRK interface.

Reference 10 then uses `a(T)=ac alpha(T/Tc)`. Its printed Eq. 42 has
`s=0.48508+1.5517 omega-0.151613 omega^2`; Eq. 43 uses
`sqrt(alpha)=1+tanh[s(1-sqrt(T/Tc))]` above Tc and the linear factor below
Tc. Both were visually checked. Ref. 8 instead prints the unmodified
factor and the coefficient `-0.15613 omega^2`. Neither passage explicitly
sets all radical omega values to zero. The earlier
[temperature-factor audit](liang-srk-root-sign-audit-20261021.md) records
these differences; no coefficient or continuation was changed here.

There is independent primary-source precedent for zero omega:
Ruiz et al.'s 2011 CERFACS report explicitly uses zero for its H/O/OH/HO2/H2O2
entries. Banuti et al.'s 2018 conference paper also explicitly adopts zero
for intermediate species. This makes `omega=0` a published modeling
convention, not a value derived from Eq. 39 or proof of Liang's choice.
The former uses Peng–Robinson and a small hydrogen mechanism; neither
publishes the missing full USC/HP prescription.
[CERFACS report, Section 2 and Table 1](https://www.cerfacs.fr/~cfdbib/repository/TR_CFD_11_114.pdf);
[Banuti et al., pages 3–4](https://sco2symposium.com/papers2018/oxy-combustion/149_Paper.pdf).

Ref. 8's displayed Eq. 16 also prints one N, rather than N squared, in
the molar attraction estimate. With its stated molecular epsilon units,
that expression is dimensionally inconsistent with molar `ac`; reference
10's mass-to-molar conversion supplies N squared. This is another reason
to preserve equation-level provenance rather than transcribe every
cited expression as equivalent.

## What the mechanism files establish

The original author kinetics, NASA thermo and CHEMKIN transport files
provide no explicit complete critical-state/omega block. Their NASA
polynomials describe ideal-gas thermochemistry; the transport rows give
geometry, LJ parameters, dipole, polarizability and rotational relaxation.
Those are distinct inputs from Tc/Pc/omega.

The pinned Cantera database is a reproducible external compilation, with
general NIST/Yaws provenance. It is not Liang's table. The existing
inventory covers 35 of 111 USC species and 36 of 92 HP species after
explicit aliases. Positive author LJ data cover all species, but that does
not make every LJ value an independently measured critical property.
[USC author files](http://ignis.usc.edu/Mechanisms/USC-Mech%20II/USC_Mech_ver_II.txt);
[HP publisher inputs](https://ars.els-cdn.com/content/image/1-s2.0-S0010218017301724-mmc2.zip);
[Cantera v3.2.0 database](https://github.com/Cantera/cantera/blob/v3.2.0/data/critical-properties.yaml).

The follow-up identified these specific cases:

| Mechanism entry | Author-file evidence | Consequence |
|---|---|---|
| USC `HOC6H4CH3` | Thermo line 615 says `AVG CRESOL` | This is an authored lump. No unique o-, m- or p-cresol CAS/critical row follows from it |
| USC `C4H82` | Kinetics comments identify only 2-butene; thermo header does not resolve cis/trans | Cantera has distinct cis and trans records; choosing either adds a closure |
| HP `OCHCHO` | Thermo line 250 explicitly says glyoxal | Identity is established, but no row exists in the pinned critical database |
| HP `FC6H6` | Thermo line 618 explicitly says fulvene | Must not map by formula to benzene; no pinned database row |
| HP `C3H6O3` | Thermo line 65 says trioxane; source paper identifies 1,3,5-trioxane | No pinned database row; its transport comment says `same as benzene`, indicating an analogy rather than critical-state measurement |
| USC/HP `C6H4O2` | Thermo header gives formula and provenance tag `PUML96`, without positional identity | Do not silently select a benzoquinone isomer |

These statements concern the inspected files and pinned database. They do
not assert that critical data are absent from all literature. Direct
WebBook requests for four additional compounds returned HTTP 403 during
this check; no access workaround was used.

Some mappings are already specific enough for a separately sourced table:
USC `CH2OCH2` → Cantera `C2H4O` (ethylene oxide), `C4H6` → `C4H6-1`
(1,3-butadiene), `C4H612` → `C4H6` (1,2-butadiene), `C4H6-2` → `C4H6-3`
(2-butyne), `CH3CHOCH2` → `C3H6O` (propylene oxide),
`CH3COCH3` → `C3H6O-3` (acetone), `C4H4O` → `C4H4O` (furan), and
`C6H5C2H` → `C8H6` (ethynylbenzene). These are structural crosswalks
supported by the USC comments and database descriptions. They still
require the database provenance to accompany their values; they do not
close the full table.

USC's transport file also states that some aromatic LJ parameters were
estimated from critical information and reuses analogous parameters for
other species. Inverting these estimates cannot independently recover
the source critical data, especially omega.

## Feasible next step and remaining decision

A full-mechanism Case 3 can be defined as a **declared approximation** by
combining identified stable-species data with author-LJ pseudo-critical
estimates and an explicit zero-omega policy. It cannot yet be described
as the recovered Liang input.

Before preparing such a table, every entry needs one explicit status:
identified physical/compiled critical data; unstable-species LJ estimate;
stable species using a declared estimate; or unresolved/lumped identity.
The latter two categories must not silently become radicals. In particular,
`AVG CRESOL` needs a stated lump closure rather than an arbitrary isomer.
Liang's phrase “major species” does not provide the membership list needed
to resolve this automatically.

Keep the alpha convention independent of table construction, preserve
existing major-species values for the continuity control, and verify
frozen-state density and `Cp=(dH/dT)_(p,X)` before flame use. Sensitivity
to unresolved entries can be assessed on existing ideal-flame composition
profiles; low mole fraction alone is not a proof of negligible caloric
effect. No value should be selected because it moves a curve toward the
paper.

## Evidence

Original source hashes and mechanism identities remain in the linked
inventory and HP audit. Additional review evidence is in ignored state:

```text
state/liang-hydrogen-20261020/critical-prescription-followup/
```

It contains rendered reference 8/10 equation pages, retrieval receipts,
and a file manifest. The CERFACS paragraph was available in indexed
primary-source text; its direct PDF retrieval failed with a TLS error.
The Banuti primary paper was readable through web retrieval; the local
download returned HTTP 406. Neither failure was bypassed. No new complete
table was assembled, and no production input changed.
