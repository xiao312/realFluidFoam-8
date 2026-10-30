const word fgmSourceIntegration
(
    runTime.controlDict().lookupOrDefault<word>("fgmSourceIntegration", "explicit")
);
const bool splitFgmSource = fgmSourceIntegration == "strangFixedState";
if (!splitFgmSource && fgmSourceIntegration != "explicit")
    FatalErrorInFunction << "Unknown fgmSourceIntegration " << fgmSourceIntegration << exit(FatalError);

combustionModels::fgmTable<psiReactionThermo>* fgmSourceModel = nullptr;
autoPtr<volScalarField> fgmFirstHalfRate;
scalarField fgmSourceOldC, fgmSourceOldZ, fgmSourceOldRho;
label fgmSourceTimeIndex = -1, fgmSourceOuterCount = 0;
if (splitFgmSource)
{
    if (!absoluteEnthalpyFGM || !fgmProgressSourceEnabled || LTS)
        FatalErrorInFunction << "strangFixedState requires absolute Ha, enabled source and global time stepping"
            << exit(FatalError);
    fgmSourceModel = dynamic_cast<combustionModels::fgmTable<psiReactionThermo>*>(&reaction());
    if (!fgmSourceModel || !fgmSourceModel->sourceIntegrationSupported())
        FatalErrorInFunction << "strangFixedState requires fgmTable with v2 raw C" << exit(FatalError);
    const word progressDdt
    (
        mesh.ddtScheme("ddt(" + rho.name() + ',' + reaction->progressVariable()->name() + ')')
    );
    if (progressDdt != "Euler")
        FatalErrorInFunction << "strangFixedState requires Euler progress transport; found "
            << progressDdt << exit(FatalError);
    fgmFirstHalfRate.reset
    (
        new volScalarField
        (
            IOobject("fgmFirstHalfRate", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
            mesh, dimensionedScalar("zero", dimMass/dimVolume/dimTime, 0)
        )
    );
}
Info<< "FGM source integration: " << fgmSourceIntegration << endl;
