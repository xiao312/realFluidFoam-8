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

## Offline coefficient characterization

Using the executing probe's exported mixture coefficients and its retained
forward-query temperatures, an independent NumPy polynomial-root calculation
compared literal isothermal d(rho)/dp with rho/p. This is offline arithmetic on
previously executed property states, not new CFD or qualification of a solver.
The ratio ranges below include only points with unchanged root topology across
a relative pressure perturbation1e-7 and finite-difference agreement within1e-4:

| Captured composition | Original pressure ratio range | Failed pressure ratio range |
| --- | --- | --- |
| Cavalieri mixed cell | 0.1871–10.578 | 0.1919–220.288 |
| Schmitt mixed cell | 0.1886–10.824 | 0.1932–239.258 |
| Pure oxygen contact | 0.02194–0.05074 | 0.007948–106.833 |

There are306 sampled property states. Nine near branch changes or poorly
resolved finite-pressure differences are excluded from these summary ranges,
but retained in the raw diagnostic with explicit flags. None is declared passed
by omission. The1e-4 finite-difference comparison is a new arithmetic diagnostic,
not a relaxation of any existing1e-8 caloric/EOS or paper agreement criterion.
This derivative is at fixed T and composition; it is not the complete coupled
absolute-Ha Jacobian or a substitute for conservation/pressure-equilibrium tests.

The result supports testing a consistent differential-pressure linearization
alongside the existing secant formulation. It does not establish it as the cause
of the reacting-G2 failure or guarantee that changing a matrix coefficient alone
will fix it. The distinct enthalpy-branch gap remains an observed limitation.
Raw diagnostic and source identities are retained under the campaign state in
srk-pressure-coefficient-audit.csv/.json; coefficients job128018627 and query
states job128016838. All future CFD comparisons must start from fresh time zero.
