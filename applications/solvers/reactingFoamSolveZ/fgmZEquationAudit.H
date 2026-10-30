// Included after ZEqn.solve/correct. This diagnostic never changes Z or rho.
// It is deliberately separate from the lookup policy and does not accept a run.
if (runTime.controlDict().lookupOrDefault<Switch>("writeMixtureFractionBudget", false))
{
    const tmp<scalarField> residual = fgmIntegratedResidual(ZEqn);
    scalarField effectiveDiagonal(ZEqn.diag());
    forAll(Z.boundaryField(), patchi)
    {
        const labelUList& cells = Z.boundaryField()[patchi].patch().faceCells();
        forAll(cells, facei)
            effectiveDiagonal[cells[facei]] += ZEqn.internalCoeffs()[patchi][facei];
    }
    const volScalarField continuity(fvc::ddt(rho) + fvc::div(phi));
    const scalarField continuityIntegrated(continuity.primitiveField()*mesh.V());

    // Use a private, unregistered copy with the same name and patch types.
    // Both current and old scalar values are one, including fixed-value BCs.
    // The actual rho/phi, Euler operator and convection scheme are unchanged.
    volScalarField constantZ
    (
        IOobject("Z", runTime.timeName(), mesh, IOobject::NO_READ,
            IOobject::NO_WRITE, false), Z
    );
    const dimensionedScalar one("one", dimless, 1);
    constantZ == one;
    constantZ.oldTime() == one;
    fvScalarMatrix constantEquation
    (
        fvm::ddt(rho, constantZ)
      + mvConvection->fvmDiv(phi, constantZ)
      + thermophysicalTransport->divj(constantZ)
    );
    const tmp<scalarField> constantResidual = fgmIntegratedResidual(constantEquation);
    // This post-solve diffusion witness is separate from the assembled ZEqn
    // residual: corrected schemes can recompute a deferred gradient here.
    tmp<fvScalarMatrix> diffusion(thermophysicalTransport->divj(Z));
    const tmp<scalarField> diffusionResidual = fgmIntegratedResidual(diffusion.ref());

    scalar maxResidualOverDiagonal=0, maxContinuity=0, maxIdentityMismatch=0;
    scalar maxConstantResidual=0, localExcursion=0;
    label worstCell=-1, nonpositiveDiagonal=0;
    forAll(Z, celli)
    {
        if (effectiveDiagonal[celli] > 0)
            maxResidualOverDiagonal=max(maxResidualOverDiagonal,
                mag(residual()[celli])/effectiveDiagonal[celli]);
        else ++nonpositiveDiagonal;
        maxContinuity=max(maxContinuity,mag(continuityIntegrated[celli]));
        maxConstantResidual=max(maxConstantResidual,mag(constantResidual()[celli]));
        maxIdentityMismatch=max(maxIdentityMismatch,
            mag(constantResidual()[celli]+continuityIntegrated[celli]));
        const scalar excursion=max(max(scalar(0),-Z[celli]),max(scalar(0),Z[celli]-1));
        if (excursion > localExcursion) { localExcursion=excursion; worstCell=celli; }
    }
    if (worstCell >= 0)
    {
        std::ostringstream witness;
        witness << std::setprecision(17) << "fgmZCellAudit t=" << runTime.value()
            << " rank=" << Pstream::myProcNo() << " cell=" << worstCell
            << " x=" << mesh.C()[worstCell].x() << " y=" << mesh.C()[worstCell].y()
            << " z=" << mesh.C()[worstCell].z()
            << " Z=" << Z[worstCell] << " oldZ=" << Z.oldTime()[worstCell]
            << " outsideDelta=" << localExcursion
            << " rho=" << rho[worstCell] << " oldRho=" << rho.oldTime()[worstCell]
            << " volume=" << mesh.V()[worstCell]
            << " diagonalKg_s=" << effectiveDiagonal[worstCell]
            << " residualKg_s=" << residual()[worstCell]
            << " continuityKg_s=" << continuityIntegrated[worstCell]
            << " constantResidualKg_s=" << constantResidual()[worstCell]
            << " postSolveDiffusionLhsKg_s=" << -diffusionResidual()[worstCell];
        Pout<< witness.str().c_str() << endl;
    }
    reduce(maxResidualOverDiagonal,maxOp<scalar>());
    reduce(maxContinuity,maxOp<scalar>());
    reduce(maxIdentityMismatch,maxOp<scalar>());
    reduce(maxConstantResidual,maxOp<scalar>());
    reduce(nonpositiveDiagonal,sumOp<label>());
    Info<< "fgmZEquationAudit t=" << runTime.value()
        << " residualL1Kg_s=" << gSum(mag(residual()))
        << " maxResidualOverDiagonal=" << maxResidualOverDiagonal
        << " maxContinuityKg_s=" << maxContinuity
        << " maxConstantResidualKg_s=" << maxConstantResidual
        << " maxConstantIdentityMismatchKg_s=" << maxIdentityMismatch
        << " nonpositiveDiagonal=" << nonpositiveDiagonal
        << " fieldsModified=0" << endl;
}
