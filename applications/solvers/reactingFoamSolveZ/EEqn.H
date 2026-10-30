{
    if (absoluteEnthalpyFGM)
    {
        updateFgmFixedTemperatureEnthalpy(thermo, composition, fgmAbsoluteEnthalpy());
    }
    volScalarField& he = absoluteEnthalpyFGM ? fgmAbsoluteEnthalpy() : thermo.he();

    // Retain the assembled operators while diagnosing their budget. In
    // particular, Fourier diffuses he, not a reconstructed Cp*grad(T).
    tmp<fvScalarMatrix> energyDdt(fvm::ddt(rho, he));
    tmp<fvScalarMatrix> energyConvection(mvConvection->fvmDiv(phi, he));
    tmp<fvScalarMatrix> energyDiffusion(thermophysicalTransport->divq(he));
    volScalarField kineticTerms(fvc::ddt(rho, K) + fvc::div(phi, K));
    volScalarField pressureWork
    (
        he.name() == "e"
          ? fvc::div
            (
                fvc::absolute(phi/fvc::interpolate(rho), U),
                p,
                "div(phiv,p)"
            )
          : -dpdt
    );
    volScalarField heatRelease
    (
        tabulatedHeatRelease.valid()
      ? tabulatedHeatRelease()
      : reaction->Qdot()()
    );
    if (absoluteEnthalpyFGM) heatRelease *= scalar(0);
    fvScalarMatrix EEqn
    (
        energyDdt() + energyConvection() + energyDiffusion()
      + kineticTerms + pressureWork
     ==
        heatRelease
      + fvOptions(rho, he)
    );

    autoPtr<fvScalarMatrix> physicalEquation;
    if (writeEnergyBudget)
    {
        physicalEquation.reset(new fvScalarMatrix(EEqn));
    }
    else
    {
        energyDdt.clear();
        energyConvection.clear();
        energyDiffusion.clear();
    }

    EEqn.relax();

    fvOptions.constrain(EEqn);

    scalar initialAbsoluteResidual = 0;
    scalar reconstructedNormalization = 0;
    if (writeEnergyBudget && writeEnergyResidualAudit)
    {
        initialAbsoluteResidual = gSum(mag(fgmIntegratedResidual(EEqn)()));
        reconstructedNormalization = fgmScalarNormalization(EEqn);
    }
    const solverPerformance energyPerformance = EEqn.solve();
    const scalar finalAbsoluteResidual = writeEnergyBudget && writeEnergyResidualAudit
      ? gSum(mag(fgmIntegratedResidual(EEqn)())) : 0;

    fvOptions.correct(he);

    if (writeEnergyBudget)
    {
        // Source - A*he, counting each coupled neighbour once. Negating an
        // individual operator residual gives its signed integrated LHS watts.
        const tmp<scalarField> residual = fgmIntegratedResidual(physicalEquation());
        Info<< "energyEquation t=" << runTime.value()
            << " ddtW=" << -gSum(fgmIntegratedResidual(energyDdt.ref())())
            << " convectionW=" << -gSum(fgmIntegratedResidual(energyConvection.ref())())
            << " diffusionW=" << -gSum(fgmIntegratedResidual(energyDiffusion.ref())())
            << " kineticW=" << fvc::domainIntegrate(kineticTerms).value()
            << " pressureW=" << fvc::domainIntegrate(pressureWork).value()
            << " sourceW=" << fvc::domainIntegrate(heatRelease).value()
            << " residualW=" << -gSum(residual())
            << " residualL1W=" << gSum(mag(residual()))
            << " linearIterations=" << energyPerformance.nIterations()
            << " linearFinalNormalizedResidual=" << energyPerformance.finalResidual()
            << endl;
        if (writeEnergyResidualAudit)
        {
            const fgmResidualArithmeticAudit arithmetic = fgmResidualArithmetic(physicalEquation());
            // Retain the old API as a witness, not as the acceptance metric.
            // Its const residual path requires off-diagonal storage.
            physicalEquation().upper();
            const tmp<scalarField> legacy = physicalEquation().residual();
            const tmp<scalarField> coupled = fgmCoupledBoundarySource(physicalEquation());
            Info<< "energyResidualAudit t=" << runTime.value()
                << " legacyL1W=" << gSum(mag(legacy()))
                << " coupledSourceW=" << gSum(coupled())
                << " duplicateIdentityErrorL1W=" << gSum(mag(legacy() - residual() - coupled()))
                << " linearInitialAbsoluteL1W=" << initialAbsoluteResidual
                << " linearFinalAbsoluteL1W=" << finalAbsoluteResidual
                << " reconstructedInitialNormW=" << reconstructedNormalization
                << " linearInitialNormalizedResidual=" << energyPerformance.initialResidual()
                << " linearFinalNormalizedResidual=" << energyPerformance.finalResidual()
                << " linearIterations=" << energyPerformance.nIterations()
                << " matrixSummandL1W=" << arithmetic.summandL1W
                << " residualArithmeticBoundW=" << arithmetic.roundoffBoundW
                << " arithmeticOperationsPerCell=" << arithmetic.operationsPerCell
                << endl;
        }
    }

    if (absoluteEnthalpyFGM)
    {
        thermo.he() == fgmAbsoluteEnthalpy() - fgmChemicalEnthalpy(mesh, composition);
    }
    const auto fgmThermoStart = fgmTiming.start();
    thermo.correct();
    fgmTiming.stop(fgmWallTiming::thermoCorrection, fgmThermoStart);
    const auto fgmCaloricStart = fgmTiming.start();
    auditFgmThermoClosure(thermo);
    fgmTiming.stop(fgmWallTiming::caloricAudit, fgmCaloricStart);

    Info<< "min/max(T) = "
        << min(T).value() << ", " << max(T).value() << endl;
}
