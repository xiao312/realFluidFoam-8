# G2 RANS mixing diagnostic

The generator accepts the registered5.61MPa/85/288K and Schmitt5.6MPa/83/300K
stream sets. Each requires its own actual physical table and thermo identity.
The kEpsilon/delta-PDF approximation remains distinct from the reference LES.

This module prepares an explicit k-epsilon / unity-Lewis eddy-diffusivity
diagnostic on a new G2 case. It tests mean-flow mixing with the existing fixed-chi
steady flamelet. It is not Sharma's LES, a presumed-PDF combustion model, a
validated turbulence closure, or permission to publish an accepted paper match.

`configure.mjs CASE CONFIG.json` is read-only. Add `--apply` inside an admitted
allocation to modify a newly prepared, undecomposed, time-zero case. Inputs are
the direct-G2 manifest, its original dictionaries/fields, and the explicit JSON
configuration illustrated by `example.json`. The script requires cold real-fluid
steady-table initialization at 5.61 MPa and preserves the physical table, geometry,
85/288 K streams, mean velocity boundary conditions, scalar limits and timestep.
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
The implemented eddyDiffusivity calls thermo.alphaEff and never Dimix, so the
existing unused-Dimix optimization can be extended to this exact declared path.
The policy continues to refuse all other RAS/LES/model combinations and all
public/raw Dimix access while suppressed. Non-unity transport is deliberately
excluded: its species enthalpy flux needs a separate absolute-Ha audit.

Dependencies are Node, the direct-G2 generator/initializer, the existing full
SRK runtime, stock kEpsilon/eddyDiffusivity models and boundary conditions, and
the narrow steadyFlamelet/Dimix policy extension. Their constructor guards must
be rebuilt and qualified; dictionary changes alone cannot enable this path.
No new external library, model ABI, network access or secret is introduced.
Downstream allocated execution owns compilation, MPI, run timing and evidence.

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
