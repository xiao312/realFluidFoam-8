#ifndef fgmContinuityStage_H
#define fgmContinuityStage_H

// Read-only, stage-labelled cell-integrated continuity witness. This is not
// the EOS-versus-transport-density discrepancy printed by the stock header.
inline void auditFgmContinuityStage
(
    const Foam::word& stage,
    const Foam::volScalarField& rho,
    const Foam::surfaceScalarField& phi
)
{
    using namespace Foam;
    if (!rho.time().controlDict().lookupOrDefault<Switch>
        ("writeMixtureFractionBudget", false)) return;
    const volScalarField continuity(fvc::ddt(rho) + fvc::div(phi));
    const scalarField integrated(continuity.primitiveField()*rho.mesh().V());
    std::ostringstream record;
    record << std::setprecision(17)
        << "fgmContinuityStage t=" << rho.time().value()
        << " stage=" << stage.c_str()
        << " maxContinuityKg_s=" << gMax(mag(integrated))
        << " sumContinuityKg_s=" << gSum(integrated)
        << " massKg=" << gSum(rho.primitiveField()*rho.mesh().V())
        << " fieldsModified=0";
    Info<< record.str().c_str() << endl;
}

#endif
