# SRK cubic-root evaluation

This module evaluates the existing Soave–Redlich–Kwong EOS using the fork's
species/mixture parameters. It owns density and departure-property calculations;
it does not select chemical rates, fit critical data, or implement phase splitting.
Inputs and public interfaces remain the existing p(Pa), T(K), mixture coefficients
and inherited species R/W. Outputs retain existing SI units and the default largest-real-root policy.
Optional homogeneousGibbs selection is described below; there is no network
dependency or secret handling.

The one-real-root Cardano branch uses the larger-magnitude radical and recovers
its partner through S*Tl=-Q. Independent evaluation of both radicals subtracts
nearly equal numbers near Q=0. Schmitt contact job128021342 exposed this at
6MPa and163.64244606263K: the historical formula returned density274.913430489,
while stable evaluation and independent cubic roots give274.913427476kg/m3.
The transported density was274.913427475. Acceptance limits remain unchanged.
The three-root branch and its largest-root choice are deliberately unchanged;
this does not solve the separate captured G2 enthalpy/branch gap.

Dependencies: existing OpenFOAM scalar/math facilities (cbrt from the existing
math runtime), rfSpecie and SRK mixture. Dependents include fluid/reaction thermo,
transport, chemistry and applications that instantiate the inline EOS. Rebuild
the complete custom runtime from the frozen source when qualifying this change;
do not combine new inline headers with old thermodynamic binaries.

Minimal use is the existing thermo.rho(p,T) call; no new API is required.
Verification: compile all15 custom libraries and the probe/initializer/solvers
through the FlamePilot Slurm adapter; verify exact dynamic linkage; run fresh
uniform/short controls and all six fresh Schmitt20ms contacts with unchanged
1e-8 EOS/caloric limits. Compare actual density to independent cubic roots at
the captured cancellation points. Preserve failed results and energy defects.
Successful root evaluation or contact completion is not reacting-G2 validation.


## Optional homogeneous Gibbs root candidate

`srkRootSelection homogeneousGibbs` in every species dictionary selects the
admissible mechanically stable root with lowest fixed-composition residual Gibbs
energy. Default `largest` preserves historical behavior. This is a homogeneous
phase choice, not a composition-changing stability test or VLE flash; latent
enthalpy gaps may remain. No fitted coefficients, composition or bounds change.

The policy is copied through thermo arithmetic/mixing; inconsistent policies fail
explicitly. Example: `"O2" { srkRootSelection homogeneousGibbs; ... }`. The input
exporter supports `--srk-root-selection homogeneousGibbs` only for SRK. Its default
dictionary remains byte-identical. Rebuild the complete dependent15-library
runtime because the thermo object layout changes; never mix old/new binaries.

Verify default-policy property parity, independent cubic roots/lnphi, captured
point inversion under both policies, and then fresh-time-zero CFD. Actual target
residuals, pressure/energy budgets and phase scope determine interpretation; a
better inversion is not proof of reacting-flow or VLE accuracy.
