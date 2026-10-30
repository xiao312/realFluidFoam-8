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

    EEqn.solve();

    fvOptions.correct(he);

    if (writeEnergyBudget)
    {
        // OF8 residual() reads off-diagonal storage even for a purely diagonal
        // operator such as fvm::ddt. The non-const upper() accessor allocates
        // explicit zeros if both triangles are absent, or copies the existing
        // symmetric triangle. Do this only on the retained diagnostic matrices,
        // after the real EEqn has been solved; no equation coefficient changes.
        energyDdt.ref().upper();
        energyConvection.ref().upper();
        energyDiffusion.ref().upper();
        physicalEquation().upper();
        // fvMatrix::residual is source - A*he, already cell integrated.
        // Negating a standalone operator residual gives its signed LHS watts.
        const tmp<scalarField> residual = physicalEquation().residual();
        Info<< "energyEquation t=" << runTime.value()
            << " ddtW=" << -gSum(energyDdt().residual()())
            << " convectionW=" << -gSum(energyConvection().residual()())
            << " diffusionW=" << -gSum(energyDiffusion().residual()())
            << " kineticW=" << fvc::domainIntegrate(kineticTerms).value()
            << " pressureW=" << fvc::domainIntegrate(pressureWork).value()
            << " sourceW=" << fvc::domainIntegrate(heatRelease).value()
            << " residualW=" << -gSum(residual())
            << " residualL1W=" << gSum(mag(residual()))
            << endl;
    }

    if (absoluteEnthalpyFGM)
    {
        thermo.he() == fgmAbsoluteEnthalpy() - fgmChemicalEnthalpy(mesh, composition);
    }
    thermo.correct();

    Info<< "min/max(T) = "
        << min(T).value() << ", " << max(T).value() << endl;
}
