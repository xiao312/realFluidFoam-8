# Methods to test for G2 thermodynamic coupling

15 November 2026, Asia/Shanghai. Research and recommendations; no new algorithm
in this note has been implemented or scientifically accepted. Existing S11/S12
CFD runs continue under their original bounds. No new compute was submitted for
this research.

## Decision

The best immediate experiment is an exact update for the existing relaxation
model, followed by a conservative pressure-equilibrium flux comparison. The
strongest public implementation found for the latter is Trixi.jl's implementation
of Terashima, Ly and Ihme's 2025 APEC flux. The closest recent pressure-based
research direction is the 2026 multicomponent PEQSI algorithm. These address
different parts of the problem and should not be combined in one unexplained
change.

Keep G2 diagnostics and focused mechanism tests running as parallel development
tracks. An imperfect paper plot should not prevent an independent experiment.
Passing a contact test also does not qualify reacting G2.

This extends the [14 November methods note](schmitt-g2-methods-research-20261114.md).
The new findings are inspected public APEC code, an SRK flame regression in PeleC,
a source-integration confound in our timestep study, and a more explicit sequence
of experiments. Earlier double-flux and root-policy failures remain evidence.

## Evidence that changes the interpretation

Our same-time Schmitt controls at 300 us reached 1,689 K with Cr = 100 and
3,254 K with a nominal fixed relaxation timescale of 10 us. The longer fixed-time
case failed at 682 us. The Gibbs-only and coupled-recovery Cavalieri controls
both failed at 141.918 us with an 8.696 kJ/kg enthalpy mismatch. The coupled
predictor rejected its one candidate and made no correction. A successful local
property query therefore did not transfer to that CFD state.

At the live approximately 19:58 inspection, timestep-refined Cavalieri completed
its requested 1 ms (job 128109186, 5,251 allocated seconds, 32 cores, Slurm 0:0).
Its final Tmax was 3,322.735 K and caloric maxRelative residual 2.394e-9,
below the unchanged 1e-8 criterion. Schmitt was running at 0.628 ms, with its
0.6 ms write-time caloric residual 2.431e-9. These are startup trajectories,
not developed paper statistics. Solver completion and caloric closure do not
establish energy/element conservation or paper agreement.
Exact operational records are in the separate `g2-source-coupling-20261115` state.

There is an important confound. The implemented source is

\[
Y^{n+1}=Y^*+\alpha(Y_{\rm table}-Y^*),\qquad \alpha=\Delta t/\tau.
\]

For a frozen target its effective decay timescale is
\(\tau_{\rm eff}=-\Delta t/\log(1-\Delta t/\tau)\). At nominal tau = 10 us,
the maximum timesteps of 5 and 0.5 us give effective timescales of approximately
7.21 and 9.75 us. Thus our refinement changes both flow discretization error and
source-integration error. It does not isolate pressure coupling alone.

The exact frozen-target update uses `alpha = -expm1(-dt/tau)`. This is a proposed
integration change, not a fitted chemical rate. It does not repair elemental
inconsistency in a target or remove splitting error when the target changes.
The original per-step Cr mode should remain available for paper reproduction.

## Inspected codes and current research

### 1. Trixi.jl / Terashima APEC: first flux prototype

[Terashima, Ly and Ihme (2025)](https://doi.org/10.1016/j.jcp.2024.113701)
construct fully conservative fluxes with approximate pressure-equilibrium
preservation. Actual functions `flux_terashima_etal` and
`flux_central_terashima_etal` are public in
[Trixi's nonideal Euler implementation](https://github.com/trixi-framework/Trixi.jl/blob/3ffaf4b91885fd3ede90d54476263ad3073a722d/src/equations/nonideal_compressible_euler_2d.jl#L194).
The pinned 2D file was byte-for-byte equal to the fetched main-branch file.
The [official changelog](https://trixi-framework.org/TrixiDocumentation/stable/changelog/)
also records these additions.

The inspected method corrects the face interpolation of internal-energy density
using constant-pressure thermodynamic derivatives, then builds compatible
momentum and total-energy fluxes. This is a modification of transport, not a
post-step temperature projection. The inspected 2D equation has four Euler
variables; it is not a ready-made 53-species reacting solver. Public density-wave
and finite-volume examples exist, but their default flux choices do not
automatically enable APEC.

**Our experiment:** reproduce a supplied nonideal advection example, then port a
small attributed C++ face-flux kernel to the existing contact application using
our actual SRK/caloric functions. Compare baseline conservative flux, retained
double-flux and APEC on the same Schmitt contacts. Measure pressure/velocity
errors and mass/energy budgets together. Extend composition derivatives before
claiming a multicomponent implementation; do not insert one scalar correction
into the enthalpy equation and call it APEC.

### 2. PeleC / PelePhysics: independent thermodynamics and flame reference

The inspected [PelePhysics SRK source](https://github.com/Pele-Suite/PelePhysics/blob/development/Source/Eos/SRK.H)
provides `REY2T`, `RTY2P`, internal-energy derivatives and composition-dependent
properties. Its density/internal-energy recovery differs from our repeated
fixed-pressure enthalpy inversion. Importantly, `RHY2T` is explicitly unsupported
in that file, and pressure/temperature-to-density initialization still selects
the largest cubic root. It is not an automatic phase-selection repair.

PeleC also has an actual
[PMF-SRK regression directory](https://github.com/Pele-Suite/PeleC/tree/development/Exec/RegTests/PMF-SRK).
Its [GNUmakefile](https://github.com/Pele-Suite/PeleC/blob/development/Exec/RegTests/PMF-SRK/GNUmakefile)
selects SRK and LiDryer; its input references an H2 flame data file. This is a
useful reacting reference, not an existing methane/oxygen G2 case.

**Our experiment:** compare matched-coefficient property values and derivatives
at the retained cold states, followed by a small reacting reference. Match
NASA data, critical parameters, mixing rules and energy reference first. The
[constants source](https://github.com/Pele-Suite/PelePhysics/blob/development/Source/PhysicsConstants.H)
uses RU = 8.31446261815324e7; direct copying into our SI/molar implementation
would be incorrect. A density-energy formulation must derive pressure work and
fluxes consistently; replacing h with e in a dictionary is insufficient.

### 3. PEQSI 2026: closest pressure-based architecture

[Tsutsumi et al. (2026), PCI 106563](https://doi.org/10.1016/j.proci.2026.106563)
extend a pressure-equilibrium semi-implicit method to multicomponent real fluids
and combine it with an enthalpy-based treatment. Reported tests include 2D
LOX/GH2 shear layers and 3D LN2/GH2 injection, with timestep limits based on
convection rather than explicit acoustics. These are relevant nonreacting
demonstrations, not verification of reacting methane/oxygen FGM G2.

The predecessor is
[Wada et al. (2024), Physics of Fluids 36, 116104](https://doi.org/10.1063/5.0231255).
The author's [research description](https://cap.stanford.edu/profiles/viewCV?facultyId=346764&name=Wada_Sho)
explains explicit advection and implicit acoustic steps. No public PEQSI source
repository was verified in this search; the 2026 assessment is based on the
publisher's abstract, not an audited full implementation.

**Our experiment:** derive a pressure/enthalpy update with EOS-consistent
thermodynamic derivatives and test a source-free contact before adding reaction.
Use the [Loci-STREAM pressure-based double-flux guide](https://streamline-numerics-inc-loci-stream.readthedocs-hosted.com/en/stable/theory/appendices/appendix_double_flux.html)
as an additional implementation reference for keeping frozen thermodynamic
surrogates consistent across pressure, energy and EOS synchronization. Its
developer documentation is not independent validation of our adaptation.

### 4. Exact conservative PEP methods: promising, with conditioning limits

[DeGrendele et al. (December 2025 preprint)](https://arxiv.org/html/2512.04450v1)
construct conservative pressure-equilibrium flux corrections for arbitrary EOS
and species counts. Their demonstrated cases are smooth inviscid interfaces
with ideal, stiffened and van der Waals models. The correction system uses
conditioning-aware pseudoinverses and an approximate limiting scheme. Public
author code was not verified. SRK combustion, positivity and G2 remain transfer
questions.

[Coppola, Aiello and De Michele (May 2026 preprint)](https://arxiv.org/html/2605.03617v2)
derive EOS-dependent mass/internal-energy fluxes, with PR transcritical and
2D inviscid tests. Their exact nonlinear mean can be singular in uniform regions;
the approximate APEP-RG formulation is therefore particularly interesting for
our large uniform initial regions. Their 2D tests use a small CFL to limit time
integration error. This is not evidence that a direct PIMPLE port will allow
large timesteps. Public author code was not verified.

**Our experiment:** after APEC, compare the nonsingular approximate formulation
on the same contacts. Record conditioning and positivity alongside pressure
and energy. Exact algebraic pressure equilibrium alone is not a complete
stability guarantee; [Ranocha and Gassner](https://arxiv.org/abs/2009.13139)
demonstrate that distinction and provide reproduction code.

### 5. RFQC 2026: useful longer-term phase-change alternative

[Bai et al., JCP 564 (2026), 115156](https://arxiv.org/html/2602.00658v3)
evolve frozen thermodynamic linearization quantities and perform EOS
re-projection. They quantify the resulting energy error and demonstrate
transcritical/phase-change tests. The inspected thermodynamic derivation is
single-component PR with equilibrium phases; multicomponent/3D extension is
listed as future work. No public implementation was verified.

**Our use:** an alternative if a quantified quasi-conservative method is needed.
It must report re-projection energy separately and be compared against our
existing double-flux results. It is a larger change than the first APEC test and
does not directly supply a reacting 53-species closure.

### 6. ThermoPack / reduced-space flash: determine whether phase physics matters

[ThermoPack's public interfaces](https://thermotools.github.io/thermopack/vcurrent/thermo_methods.html)
include PH, TP and UV flash, derivatives and phase-envelope tools.
[Fathi and Hickel (2021)](https://doi.org/10.1002/aic.17174) provide reduced-space
multicomponent flash methods with analytic cubic-EOS Jacobians. These address
phase splitting, which is different from selecting a homogeneous cubic root at
fixed bulk composition.

**Our experiment:** use matching parameters to map stability and possible phase
splits around the retained failed states. A major-species subset is a separately
labelled model if the full radical parameterization cannot be matched. Do not
swap default external fluid data into an alleged exact-state comparison.
Adopt a phase closure only after distinguishing physical phase behavior from
numerically generated pressure excursions. Current timestep sensitivity argues
against assuming phase physics is the first mandatory repair.

## Additional practices worth borrowing

[PeleLMeX's model documentation](https://github.com/Pele-Suite/PeleLMeX/blob/development/Docs/sphinx/manual/Model.rst)
describes predicting face temperature/composition and reconstructing face
enthalpy through the EOS, conservative correction of diffusion fluxes, and SDC
coupling of transport and reaction. These are useful design principles; its
documented ideal-gas divergence constraint cannot be copied as a real-fluid
constraint. With our current first-order upwind scheme, EOS reconstruction of
the same admissible upwind cell can be equivalent to upwinding h, so audit that
equivalence before expecting a benefit.

[PETSc SNES](https://petsc.org/release/manual/snes/) supplies line search,
trust-region methods and recoverable domain-error handling. Borrow the idea of
rejecting an inadmissible nonlinear trial and reducing its step, while requiring
the accepted state to satisfy the original equations. That differs from killing
the run at every bad trial or clipping the accepted state. A coupled residual
must include EOS, continuity and energy; smaller linear-solver residuals alone
do not establish coupled convergence. A discontinuous target interval still
cannot be solved by a better scalar Newton method.

[SU2 provides another public FGM implementation](https://github.com/su2code/SU2/blob/master/SU2_CFD/src/fluid/CFluidFlamelet.cpp).
The inspected `CFluidFlamelet` code has explicit table/MLP lookup interfaces,
controlling-variable names and source lookup configuration. Its
[combustion tutorial](https://su2code.github.io/tutorials/Inc_Combustion/)
uses progress, enthalpy and mixture-fraction coordinates. This is useful for
our table interface and source-field contract, rather than a verified dense-fluid
G2 replacement. The tutorial's displayed equations should be checked against
source/configuration before reuse; they are not our governing-equation authority.
Pin a source revision and inspect the license before borrowing implementation.

For independent EOS derivative checks,
[teqp](https://teqp.readthedocs.io/en/latest/) offers public general-cubic,
thermodynamic/composition-derivative and phase-equilibrium tools. Use matching
coefficients and compare derivatives at retained states; a different default
fluid database is not an exact reference for our implementation.

## How to run this as a CFD research program

NASA's [verification guidance](https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html)
separates implementation checks, iterative convergence and discretization
error. Its [analysis process](https://www.grc.nasa.gov/www/wind/valid/tutorial/process.html)
calls for controlled sensitivity studies, and its
[validation guidance](https://www.grc.nasa.gov/www/wind/valid/tutorial/valassess.html)
uses increasingly complex comparisons. Our adaptation is a small number of
diagnostic experiments tied directly to observed failures, alongside the fixed
paper ladder, rather than another large collection of synthetic tests.

| Priority | Experiment | Decision it resolves | Evidence to retain |
| --- | --- | --- | --- |
| 0 | Complete S11/S12 under existing bounds | Does refinement cross the known failures? | Same-time profiles, final closure, budgets, source alpha and actual dt |
| 1 | Exact frozen-target relaxation; coarse/fine fresh cases | Separates source-integration error from flow-time integration | Analytic source trajectory; PIMPLE iteration-count sensitivity; identical nominal tau |
| 2 | Baseline / double-flux / APEC contacts | Does compatible flux construction reduce pressure error without hidden energy injection? | Paper profiles, p/U norms, global mass/energy and EOS residuals |
| 3 | Matched-state PelePhysics comparison | Separates our property/derivative implementation from flow coupling | Units, coefficients, energy reference, all roots and derivatives |
| 4 | Pressure/energy formulation prototype | Can nonlinear coupling converge at useful timesteps? | Full coupled residual history, rejected trials, EOS density versus transported density |
| Parallel | Phase-stability mapping | Is a homogeneous EOS physically adequate in the encountered region? | Matched-parameter phase/stability results and explicit model differences |
| Parallel | Species/source invariant audit | Does transport or relaxation introduce elemental drift? | Pre-clipping species, source-only element change, target/predictor mismatch and shared mass flux |

For each algorithm, retain a small failure register: exact cell state and
location, first failing operator, EOS branch, derivative conditioning, actual
timestep/source clock and source/library identities. Compare at common physical
times; do not compare one failed startup snapshot with a developed LES mean.
Time and grid refinement should estimate uncertainty for selected quantities,
not become a demand to perfect every picture before any harder diagnostic.

The first practical implementation choice is therefore **exact source
integration plus an APEC contact kernel**, with a pressure/energy formulation
study next. PEQSI and the newer PEP papers are valuable architectural references;
none is an established drop-in fix for our current reacting solver.

## Implementation follow-up, 15 November

Opt-in fixedTimeExact is implemented in source80fa810 and actually qualified
by job128112392 (320s): original default rows unchanged;60exact model-source
rows passed with constant-Ha/Qdot checks and equal-time endpoint difference
1.364e-12K. This is source integration qualification, not physical validation.
The oxygen-only APEC application is an experimental adaptation with direct
rho/e recovery and shared conservative energy flux. It is not yet qualified
or transferred to reacting G2. See its local module README and S16 receipts.
