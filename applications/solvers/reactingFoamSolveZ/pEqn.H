rho = thermo.rho();

// Isolate the author's real-gas time correction from changes to energy ordering.
// Default remains the stock reactingFoam psi-product time operator.
const bool useRealFluidDensityTimeCorrection = runTime.controlDict()
    .lookupOrDefault<Switch>("realFluidDensityTimeCorrection", false);
const bool useDifferentialPressure = runTime.controlDict()
    .lookupOrDefault<Switch>("realFluidDifferentialPressure", false);
volScalarField pressureDensitySlope("pressureDensitySlope", psi);
autoPtr<volScalarField> pressureDensityTimeOffset;
if (useDifferentialPressure)
{
    if (pimple.transonic() || LTS)
        FatalErrorInFunction << "Differential pressure mode requires nontransonic global time"
            << exit(FatalError);
    updateSrkPressureDensitySlope(thermo, pressureDensitySlope);
    // Evaluate once: repeated nonorthogonal solves retain the same reference.
    pressureDensityTimeOffset.reset(new volScalarField
    (
        "pressureDensityTimeOffset",
        fvc::ddt(rho)-fvc::ddt(pressureDensitySlope,p)
    ));
    if (runTime.timeIndex()==1 || runTime.writeTime())
    {
        const tmp<volScalarField> slopeRatio=pressureDensitySlope/psi;
        Info<< "pressureTimeForm=srkDifferentialIncrement t=" << runTime.value()
            << " slopeRatioMin=" << gMin(slopeRatio().primitiveField())
            << " slopeRatioMax=" << gMax(slopeRatio().primitiveField()) << endl;
    }
}
auto pressureTimeOperator = [&]() -> tmp<fvScalarMatrix>
{
    if (useDifferentialPressure)
        return pressureDensityTimeOffset()+fvm::ddt(pressureDensitySlope,p);
    if (useRealFluidDensityTimeCorrection)
        return fvc::ddt(rho) - fvc::ddt(psi, p) + fvm::ddt(psi, p);
    return fvm::ddt(psi, p);
};
if (useRealFluidDensityTimeCorrection && !useDifferentialPressure && (runTime.timeIndex()==1 || runTime.writeTime()))
    Info<< "pressureTimeForm=realFluidDensityCorrection t=" << runTime.value() << endl;

const volScalarField rAU(1.0/UEqn.A());
const surfaceScalarField rhorAUf("rhorAUf", fvc::interpolate(rho*rAU));

tmp<volScalarField> rAtU
(
    pimple.consistent()
  ? volScalarField::New("rAtU", 1.0/(1.0/rAU - UEqn.H1()))
  : tmp<volScalarField>(nullptr)
);
tmp<surfaceScalarField> rhorAtUf
(
    pimple.consistent()
  ? surfaceScalarField::New("rhoRAtUf", fvc::interpolate(rho*rAtU()))
  : tmp<surfaceScalarField>(nullptr)
);

const volScalarField& rAAtU = pimple.consistent() ? rAtU() : rAU;
const surfaceScalarField& rhorAAtUf =
    pimple.consistent() ? rhorAtUf() : rhorAUf;

volVectorField HbyA(constrainHbyA(rAU*UEqn.H(), U, p));

if (pimple.nCorrPiso() <= 1)
{
    tUEqn.clear();
}

surfaceScalarField phiHbyA
(
    "phiHbyA",
    (
        fvc::interpolate(rho)*fvc::flux(HbyA)
      + MRF.zeroFilter(rhorAUf*fvc::ddtCorr(rho, U, phi))
    )
);

MRF.makeRelative(fvc::interpolate(rho), phiHbyA);

if (pimple.transonic())
{
    surfaceScalarField phid
    (
        "phid",
        (fvc::interpolate(psi)/fvc::interpolate(rho))*phiHbyA
    );

    phiHbyA -= fvc::interpolate(psi*p)*phiHbyA/fvc::interpolate(rho);

    if (pimple.consistent())
    {
        phiHbyA += (rhorAAtUf - rhorAUf)*fvc::snGrad(p)*mesh.magSf();
        HbyA += (rAAtU - rAU)*fvc::grad(p);
    }

    while (pimple.correctNonOrthogonal())
    {
        fvScalarMatrix pEqn
        (
            pressureTimeOperator()
          + fvc::div(phiHbyA) + fvm::div(phid, p)
          - fvm::laplacian(rhorAAtUf, p)
         ==
            fvOptions(psi, p, rho.name())
        );

        pEqn.solve();

        if (pimple.finalNonOrthogonalIter())
        {
            phi == phiHbyA + pEqn.flux();
        }
    }
}
else
{
    if (pimple.consistent())
    {
        phiHbyA += (rhorAAtUf - rhorAUf)*fvc::snGrad(p)*mesh.magSf();
        HbyA += (rAAtU - rAU)*fvc::grad(p);
    }

    // Update the pressure BCs to ensure flux consistency
    constrainPressure(p, rho, U, phiHbyA, rhorAAtUf, MRF);

    while (pimple.correctNonOrthogonal())
    {
        fvScalarMatrix pEqn
        (
            pressureTimeOperator()
          + fvc::div(phiHbyA)
          - fvm::laplacian(rhorAAtUf, p)
         ==
            fvOptions(psi, p, rho.name())
        );

        pEqn.solve();

        if (pimple.finalNonOrthogonalIter())
        {
            phi = phiHbyA + pEqn.flux();
        }
    }
}

#include "rhoEqn.H"
#include "compressibleContinuityErrs.H"

// Explicitly relax pressure for momentum corrector
p.relax();

U = HbyA - rAAtU*fvc::grad(p);
U.correctBoundaryConditions();
fvOptions.correct(U);
K = 0.5*magSqr(U);

auditFgmContinuityStage("beforePressureLimit", rho, phi);
if (pressureControl.limit(p))
{
    p.correctBoundaryConditions();
    rho = thermo.rho();
    auditFgmContinuityStage("afterPressureEOSDensity", rho, phi);
    // OF8 limit() reports configured bounds, not whether p was changed.
    // Keep its pressure/EOS update, then restore conservative rho for the
    // next outer transport solve. The scalar equation and its bounds stay
    // unchanged; this is the same density equation already used above.
    if (conserveTabulatedDensity)
    {
        #include "rhoEqn.H"
        auditFgmContinuityStage("afterPressureDensitySolve", rho, phi);
    }
}

if (thermo.dpdt())
{
    dpdt = fvc::ddt(p);
}
