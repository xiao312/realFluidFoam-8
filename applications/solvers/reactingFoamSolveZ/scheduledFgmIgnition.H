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
                    const scalar value=coordinates[peak];
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
            << " maxDeltaC=" << maxDeltaC
            << " maxDeltaHa=" << gMax(mag(fgmAbsoluteEnthalpy().primitiveField()-savedHa))
            << " massBefore=" << massBefore << " massAfter=" << fvc::domainIntegrate(rho).value()
            << " Tmin=" << min(thermo.T()).value() << " Tmax=" << max(thermo.T()).value()
            << " sameProcess=1 sourceEnabled=1" << endl;
        fgmColdFlowActive=false;
    }
}
