// Optional fixed-mesh, source-free Euler predictor admissibility bound.
// Included after setDeltaT and before runTime++. No field assignment occurs.
if (runTime.controlDict().lookupOrDefault<Switch>("limitDensityPredictorTimeStep", false))
{
    const word densityDdt(mesh.ddtScheme("ddt(" + rho.name() + ')'));
    if (LTS || !runTime.controlDict().lookupOrDefault<Switch>("adjustTimeStep", false)
        || densityDdt != "Euler" || mesh.moving()
        || static_cast<const fv::optionList&>(fvOptions).size() != 0)
        FatalErrorInFunction
            << "Density predictor step bound requires adaptive global Euler, fixed mesh"
            << " and empty fvOptions; no unaccounted mass sources"
            << exit(FatalError);

    const scalar proposed = runTime.deltaTValue();
    const scalar margin = 0.9;
    const tmp<volScalarField> divergence = fvc::div(phi);
    scalar bound = GREAT, proposedMaxLoss = -GREAT;
    label invalid = 0, proposedNonpositive = 0;
    forAll(rho, celli)
    {
        const scalar density = rho[celli], loss = divergence()[celli];
        if (!std::isfinite(density) || density <= 0 || !std::isfinite(loss))
        {
            ++invalid;
            continue;
        }
        const scalar fraction = proposed*loss/density;
        proposedMaxLoss = max(proposedMaxLoss, fraction);
        if (fraction >= 1) ++proposedNonpositive;
        if (loss > 0) bound = min(bound, margin*density/loss);
    }
    reduce(invalid, sumOp<label>());
    reduce(proposedNonpositive, sumOp<label>());
    reduce(bound, minOp<scalar>());
    reduce(proposedMaxLoss, maxOp<scalar>());
    if (invalid || !std::isfinite(proposed) || proposed <= 0)
        FatalErrorInFunction << "Nonfinite/nonpositive accepted rho or invalid predictor input"
            << "; no field repair performed" << exit(FatalError);
    const scalar selected = min(proposed, bound);
    if (!std::isfinite(selected) || selected <= 0)
        FatalErrorInFunction << "No positive admissible predictor timestep" << exit(FatalError);
    if (selected < proposed) runTime.setDeltaT(selected);
    Info<< "densityPredictorTimeStep t=" << runTime.value()
        << " proposedDeltaT=" << proposed << " selectedDeltaT=" << selected
        << " maxProposedMassLossFraction=" << proposedMaxLoss
        << " maxSelectedMassLossFraction=" << proposedMaxLoss*selected/proposed
        << " proposedNonpositiveCells=" << proposedNonpositive
        << " margin=" << margin << " fieldsModified=0"
        << " dtModified=" << label(selected < proposed) << endl;
}
