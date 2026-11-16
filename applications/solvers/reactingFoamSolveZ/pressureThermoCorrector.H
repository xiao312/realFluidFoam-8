// Statement include: caller owns the momentum matrix and PIMPLE state.
// Additional iterations repeat only pressure/properties, not species or energy.
for (label couplingPass=0;couplingPass<maxRhoHaPressureIterations;++couplingPass)
{
    bool retryPressure=false;
    #include "pEqn.H"
    if (runTime.controlDict().lookupOrDefault<Switch>("realFluidPressureThermoRefresh",false))
    {
        const scalarField heldEnthalpy(thermo.he().primitiveField());
        const auto refreshStart=fgmTiming.start();
        thermo.correct();
        fgmTiming.stop(fgmWallTiming::thermoCorrection,refreshStart);
        const scalar mutation=gMax(mag(thermo.he().primitiveField()-heldEnthalpy));
        if (mutation!=0)
            FatalErrorInFunction << "Post-pressure inversion mutated internal sensible enthalpy"
                << exit(FatalError);
        if (coupledRhoHaState) retryPressure=applySrkRhoHaPredictor
            (thermo,rho,fgmAbsoluteEnthalpy(),"afterPressure")>0;
        const tmp<volScalarField> refreshedDensity=thermo.rho();
        // The scalar equations require the continuity-consistent rho.
        // A property-cache refresh must not undo that selected policy.
        if (!conserveTransportDensity) rho=refreshedDensity();
        auditFgmThermoClosure(thermo, !deferCaloricTrialAudit, deferCaloricTrialAudit);
        auditFgmContinuityStage("afterPressureThermoRefresh",rho,phi);
        if (runTime.timeIndex()==1 || runTime.writeTime())
            Info<< "pressureThermoRefresh t=" << runTime.value()
                << " maxInternalHeChange_J_kg=" << mutation
                << " conservativeDensityPreserved=" << conserveTransportDensity
                << " maxThermoTransportDensityRelative=" << gMax
                (
                    mag(rho.primitiveField()-refreshedDensity().primitiveField())
                   /max(mag(refreshedDensity().primitiveField()),scalar(SMALL))
                ) << endl;
    }

    if (!retryPressure) break;
    Info<<"rhoHaPressureCoupling t="<<runTime.value()<<" pass="<<couplingPass+1
        <<" maximum="<<maxRhoHaPressureIterations<<" nextPressureSolveRequired=1"<<endl;
    if (couplingPass+1==maxRhoHaPressureIterations)
    {
        thermo.p().write();thermo.T().write();thermo.he().write();rho.write();
        fgmAbsoluteEnthalpy().write();U.write();phi.write();K.write();
        forAll(Y,i) Y[i].write();
        if (mesh.foundObject<volScalarField>("Z")) mesh.lookupObject<volScalarField>("Z").write();
        Info<<"rhoHaCouplingFailure authorizedForRestart=0 mechanicalClosureAccepted=0"<<endl;
        FatalErrorInFunction<<"Pressure/property coupling did not reach a state needing no predictor"<<exit(FatalError);
    }
}
