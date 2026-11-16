# G2 and Maders: geometry, manifold and ignition audit

16 November 2026. Development evidence, not scientific acceptance.

The current G2 comparisons do not test a matched literature LES/FGM setup.
Maders is much closer to its published model. Its retained fine-grid temperatures
are consistent with the executed manifold; its spatial flame structure remains
poorly matched. These require different development actions.

## Geometry and inlet conditions

The current G2 paper-exit wedge has the correct 5 mm oxygen exit, 0.3 mm
separator and 5.6/10 mm methane annulus. It does **not** contain the oxygen
3.6-to-5 mm diverging passage. It starts directly at the injector exit with a
mass-flow boundary. It cannot produce the upstream wall boundary layers,
separation, lip recirculation or inlet turbulence of the published domains.
The older registered mesh does include an upstream passage, but its measured
diameter is 3.2 mm, not 3.6 mm. Neither is the complete paper mesh.

Sharma PDF page9 Figure3/TableII gives 3.6/5/5.6/10 mm and a 10-degree post
divergence angle. It uses a 50 mm square chamber, truncated at200 mm. Its LES
starts from perturbed RANS, evolves for more than50 flow-through times before
sampling, and uses roughly3M/6M cells. These are materially different from our
10k-cell, laminar, axisymmetric, millisecond startup diagnostics. A different
startup is allowable for our clean-zero rule, but developed statistics must be
demonstrated independently; a startup profile is not a literature mean.

Cavalieri PDF pages8–9 also retains the diverging duct, square chamber and
inflow turbulence, then samples60 ms after flushing the initial condition.
Schmitt PDF pages12–13 uses400 mm length,83/300 K streams, characteristic
boundaries, turbulent inlet profiles and50 ms statistics after one convective
time. The85/288 K Cavalieri/Sharma conditions must remain separate.

The mass-flow basis stays O2=44.4 g/s, CH4=143.1 g/s, O/F≈0.31. Mueller and
Cavalieri tabulate these. Sharma's prose reverses the labels, contradicting its
stated mixture ratio. Do not change mass flows to match that sentence or confuse
upstream and exit oxygen velocities. At fixed mass and density, changing the
O2 inlet radius1.8→2.5 mm changes bulk velocity by a factor0.5184.

The new `paper-injector-wedge` recipe isolates the missing taper while retaining
the same chamber approximation. It interprets10 degrees as the angle to the
axis, giving3.969897 mm taper length. This angle convention is an explicit
reconstruction assumption, not a measured experimental duct length. No unknown
straight-pipe length is invented. The asset requires allocated mesh checks and
is not automatically accepted by an existing CFD loader.

## What each chemistry closure actually does

| Implementation | Transport and lookup | What it can establish |
| --- | --- | --- |
| Latest G2 relaxedTable runs |53 species andZ; Y relaxes toward one burning Y(Z) flamelet, exact10us frozen-target source clock | Species/transport/Ha coupling diagnostic; no physical ignition/extinction prediction |
| Existing genuine fgmTable path | RawC andZ; composition and signed volumetric source from mapped(Z,C) | Laminar FGM, subject to actual manifold coverage, transport and thermo qualification |
| Maders Fig4 reference | Z andgamma; gamma=sum(Yi/MWi), i=CO2,H2O,H2; table density/transport; unityLe | Atmospheric diluted-methane coflow FGM |
| Sharma reference | RawYc=YCO+YCO2 transport; equilibrium normalization only for lookup; unsteady diffusion-flamelet manifold and presumed PDFs | Finite-rate turbulent FGM |
| Schmitt reference | Fast chemistry/equilibriumY(Z), reduced seven-species CH4/O2 representation and beta-PDF | Equilibrium-chemistry LES; not a finite-rate FGM comparison |
| Cavalieri reference | Flamelet manifold parameterized byZ, variance and scalar dissipation; real-fluid property mixing models | Turbulent steady-flamelet LES; not our single fixed-chi relaxation |

Schmitt Section2.4 explicitly assumes equilibrium. An earlier interpretation of
this paper as finite-rate reduced kinetics was incorrect. His successful G2 LES
also means finite-rate FGM is not a prerequisite for every useful G2 comparison.
It does not mean a single laminar relaxation table reproduces his filtered model.

Our current G2 target flamelet uses chi_st=100000/s. Cavalieri Fig2 uses1/s,
Fig8 compares1 and1000/s, and its LES maximum chi_st is about10000/s. This is
a concrete mismatch to investigate, not permission to select chi by visual fit.
A low/high-chi physical family and resolved scalar-dissipation diagnostic should
precede selecting a steady-flamelet closure.

The genuine FGM route must retain unnormalized transportedC, the exact progress
weights, source unitskg/m3/s (no extra density multiplier), signed rates and
pure-stream degeneracy. It needs steady and transient extinction/ignition
coverage, not equilibrium endpoints joined by arbitrary straight source curves.
Ideal-gas flamelets coupled to SRK density/enthalpy remain a declared model
approximation. A small caloric residual only verifies the executingEOS inversion;
it cannot establish consistency between table chemistry and the CFD state.

## Ignition

Maders PDF page4 prescribes cold flow followed by local ignition at the burner
exit near stoichiometry, assigning gamma at the maximum tabulated source. Our
corrected scheduled source-peak event follows that method in one clean-zero
process. Its density/flux/timestep reset is a numerical correction, not a new
combustion model. The published paper does not provide an exact kernel extent,
ignition duration or convergence threshold; our choices remain sensitivities.

The latest G2 relaxation cases have a pure-fuel background and no explicit
progress ignition. Any mixture is driven toward the burning target. This is
imposed burning-state relaxation, not predicted ignition. For a trueG2 FGM test,
start with a cold consistent state, establish mixing in the same time-zero run,
then use a declared local progress seed on the physical manifold. Log location,
selected cells, C/Ha/rho changes and timestep reset. A seed must not become a
persistent unreported heat source or overwrite temperature independently ofHa/Y.

DeepFlame's pinned source supports transported progress withomega_c, optional
enthalpy transport and table-temperature or enthalpy-based reconstruction. Its
ignition routine forces progress in a spatial ball for a specified duration.
That is evidence for an explicit startup procedure, not a justification to copy
its c=1 prescription without checking the selected coordinate's scaling.

## Independent Maders field test

`field_audit.py` was run on the retainedR19 fine-grid profiles at1.11500646592s
and the exact executed quenching-table NPZ SHA256
`793a2accc2b7296c89e36c8b4d912b2afc47e5029294bed277027c5928c40734`.
Both249-point profiles have full mapped-coordinate coverage.

| Height | Hot-region T minus independently reconstructed tableT RMS | Maximum absolute difference | Ha minus linear inlet mixing RMS |
| --- | --- | --- | --- |
|10 mm |0.395 K |1.538 K |2.905 J/kg |
|40 mm |0.257 K |1.950 K |45.306 J/kg |

These are sampled-point diagnostics, not exact cell closure. They argue against
a gross energy/table-temperature discrepancy as the cause of the much larger
paper profile errors. Interpolation, mechanical work and diffusion contribute
to the reported small differences. The sampled fgmTdiag/source fields are
approximately zero despite nonzero independently reconstructed values: those
stored diagnostic fields are stale and must not be used to judge source validity.
This audit does not establish why they were stale or qualify their repair.

Maders next controls should distinguish inlet/buoyancy/outer-boundary effects,
radial/axial resolution and manifold source error. Keep absoluteHa. The current
100um axial refinement is not the cited30–60um front resolution. Compare the
same numerical protocol, measured settling and original profile coordinates;
do not alter chemistry to move the flame peak.

The recovered Verhoeven thesis PDFp44 confirms0.23m/s **maximum** fuel velocity,
300K streams and a no-slip outer wall. Maders uses298K. Do not double the fuel
flow by interpreting0.23 as its mean. A direct read of the retainedR19 time-zero
U dictionary found `outerWall { type slip; }`, selected by the old `paper` case
generator. This is a confirmed setup mismatch. The generator now defaults to
noSlip and offers an explicitly recorded historical slip control. A paired fresh
physical comparison is still required; this change alone does not establish the
cause of the large flame-shape discrepancy. The recovered thesis is retained at
`state/fgm-published-targets-20261112/verhoeven2011.pdf` and was actually read,
not inferred from the unsuccessful new download.

## Development sequence

1. Qualify the new injector mesh with actual blockMesh/checkMesh and retain
   the old exit-only result. Measure inlet/exit areas and the pressure/momentum
   response before any reacting geometry comparison.
2. Preserve the improvedZ/species transport consistency from the prior campaign.
   Tightening energy linear solves did not fix accepted-state energy balance;
   diagnose pressure/source-stage accepted states rather than tuning tolerances.
3. Separate equilibrium/steady-flameletG2 from finite-rateFGM. First determine
   physical chi sensitivity and element/enthalpy consistency. Then build and
   qualify a raw-C manifold at the actual case pressure/stream temperatures.
4. Test source, transport and ignition in a small physical control before a
   new fullG2 clean-zero case. Add turbulence/inlet fluctuations and statistical
   sampling for comparisons of developed literature means.

The prior overnight campaign is closed. New mesh/property qualifications are a
separate follow-up; no old deadline, usage, field or acceptance record is reset.

## Primary sources

- [Maders2017 paper and metadata](https://www.abcm.org.br/proceedings/view/COB17/0722), PDF pages2–6.
- [Sharma2023 manuscript](https://arxiv.org/abs/2311.15034), pages5,8–10 and AppendixA.
- [Schmitt2020](https://doi.org/10.1007/s10494-019-00096-y), Sections2.4 and3.2.
- [Cavalieri2025](https://doi.org/10.1016/j.ijheatmasstransfer.2025.127284), Sections2 and4.
- [Verhoeven2011 diffusion-flameletFGM comparison](https://doi.org/10.1016/j.combustflame.2011.07.011).
- [Fluent FGM theory](https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/flu_th/flu_th_sec_par_premix_theory.html), distinction between strain- and progress-parameterized manifolds.
- [DeepFlame baseFGM source](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/src/dfCombustionModels/FGM/baseFGM/baseFGM.C), transported progress and timed ignition.
- [DeepFlame flareFGM source](https://github.com/deepmodeling/deepflame-dev/blob/7cb3294b275525cb8829ada3d3fbc067ab9323eb/src/dfCombustionModels/FGM/flareFGM/flareFGM.C), property/source lookup and thermo reconstruction.

The downloaded PDFs, extracted page text and exact DeepFlame fileSHA256 index
are retained outsideGit in `state/g2-fgm-setup-audit-20261116/references`.
Forum searches supplied leads but no sufficiently case-specific evidence to
override the papers or executing source.
