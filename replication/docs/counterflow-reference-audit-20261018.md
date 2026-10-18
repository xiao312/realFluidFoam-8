# Counterflow reference audit, 18 October 2026

The preserved OF6 tutorial is not the mesh specified in Nguyen's 2022 paper.
It is a useful source input, but it does not establish a paper-matched simulation.
This audit compares primary references with the existing generators. It changes no jobs or solver code.

## Primary evidence and scope

Page numbers below are printed page numbers. Nguyen's printed and PDF page numbers agree.
Juanos and Sirignano's printed page 56 is PDF page 3.

- Nguyen et al., *Computer Physics Communications* 273 (2022), 108264: supplied PDF `1-s2.0-S0010465521003763-main.pdf`.
  SHA-256: `716602f37f6b27f62791986770788e450225bc688686c54049849ecfe8414a60`.
- Juanos and Sirignano, *Pressure effects on real-gas laminar counterflow*, *Combustion and Flame* 181 (2017), 54–70.
  Local PDF: `state/juanos-sirignano-2017.pdf`.
  SHA-256: `8104c6f00cb5b610b9ac9776cc4484be5baad39212a027dcd9a68440f8582a31`.
- Preserved tutorial: `realFluidThermophysicalModels-6`, revision `61f86014ef3f4277d04a348c83777d6a20d24cf3`.
  Local input authority: [provenance manifest](../validation/flames/author-counterflow/provenance.json).
- Case implementation inspected: [author port](../validation/flames/author-counterflow/prepare.py),
  [pressure/air adaptation](../validation/flames/paper-campaign/prepare.py),
  [inlet finalization](../validation/flames/finalize_inlets.py), and
  [paper mesh draft](../development/counterflow/prepare.py).

The original mesh and dictionaries were read directly. Paper page locations were checked against the PDFs.
This static audit does not prove the state of a particular running directory.
Run manifests and staged input hashes remain the authority for each job.

## Geometry and mesh

| Condition | Paper specification | Current tutorial-based mesh | Finding |
| --- | --- | --- | --- |
| Oxyfuel, 1 atm | Nguyen p.10, Table 1: radius × separation 20 × 20 mm; radial spacing 20 µm; axial spacing 20–30 µm | 80 radial cells; 40/60/40 axial cells over 6/8/6 mm; radial spacing 250 µm; central axial spacing 133.33 µm, outer spacing 150 µm | Domain matches. Radial spacing is 12.5 times larger; central axial spacing is 6.67 times larger than the paper minimum. |
| Oxyfuel, 200 atm | Nguyen p.10, Table 1: 5 × 5 mm; radial spacing 5 µm; axial spacing 5–10 µm | Same 80 × 140 topology, scaled domain; radial spacing 62.5 µm; central axial spacing 33.33 µm, outer spacing 37.5 µm | Domain matches. Radial spacing is 12.5 times larger; central axial spacing is 6.67 times larger than the paper minimum. |
| Air, 100 atm | Nguyen p.11, §5.2: 20 × 20 mm; uniform 5 µm mesh in the flame zone; stretched remainder | 80 × 140 topology; radial spacing 250 µm; central axial spacing 133.33 µm | Domain matches. Central axial spacing is 26.67 times larger than 5 µm. The tutorial is not the published flame-zone resolution. |

All tutorial variants have 11,200 cells and one wedge cell in the azimuthal direction.
The original wedge half-angle is 2.5°. Nguyen specifies axisymmetry but does not give a wedge angle.

For oxyfuel, the paper explicitly requires uniform radial spacing and approximately 20 axial points through the flame.
It does not give stretched-zone boundaries, cell counts, or grading ratios.
The draft reconstructs 888,000 cells at 1 atm and 816,000 cells at 200 atm from the stated spacing ranges.
Those counts are our reconstruction, not published counts.

For air, the phrase "uniform mesh of 5 µm" has no directional table.
The earlier draft selected 20 µm radial spacing and 5 µm central axial spacing, giving 1,978,000 cells.
The corrected draft now selects 5 µm uniform radial spacing, giving 7,912,000 cells; this larger air mesh is not launched.
That radial choice is an assumption. It is not established as matching the paper's flame-zone mesh.
A literal interpretation can require 5 µm radial spacing in that zone too.
The air mesh specification must expose this uncertainty rather than claim an exact match.

## Inlets and outlets

| Item | Primary specification | Existing generator and action |
| --- | --- | --- |
| Oxyfuel composition | Nguyen p.10, §5.2: pure CH4 versus 21% O2 and 79% CO2 by volume | Tutorial uses rounded oxidizer mass fractions, O2 = 0.162 and CO2 = 0.838. Paper draft converts exact molar fractions with the case molecular weights. |
| Oxyfuel temperatures | Nguyen p.10: fuel 300 K; oxidizer 1000 K | Preserved correctly. |
| Oxyfuel strain and momentum | Nguyen p.10: `a = 2(|UF|+|UO|)/L = 100 s^-1`; `rhoF UF^2 = rhoO UO^2` | Original 1-atm velocities 0.467/0.533 m/s enforce the strain exactly but only approximate momentum matching. High-pressure adaptation and paper draft use actual library inlet densities. |
| Oxyfuel outlet pressure | Nguyen p.10: total pressure 1 or 200 atm | Tutorial uses `totalPressure`, with `p0` from the internal pressure. Pressure adaptation replaces that internal value. |
| Oxyfuel other outlet fields | Nguyen p.10: zero-gradient conditions for remaining variables | Live saved fields use `pressureInletOutletVelocity` for U and `inletOutlet` for T; inspected species already use `zeroGradient`. Paper draft changes non-pressure fields to `zeroGradient`. Mixed and zero-gradient conditions can agree during pure outflow but differ under backflow. |
| Air fuel inlet | Juanos p.56, Eqs.9–10; p.60, §6: pure CH4, 300 K, 1 m/s | Correctly imposed by the pressure/air adaptation and inlet finalization. |
| Air oxidizer inlet | Juanos p.56, Eq.10: equal and opposite mass flux, not momentum flux; p.60: 300 K | Existing adaptation correctly uses `UO = rhoF/rhoO` with fuel speed 1 m/s. Do not impose the oxyfuel momentum constraint here. |
| Air composition | Juanos p.60: air; no numerical O2/N2 ratio identified in the inspected main text | Generator assumes 21/79 molar O2/N2. Record that assumption. |
| Air pressure and separation | Nguyen p.11: 100 atm and 2 cm axial separation, following Juanos case 6 | Correctly represented as 10,132,500 Pa and 0.02 m. |

Juanos p.69, Appendix B, explicitly shows that mass-flux versus momentum-flux matching shifts the flame and stagnation plane.
Thus, those constraints must stay separate even if both produce similar peak temperatures.
Nguyen's air case inherits Juanos case 6 boundary conditions, with the declared dimensional and diffusion-model differences below.
Juanos's 1-D problem has no radial outlet. The air variant's lateral outlet is a 2-D implementation choice.

## Chemistry, transport, and equations

Nguyen p.9, §4.2, Eqs.35–39 specifies compressible continuity, momentum, species, and sensible-enthalpy equations.
It includes kinetic-energy transport, pressure work, reaction heat, and species enthalpy diffusion.
The diffusion velocity uses mole-fraction gradients and a mixture-averaged diffusion coefficient.
The last species closes mass fractions and net diffusive mass flux.
Soret, Dufour, and radiative heat transfer are explicitly omitted.

Nguyen pp.9–11 specifies SRK, realFluid-JANAF, Chung transport, Takahashi diffusion correction, GRI-Mech 3.0, PIMPLE, and SEULEX.
The existing OF8 case selects these model families.
The [earlier source audit](solver-paper-audit-20261017.md) establishes their broad implementation correspondence.
It does not prove bitwise or equation-by-equation equivalence with the unpublished publication run.

For the air comparison, Nguyen p.11 explicitly allows two differences from Juanos case 6:

- Nguyen solves a 2-D axisymmetric domain; Juanos uses a 1-D similarity formulation.
- Nguyen uses mixture-averaged diffusion; Juanos uses multicomponent diffusion.

Juanos p.60, Table 1 identifies case 6 as SRK density, the full real-gas energy equation (Eq.5), and corrected viscosity/conductivity.
Case 7 uses the simplified species-weighted enthalpy approximation (Eq.8). Case 7 is not the requested benchmark.
Juanos p.56, Eq.7 neglects the pressure-diffusion contribution and normally omits the Soret term.
The separate Soret comparison is not the base case 6 target.
Radiation is omitted from the solved energy equation; p.58 assesses its small contribution afterward.
GRI 3.0 has 53 species and 325 elementary reactions in Juanos p.56.

The air generator inherits `inertSpecie CO2` from the oxyfuel port.
It changes the oxidizer to O2/N2 without changing this closure species.
Nguyen describes a last species, usually a diluent, but does not identify the closure species for the published air run.
Using CO2 as the algebraic closure does not by itself prove an error: it is a dependent species in the transport system.
However, an N2-closure sensitivity is warranted for the air case, with species/element balances checked.
It must be a declared numerical variant, not an undocumented correction to historical jobs.

## Numerical controls and remaining unknowns

The preserved GRI30 tutorial specifies:

- Euler time differencing; Gauss linear gradients; limitedLinear convection; corrected Laplacian and normal gradients.
- One outer PIMPLE corrector, two pressure correctors, no non-orthogonal correctors, and momentum prediction enabled.
- SEULEX absolute tolerance `1e-8`, relative tolerance `0.1`, and initial chemical time step `1e-7 s`.
- Initial fixed flow time step `1e-6 s`; the current continuation changes time controls through its separate adaptive release.

Nguyen's inspected main paper does not specify these discretization choices, iteration counts, chemical tolerances, flow time step, or stopping criterion.
They are tutorial or project controls, not verified paper settings.
The paper describes steady profiles; reaching 70 ms is not itself a published convergence criterion.

Juanos p.57, §4 instead uses finite differences, first-order upwind convection, second-order central diffusion, and TWOPNT.
Its grid adapts from a coarse solution, and pressure continuation supplies higher-pressure initial guesses.
Those are reference-solver methods, not instructions to substitute TWOPNT numerics into Nguyen's OF8 replication.

The OF8 source has the 2022 reacting solver's broad PIMPLE ordering and a later shared temperature inversion implementation.
The separate 2025 `realFluidFoam` solver changes the inner coupling and transport interfaces.
Changing executable is therefore not a mesh-setting correction.
The [thermophysical audit](thermo-architecture-audit-20261017.md) records the inversion differences and known qualification limits.

The following details remain unresolved from the primary papers: exact meshes, input data tables, historical source commit, and solver tolerances.
The paper's use of a model family does not establish equality of every species critical property, binary interaction, or transport parameter.

## Consequence for the next cases

Use the published domain, mesh spacing, inlet constraints, temperatures, composition, and outlet description for the new oxyfuel cases.
Retain the tutorial-based results as a coarse-grid baseline.
Record reconstructed grading and retain independent mesh-convergence checks.

For air, resolve the chemistry failure before a full fine-grid run.
Document the radial-resolution ambiguity and closure-species choice in its manifest.
Compare absolute axial profiles, including species and transport properties, without moving them to align peaks.
Inspect inlet mass/momentum fluxes, lateral backflow, and species/element balances before attributing a position error to the solver.

These findings identify mismatches and unknowns. They do not establish which mismatch causes the present 200-atm flame-position error.

## Live-input verification and bounded correction

Read-only inspection of jobs 124767586/124767667 confirmed the coarse mesh and
U/T outlet types above. At 1 atm the inlet speeds are 0.467/0.533 m/s.
At 200 atm they are 0.110787900036/0.139212099964 m/s. Both use oxidizer
O2 mass fraction 0.162. System/constant dictionaries and boundary snapshots
are archived under `state/counterflow-live-settings-20261018.json` and
`state/counterflow-live-boundaries-20261018.json`, with source hashes.

The new oxyfuel workflow uses the paper spacing, exact composition and corrected
outlet types. It recalculates inlet speeds with the actual library density.
A private copy of a stable coarse checkpoint supplies a mapped warm start;
only primitive fields are mapped, and thermodynamic properties are recomputed.
The first 32-core allocation is a 10-microsecond mesh/mapping/chemistry/cost check.
This is not a full steady-flow run and has no convergence acceptance.
The OF8 solver and library physics remain unchanged. No 2025 coupling change
is mixed into this case-setting correction.
