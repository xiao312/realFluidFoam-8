const word fgmEnergyForm
(
    runTime.controlDict().lookupOrDefault<word>("fgmEnergyForm", "sensibleEnthalpy")
);
const bool absoluteEnthalpyFGM = fgmEnergyForm == "absoluteEnthalpy";
const Switch fgmProgressSourceEnabled
(
    runTime.controlDict().lookupOrDefault<Switch>("fgmProgressSourceEnabled", true)
);
if (!fgmProgressSourceEnabled && !absoluteEnthalpyFGM)
{
    FatalErrorInFunction << "Source-disabled FGM diagnostic requires absoluteEnthalpy mode" << exit(FatalError);
}
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
    if (runTime.controlDict().lookupOrDefault<Switch>("fgmRequireHaInitialization", false))
    {
        IOdictionary initialization
        (
            IOobject
            (
                "fgmHaInitialization", runTime.constant(), mesh,
                IOobject::MUST_READ, IOobject::NO_WRITE
            )
        );
        if (runTime.value() != 0 || initialization.lookup<scalar>("preparedTime") != 0)
            FatalErrorInFunction << "Guarded Ha initialization requires a fresh time-zero case" << exit(FatalError);
        const dictionary& prepared = initialization.subDict("thermoType");
        const dictionary& selected = thermo.subDict("thermoType");
        forAllConstIter(dictionary, selected, entry)
        {
            const word key = entry().keyword();
            if (prepared.lookup<word>(key) != selected.lookup<word>(key))
                FatalErrorInFunction << "Ha initialization thermoType differs at " << key << exit(FatalError);
        }
    }
    fgmAbsoluteEnthalpy.reset
    (
        new volScalarField
        (
            IOobject("Ha", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::AUTO_WRITE),
            mesh
        )
    );
    updateFgmFixedTemperatureEnthalpy(thermo, composition, fgmAbsoluteEnthalpy());
    thermo.he() == fgmAbsoluteEnthalpy() - fgmChemicalEnthalpy(mesh, composition);
    thermo.correct();
    rho = thermo.rho();
    // Density-dependent inlet velocity must use this initialized EOS state,
    // not a placeholder velocity serialized by a different thermodynamic model.
    U.correctBoundaryConditions();
    K = 0.5*magSqr(U);
    phi = fvc::flux(rho*U);
}
Info<< "FGM energy form: " << fgmEnergyForm
    << "; table Q is " << (absoluteEnthalpyFGM ? "diagnostic only" : "an explicit source") << endl;
