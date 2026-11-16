# G2 RANS mixing diagnostic

`configure-uniform-methane.mjs CASE [--apply]` prepares a separate source-paused
single-fluid isolation control after setFields but before executing-EOS Ha
initialization. Both passages/chamber contain CH4 at288K/5.61MPa; original
inlet volume velocities are retained using the qualified pure-stream SRK
density ratio. This is not G2 or a changed scientific acceptance criterion.
It tests whether cold kEpsilon failure requires composition/temperature/density
contrast. It updates all initial species/Z/C/T fields, the LOX-named inlet mass
flow and explicit stream manifest together; the passage name denotes geometry,
not oxygen in this diagnostic. No evolved field is used. Full provenance and
changed hashes are retained. Node built-ins only, no network/secrets; mutation
requires a fresh admitted project case. Verify syntax, pure composition and
mass-flow consistency in a read-only fixture, then actual executing density,
caloric/element/continuity and turbulence histories. A successful uniform-fluid
case does not validate a mixing flame or its paper comparison.

Optional `unusedDiffusionPolicy: suppress-unity-Le` selects a separately
identified optimized split-FGM case with `skipUnusedDiffusion:true`. The default
example remains on the full-property path. The optimized combination requires
newly built thermo-policy products: old binaries must reject it. Exact
kEpsilon/eddyDiffusivity Prt0.7 and immutable absolute-Ha configuration remain
required. Source inspection shows DEff=alphaEff, with the same coefficient in
Z/C/Ha diffusion; species Dimix is unused. Its accessors still fail if called.
Before a longer run, compare actual full-versus-suppressed properties, field
histories and elapsed time from identical fresh initial conditions, plus
internal/boundary/raw-Dimix negative controls. No transport or chemical
coefficient is fitted. This is implemented but not yet physically qualified.

`example-fgm.json` selects a separate transported-progress FGM diagnostic. It
requires `sourceTreatment:delta-at-mean-Z-C`, a fresh original-zero raw-C case,
and, by default, `skipUnusedDiffusion:false`. It uses the normal full-property path. The
existing runtime already registers kEpsilon/eddyDiffusivity and transports C
with the same alphaEff as Z and Ha. Source/composition are queried at mean Z/C;
there is no presumed PDF or scalar-variance model. The unchanged source table,
caloric/bounds/conservation checks and actual inlet velocities remain owned by
their original modules. Verify configuration against a real candidate plan,
then exact model selection, finite turbulence fields and fresh physical runs.
This combination remains a diagnostic until separately qualified. Full-property
overhead must be measured; do not infer transport correctness from compilation.
The original steady configuration/optimization remains unchanged.

The generator accepts the registered5.61MPa/85/288K and Schmitt5.6MPa/83/300K
stream sets. Each requires its own actual physical table and thermo identity.
The kEpsilon/delta-PDF approximation remains distinct from the reference LES.

This module prepares an explicit k-epsilon / unity-Lewis eddy-diffusivity
diagnostic on a new G2 case. It tests mean-flow mixing with either a fixed-chi
steady flamelet or the explicitly selected transported-progress FGM table. It is not Sharma's LES, a presumed-PDF combustion model, a
validated turbulence closure, or permission to publish an accepted paper match.

`configure.mjs CASE CONFIG.json` is read-only. Add `--apply` inside an admitted
allocation to modify a newly prepared, undecomposed, time-zero case. Inputs are
the direct-G2 manifest, its original dictionaries/fields, and the explicit JSON
configuration illustrated by `example.json`. The script requires cold real-fluid
initialization and preserves the selected physical table, geometry, registered
stream conditions, mean velocity boundary conditions, scalar limits and timestep.
It writes k, epsilon, nut and alphat; exact momentum/thermal selections; required
solver/scheme entries; a declared closure flag; and hashes of every modification.
Repeated configuration or an evolved/decomposed case is refused.

The default example adopts inlet intensity 0.05 and length 0.004 m from Cutrone
et al., Computers & Fluids 39 (2010), Table 5, p. 496, DOI
[10.1016/j.compfluid.2009.10.001](https://doi.org/10.1016/j.compfluid.2009.10.001).
These are adopted inputs, not measured values for our geometry. That work uses
k-omega/FPV and differs from this k-epsilon/fixed-chi diagnostic. Sharma's 2023
paper specifies dynamic Smagorinsky-Lilly LES, Pr_SGS 0.85 and Sc_t 0.7, beta-PDF
averaging, and millions of 3D cells; it does not supply inlet k/epsilon values.

At an inlet, stock OF8 conditions evaluate k=1.5*(I*|U|)^2 and
epsilon=Cmu^0.75*k^1.5/L using the actual local velocity and k, with Cmu 0.09.
The stationary initial domain instead receives the declared positive numerical
seed k=1e-6 m2/s2 and epsilon derived from its specified length. Outlet backflow
uses the same seed. No evolved turbulence field is reused. No-slip walls use
kqRWallFunction, epsilonWallFunction and nutkWallFunction; slip surfaces retain
zero-gradient k/epsilon and calculated nut. The adiabatic wall alphat is zero.
Wall-function suitability must be assessed using actual yPlus; a 100 us run alone
does not establish a developed mean or wall-resolved result.

This first combination fixes Prt=0.7 and uses the same effective mass and heat
diffusivity, alpha+rho*nut/0.7. It therefore differs from Sharma's Prt 0.85.
The selected eddyDiffusivity flux uses thermo.alphaEff, not species Dimix.
The default FGM variant uses the normal full-property path and computes the
otherwise unused Dimix; its overhead must be measured against the explicitly
selected new optimization. Non-unity transport is deliberately
excluded: its species enthalpy flux needs a separate absolute-Ha audit.

Dependencies are Node, the direct-G2 generator/initializer, the existing full
SRK runtime, stock kEpsilon/eddyDiffusivity models and boundary conditions, and
the narrowly declared steady/split-FGM Dimix policy. Their constructor guards must
be rebuilt and qualified; dictionary changes alone cannot enable this path.
No new external library, model ABI, network access or secret is introduced.
Downstream allocated execution owns compilation, MPI, run timing and evidence.
The full-property FGM path requires no policy-header or runtime-library change;
exact existing library products must still be verified.

Minimal use:

```sh
node replication/validation/mascotte-g2/rans-diagnostic/configure.mjs /workspace/cases/new-g2 replication/validation/mascotte-g2/rans-diagnostic/example.json
```

Verify source with `node --check configure.mjs` and `git diff --check`. Review the
read-only plan against a real generated case. The first allocated qualification
must verify model selection and finite k/epsilon/nut, unchanged property results,
fresh 100 us execution, conservative budgets, fixed scalar bounds and actual
profiles. Retain failures and compare the laminar baseline. No runtime success
is asserted by these preparation checks.

The first composite build must rebuild `fluidThermophysicalModels`,
`reactionThermophysicalModels` and `combustionModels`: the policy is an inline
constructor dependency of the selected hePsiThermo/SRK templates and the
steady-flamelet model. The remaining twelve libraries can retain their exact
qualified hashes. Rebuild the solver and property probe against this same
header set to avoid mixed inline policy definitions; no new registration is
required for the already available kEpsilon or eddyDiffusivity models.


`node initialize-duct-turbulence.mjs FRESH_CASE [--apply]` is an explicit
initial-condition experiment after analytic duct velocity initialization and
before decomposition. It sets k=1.5(I|U|)^2, epsilon=Cmu^0.75 k^1.5/L,
nut=Cmu k^2/epsilon and alphat=rho nut/Prt in the two upstream passages,
using the configured inlet intensity/length and executing pure-stream densities.
Chamber seeds and all boundary conditions remain unchanged. It addresses the
mismatch between primed inlet velocity and a nearly stagnant uniform turbulence
seed, not a combustion calibration or proof of the RANS failure cause. Default
is read-only; --apply requires Slurm and fresh original-zero fields. Inputs
are the bound RANS/velocity/EOS receipts and actual U/Z fields; output binds
all four before/after field hashes and measured ranges. Node built-ins only;
no network, credentials, CFD advance or scheduler interface. Verify readonly
behavior and analytic k/epsilon/viscosity consistency, then compare independent
cold and reacting original-zero physical controls. Failure remains failure.
