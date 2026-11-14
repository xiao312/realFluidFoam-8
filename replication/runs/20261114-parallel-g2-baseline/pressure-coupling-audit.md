# Pressure-coupling audit: next reacting-G2 diagnostic

This is a source comparison and test proposal, not an implemented correction.
The full stable-SRK runtime job128022863 must be reconciled before reusing its
products. Existing captured enthalpy gaps and failed CFD verdicts remain.

The current reactingFoamSolveZ pressure time operator matches official
[OpenFOAM8 reactingFoam](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/applications/solvers/combustion/reactingFoam/pEqn.H):
its nontransonic pressure equation uses fvm::ddt(psi,p), while a separate density
continuity equation follows the pressure solve. Therefore this operator is not
an accidental local deviation from that baseline. Our additional density audit
and continuity-restoration option do not by themselves eliminate the observed
contact instability.

Official [OF8 rhoPimpleFoam](https://github.com/OpenFOAM/OpenFOAM-8/blob/master/applications/solvers/compressible/rhoPimpleFoam/pEqn.H)
instead uses an explicit density time residual with a pressure-increment term,
then a thermodynamic density update and continuity solve. It is a useful
implementation reference, but cannot be copied without checking the selected
psiReactionThermo API, density ownership, flux correction, time discretization,
boundaries and absolute-Ha coupling. Its different thermo class matters.

The fork's SRK psi(p,T)=rho/p is a secant coefficient. At fixed composition and
temperature the literal EOS differential compressibility is instead
1/(dp/drho)_T. For SRK written in mass variables b_m=b/W and a_m=a/W²:

    (dp/drho)_T = R*T/(1-b_m*rho)²
                  - a_m*rho*(2+b_m*rho)/(1+b_m*rho)²

These are identical for an ideal gas and generally differ for a dense fluid.
The isolated contact application's acoustic calculation already uses this
literal derivative. That does not prove that substituting it into one term of
the existing pressure loop is sufficient or consistent.

Next experiments should first quantify derivative/secant ratios against
independent finite differences on single-root states, then compare complete
pressure-coupling candidates on uniform, nonreacting contact and clean-start
cold-mixing controls. Preserve original pressure/velocity equilibrium targets,
caloric/EOS limits and explicit mass/energy accounting. Only then test both fresh
reacting-G2 conditions. Do not replace a missing enthalpy state by a fit or
pretend that a pressure-operator change solves the separate EOS branch policy.
