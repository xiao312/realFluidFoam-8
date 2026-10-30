const word fgmEnergyForm
(
    runTime.controlDict().lookupOrDefault<word>("fgmEnergyForm", "sensibleEnthalpy")
);
const bool absoluteEnthalpyFGM = fgmEnergyForm == "absoluteEnthalpy";
if (!absoluteEnthalpyFGM && fgmEnergyForm != "sensibleEnthalpy")
{
    FatalErrorInFunction << "Unknown fgmEnergyForm " << fgmEnergyForm << exit(FatalError);
}
autoPtr<volScalarField> fgmAbsoluteEnthalpy;
if (absoluteEnthalpyFGM)
{
    if (!reaction->compositionTabulated() || thermo.he().name() != "h")
    {
        FatalErrorInFunction << "absoluteEnthalpy needs tabulated composition and sensibleEnthalpy thermo"
            << exit(FatalError);
    }
    const word transportType = thermophysicalTransport->type();
    if (transportType != "Fourier" && transportType != "eddyDiffusivity")
    {
        FatalErrorInFunction << "absoluteEnthalpy only qualifies unity-Lewis enthalpy diffusion; selected "
            << transportType << exit(FatalError);
    }
    fgmAbsoluteEnthalpy.reset
    (
        new volScalarField
        (
            IOobject("Ha", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::AUTO_WRITE),
            mesh
        )
    );
    thermo.he() == fgmAbsoluteEnthalpy() - fgmChemicalEnthalpy(mesh, composition);
    thermo.correct();
    rho = thermo.rho();
    phi = fvc::flux(rho*U);
}
Info<< "FGM energy form: " << fgmEnergyForm
    << "; table Q is " << (absoluteEnthalpyFGM ? "diagnostic only" : "an explicit source") << endl;
