// Run BEFORE runTime++: the next oldTime includes ignition; never assign oldTime.
if (fgmColdFlowActive)
{
    const scalar now = runTime.value();
    if (now-fgmColdLastTime >= .05 || now >= fgmIgnitionTime)
    {
        Info<< "fgmColdFlowChange t=" << now << " lag=" << now-fgmColdLastTime
            << " maxDeltaZ=" << gMax(mag(fgmSourceModel->Z().primitiveField()-fgmColdPreviousZ))
            << " maxDeltaU=" << gMax(mag(U.primitiveField()-fgmColdPreviousU))
            << " sourceEnabled=0" << endl;
        fgmColdPreviousZ = fgmSourceModel->Z().primitiveField();
        fgmColdPreviousU = U.primitiveField();
        fgmColdLastTime = now;
    }
    if (now >= fgmIgnitionTime)
    {
        volScalarField& ignitionC = *reaction->progressVariable();
        const scalarField savedHa(fgmAbsoluteEnthalpy().primitiveField());
        const scalar massBefore = fvc::domainIntegrate(rho).value();
        label selected = 0;
        scalar maxDeltaC = 0;
        forAll(ignitionC, celli)
        {
            const scalar z = fgmSourceModel->Z()[celli];
            if (mesh.C()[celli].x() >= 0 && mesh.C()[celli].x() <= fgmIgnitionLength
                && z >= fgmIgnitionZMin && z <= fgmIgnitionZMax)
            {
                std::vector<double> coordinates, sources;
                fgmIgnitionTable().sourceCurve(z, coordinates, sources);
                label peak = 0;
                for (label j=1; j<label(sources.size()); ++j)
                    if (sources[j] > sources[peak]) peak=j;
                if (sources[peak] > 0)
                {
                    const scalar value=fgmIgnitionMode == "upperProgress" ? coordinates.back() : coordinates[peak];
                    maxDeltaC=max(maxDeltaC,mag(value-ignitionC[celli]));
                    ignitionC[celli]=value;
                    ++selected;
                }
            }
        }
        reduce(selected,sumOp<label>());
        reduce(maxDeltaC,maxOp<scalar>());
        if (!selected) FatalErrorInFunction << "Ignition selected no positive-source cells" << exit(FatalError);
        ignitionC.correctBoundaryConditions();
        reaction->correct();
        thermo.he() == fgmAbsoluteEnthalpy() - fgmChemicalEnthalpy(mesh, composition);
        thermo.correct();
        thermo.correct();
        rho = thermo.rho();
        Info<< "fgmIgnition t=" << now << " cells=" << selected
            << " mode=" << fgmIgnitionMode << " maxDeltaC=" << maxDeltaC
            << " maxDeltaHa=" << gMax(mag(fgmAbsoluteEnthalpy().primitiveField()-savedHa))
            << " massBefore=" << massBefore << " massAfter=" << fvc::domainIntegrate(rho).value()
            << " Tmin=" << min(thermo.T()).value() << " Tmax=" << max(thermo.T()).value()
            << " sameProcess=1 sourceEnabled=1" << endl;
        if (fgmIgnitionNumericalReset)
        {
            // The pre-event timestep/phi used cold density. Rebuild this numerical
            // state before advancing time; do not change the absolute-Ha field.
            const scalar previousDeltaT=runTime.deltaTValue();
            const scalarField savedPhi(phi.primitiveField());
            const scalarField oldCellFlux(fvc::surfaceSum(mag(phi))().primitiveField());
            const scalar eventCo=.5*gMax(oldCellFlux/(rho.primitiveField()*mesh.V()))*previousDeltaT;
            phi=fvc::flux(rho*U);
            MRF.makeRelative(fvc::interpolate(rho),phi);
            runTime.setDeltaT(min(previousDeltaT,fgmIgnitionDeltaT));
            Info<< "fgmIgnitionStepReset t=" << now << " oldDeltaT=" << previousDeltaT
                << " oldFluxEventCo=" << eventCo
                << " maxInternalPhiChange=" << gMax(mag(phi.primitiveField()-savedPhi))
                << " initialDeltaT=" << runTime.deltaTValue() << endl;
            #include "compressibleCourantNo.H"
            #include "setDeltaT.H"
            Info<< "fgmIgnitionStepReset selectedDeltaT=" << runTime.deltaTValue() << endl;
        }
        fgmColdFlowActive=false;
    }
}
