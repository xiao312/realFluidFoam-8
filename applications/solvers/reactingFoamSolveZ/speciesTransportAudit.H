// Read-only predictor diagnostics. No field values or acceptance limits change.
if (auditSpeciesTransport)
{
    reduce(minimumRawSpecies, minOp<scalar>());
    reduce(maximumClipAddition, maxOp<scalar>());
    const scalar maximumNonclosureSum = gMax(Yt.primitiveField());
    const scalar maximumRawNonclosureSum = gMax(rawTransportSum().primitiveField());
    const tmp<volScalarField> continuityDefect = fvc::ddt(rho)+fvc::div(phi);
    const scalar maximumRelativeContinuity = gMax
    (
        runTime.deltaTValue()*mag(continuityDefect().primitiveField())
       /max(mag(rho.primitiveField()),scalar(SMALL))
    );
    Info<< "speciesTransportAudit t=" << runTime.value()
        << " closureSpecies=" << Y[inertIndex].name()
        << " minRawY=" << minimumRawSpecies
        << " maxSingleSpeciesClipAddition=" << maximumClipAddition
        << " maxRawNonclosureSum=" << maximumRawNonclosureSum
        << " maxClippedNonclosureSum=" << maximumNonclosureSum
        << " minUnclippedClosure=" << 1-maximumNonclosureSum
        << " maxRelativeContinuityDefect=" << maximumRelativeContinuity
        << " stage=beforeTableRelaxation fieldsModified=0" << endl;
    if (maximumNonclosureSum > 1+1e-8)
    {
        // Retain the actual invalid predictor before the unchanged model guard
        // rejects its relaxed update. These snapshots are not restart inputs.
        forAll(Y,i) Y[i].write();
        rho.write();thermo.p().write();thermo.T().write();thermo.he().write();
        const word witnessFields[] = {"Ha","Z","c"};
        for (const word& fieldName : witnessFields)
            if (mesh.foundObject<volScalarField>(fieldName))
                mesh.lookupObject<volScalarField>(fieldName).write();
        Info<< "speciesTransportFailureWitness t=" << runTime.value()
            << " stage=beforeTableRelaxation authorizedForRestart=0" << endl;
    }
}
