// Direct state integrals, including time zero. No reconstruction from T,p,Y.
if (writeEnergyBudget)
{
    const scalar volume = gSum(mesh.V());
    const volScalarField& transportedEnergy = absoluteEnthalpyFGM ? fgmAbsoluteEnthalpy() : thermo.he();
    const scalar H = fvc::domainIntegrate(rho*transportedEnergy).value();
    const scalar Hchemical = fvc::domainIntegrate(rho*fgmChemicalEnthalpy(mesh, composition)).value();
    const scalar PV = fvc::domainIntegrate(p).value();
    const scalar KE = fvc::domainIntegrate(rho*K).value();
    Info<< "energyState t=" << runTime.value()
        << " volume=" << volume
        << " mass=" << fvc::domainIntegrate(rho).value()
        << " H=" << H << " PV=" << PV << " K=" << KE
        << " Hchemical=" << Hchemical
        << " E=" << H + KE - (thermo.he().name() == "h" ? PV : 0)
        << " Tmean=" << fvc::domainIntegrate(T).value()/volume
        << " pmean=" << PV/volume
        << " Cvmean=" << fvc::domainIntegrate(thermo.Cv()).value()/volume
        << " sourceW=" << (absoluteEnthalpyFGM ? 0 : fvc::domainIntegrate(reaction->Qdot()).value())
        << " diagnosticSourceW=" << fvc::domainIntegrate(reaction->Qdot()).value();
    if (mesh.foundObject<volScalarField>("c"))
    {
        Info<< " cmean=" << fvc::domainIntegrate
            (mesh.lookupObject<volScalarField>("c")).value()/volume;
    }
    Info<< endl;
}
