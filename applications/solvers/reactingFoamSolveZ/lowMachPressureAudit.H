// Report actual mechanical pressure and SRK acoustic scale, not constant p0 PEP.
if (lowMachPressureSplit && (runTime.timeIndex()==0 || runTime.writeTime()))
{
    volScalarField betaT("lowMachBetaT",thermo.psi());
    updateSrkPressureDensitySlope(thermo,betaT,false);
    const tmp<volScalarField> soundSpeedSquared=(thermo.Cp()/thermo.Cv())/betaT;
    if (gMin(soundSpeedSquared().primitiveField())<=0)
        FatalErrorInFunction << "Nonpositive SRK isentropic sound-speed squared"
            << exit(FatalError);
    const tmp<volScalarField> eosDensity=thermo.rho();
    Info<< "lowMachModelAudit t=" << runTime.value()
        << " maxMach=" << gMax(mag(U.primitiveField())
            /sqrt(soundSpeedSquared().primitiveField()))
        << " maxMechanicalPressureDeparture=" << gMax
            (mag(p.primitiveField()-lowMachBackgroundPressure))/lowMachBackgroundPressure
        << " maxEOSPressureDeparture=" << gMax
            (mag(thermo.p().primitiveField()-lowMachBackgroundPressure))/lowMachBackgroundPressure
        << " maxDensityRelative=" << gMax
            (mag(rho.primitiveField()-eosDensity().primitiveField())
            /max(mag(eosDensity().primitiveField()),scalar(SMALL)))
        << " enthalpyBudget=thermal mechanicalPressureNotEOS=1" << endl;
}
