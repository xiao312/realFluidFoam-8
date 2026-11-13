// Exactly once after runTime++ and before rhoEqn/PIMPLE. Never assign oldTime().
if (splitFgmSource)
{
    const auto fgmFirstSourceStart = fgmTiming.start();
    if (mesh.moving())
        FatalErrorInFunction << "strangFixedState currently requires a stationary mesh" << exit(FatalError);
    if (fgmSourceTimeIndex == runTime.timeIndex())
        FatalErrorInFunction << "Repeated first source stage in one physical timestep" << exit(FatalError);
    fgmSourceTimeIndex = runTime.timeIndex();
    fgmSourceOuterCount = 0;
    volScalarField& sourceC = *reaction->progressVariable();
    const volScalarField& sourceZ = fgmSourceModel->Z();
    // Access oldTime before changing c; this triggers OF8's lazy history storage.
    fgmSourceOldC = sourceC.oldTime().primitiveField();
    fgmSourceOldZ = sourceZ.oldTime().primitiveField();
    fgmSourceOldRho = rho.oldTime().primitiveField();
    const scalarField firstHalf = fgmColdFlowActive ? fgmSourceOldC : fgmSourceModel->advanceProgressSource
    (
        fgmSourceOldZ, fgmSourceOldRho, fgmSourceOldC,
        0.5*runTime.deltaTValue(), "firstHalf"
    );
    fgmFirstHalfRate().primitiveFieldRef() =
        fgmSourceOldRho*(firstHalf-fgmSourceOldC)/runTime.deltaTValue();
    sourceC.primitiveFieldRef() = firstHalf;
    sourceC.correctBoundaryConditions();
    fgmTiming.stop(fgmWallTiming::sourceFirstHalf, fgmFirstSourceStart);
}
