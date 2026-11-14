// Included after the solved-field matrix audit and before tabulated lookup.
if (projectTabulatedZRoundoff)
{
    scalar minimum=GREAT, maximum=-GREAT;
    label invalid=0;
    const auto scan = [&](const scalar value)
    {
        if (!std::isfinite(value)) ++invalid;
        else { minimum=min(minimum,value); maximum=max(maximum,value); }
    };
    forAll(Z, celli)
    {
        scan(Z[celli]);
        if (!std::isfinite(rho[celli]) || rho[celli]<=0
         || !std::isfinite(mesh.V()[celli]) || mesh.V()[celli]<=0
         || !std::isfinite(rho[celli]*mesh.V()[celli])
         || rho[celli]*mesh.V()[celli]<=0)
        {
            ++invalid;
            // Read stored fields only, so another EOS evaluation cannot mask
            // the original failure. Limit output per rank, never validity.
            if (invalid <= 16)
            {
                std::ostringstream state;
                state << std::setprecision(17) << "fgmZInvalidTransportState t="
                    << runTime.value() << " rank=" << Pstream::myProcNo()
                    << " cell=" << celli << " centre=" << mesh.C()[celli]
                    << " rho=" << rho[celli] << " oldRho=" << rho.oldTime()[celli]
                    << " volume=" << mesh.V()[celli] << " Z=" << Z[celli]
                    << " p=" << thermo.p()[celli] << " T=" << thermo.T()[celli]
                    << " Hs=" << thermo.he()[celli]
                    << " Ha=" << (absoluteEnthalpyFGM ? fgmAbsoluteEnthalpy()[celli] : 0)
                    << " absoluteHaEnabled=" << absoluteEnthalpyFGM
                    << " massFractions=";
                forAll(Y, i) state << Y[i].name() << ':' << Y[i][celli] << ',';
                state << " fieldsModified=0 EOSreevaluated=0";
                Info<< state.str().c_str() << endl;
            }
        }
    }
    forAll(Z.boundaryField(), patchi)
        forAll(Z.boundaryField()[patchi], facei) scan(Z.boundaryField()[patchi][facei]);
    reduce(minimum,minOp<scalar>()); reduce(maximum,maxOp<scalar>());
    reduce(invalid,sumOp<label>());
    try { forgeZRoundoff::requireRange(minimum,maximum,invalid); }
    catch (const std::exception& error)
    {
        std::ostringstream evidence;
        evidence << std::setprecision(17) << error.what()
            << " t=" << runTime.value() << " minimum=" << minimum
            << " maximum=" << maximum << " invalid=" << invalid
            << " limit=" << forgeZRoundoff::limit() << " fieldsModified=0";
        FatalErrorInFunction << evidence.str().c_str() << exit(FatalError);
    }

    label cells=0;
    scalar mass=0, absoluteMass=0, maximumDelta=0;
    forAll(Z, celli)
    {
        const scalar original=Z[celli];
        const scalar value=forgeZRoundoff::projected(original);
        const scalar delta=value-original;
        if (delta != 0)
        {
            ++cells;
            const scalar correction=rho[celli]*mesh.V()[celli]*delta;
            mass+=correction; absoluteMass+=mag(correction);
            maximumDelta=max(maximumDelta,mag(delta));
            Z[celli]=value;
        }
    }
    reduce(cells,sumOp<label>()); reduce(mass,sumOp<scalar>());
    reduce(absoluteMass,sumOp<scalar>()); reduce(maximumDelta,maxOp<scalar>());
    cumulativeZRoundoffMass+=mass;
    cumulativeZRoundoffAbsoluteMass+=absoluteMass;
    cumulativeZRoundoffCells+=cells;
    // No direct boundary assignment: fixedValue inputs retain their values.
    Z.correctBoundaryConditions();
    const scalar beforeMinimum=minimum, beforeMaximum=maximum;
    minimum=GREAT; maximum=-GREAT; invalid=0;
    forAll(Z, celli) scan(Z[celli]);
    forAll(Z.boundaryField(), patchi)
        forAll(Z.boundaryField()[patchi], facei) scan(Z.boundaryField()[patchi][facei]);
    reduce(minimum,minOp<scalar>()); reduce(maximum,maxOp<scalar>());
    reduce(invalid,sumOp<label>());
    std::ostringstream ledger;
    ledger << std::setprecision(17) << "fgmZRoundoffProjection t=" << runTime.value()
        << " beforeMinimum=" << beforeMinimum << " beforeMaximum=" << beforeMaximum
        << " afterMinimum=" << minimum << " afterMaximum=" << maximum
        << " cells=" << cells << " maxDelta=" << maximumDelta
        << " signedMassKg=" << mass << " absoluteMassKg=" << absoluteMass
        << " cumulativeSignedMassKg=" << cumulativeZRoundoffMass
        << " cumulativeAbsoluteMassKg=" << cumulativeZRoundoffAbsoluteMass
        << " cumulativeCells=" << cumulativeZRoundoffCells
        << " limit=" << forgeZRoundoff::limit()
        << " fieldsModified=" << (cells>0 ? 1 : 0)
        << " oldTimeModified=0 prescribedBoundariesModified=0";
    Info<< ledger.str().c_str() << endl;
    try { forgeZRoundoff::requireRange(minimum,maximum,invalid); }
    catch (const std::exception& error)
    {
        FatalErrorInFunction << error.what()
            << "; boundary reevaluation failed after the recorded internal correction"
            << exit(FatalError);
    }
}
