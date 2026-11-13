// Transport of the progress variable for a tabulated combustion model.
//
// Only models that declare transportsProgress() reach this file.  The model
// supplies the field it wants transported and the volumetric source in
// kg/(m3 s); this file supplies transport, relaxation and the fvOptions hooks,
// in the same order as the species equations so that a case using tabulated
// chemistry behaves like one using species transport.
//
// Declared modelling assumptions, not validation results:
//
//   * the progress variable is diffused exactly like a species mass fraction,
//     through the same thermophysical transport model (`divj`).  The table
//     carries no progress diffusivity and no Lewis number, so inventing one
//     would be a silent model change;
//   * ZEqn.H has already transported the model's mixture fraction;
//   * the default source is explicit, as the table gives it. The opt-in
//     strangFixedState mode integrates the piecewise-linear table source in
//     two frozen-Z/rho stages; its first-stage offset enters this Euler matrix.
//
// In explicit mode correct() refreshes the source before assembly. Split mode
// defers its second source lookup until both Z and c have been transported.
//
// The field must remain inside the tabulated box.  That is not enforced here:
// the model does it, refusing at lookup under boundsPolicy error.
//
// The source enters as fvm::Su(field, c), which is the explicitly-sourced form
// of a volScalarField; added as a bare field it would need an operator that
// does not exist between a GeometricField and an fvMatrix.
#include "fvmSup.H"

{
    volScalarField* cPtr = reaction->progressVariable();

    if (cPtr == nullptr)
    {
        FatalErrorInFunction
            << "combustion model " << reaction->type()
            << " declares transportsProgress() but supplies no progress field"
            << exit(FatalError);
    }

    volScalarField& c = *cPtr;

    // Look the table up at the current (Z, c) before assembling the source.
    // The species equations are skipped for a tabulated model (see YEqn.H), so
    // without this line correct() would run exactly once, in the constructor,
    // and every later step would apply a source frozen at the initial c.  A
    // field written by a solve in which the table was consulted needs the
    // lookup inside the loop, not only at construction.
    // Split transport does not need a source lookup at new Z with untransported C.
    // Its source curve is sampled only after the joint transport state is available.
    if (!splitFgmSource)
    {
        const auto fgmReactionStart = fgmTiming.start();
        reaction->correct();
        fgmTiming.stop(fgmWallTiming::reactionCorrection, fgmReactionStart);
    }
    tabulatedHeatRelease = reaction->Qdot();

    // Held in a named tmp: the progress source is owned by that tmp until the
    // matrix has consumed it.
    tmp<volScalarField> tProgressSource(reaction->progressSource());
    const scalar tabulatedIntegral = fvc::domainIntegrate(tProgressSource()).value();
    if (!fgmProgressSourceEnabled || fgmColdFlowActive) tProgressSource.ref() *= scalar(0);
    if (splitFgmSource)
    {
        if (fgmSourceTimeIndex != runTime.timeIndex())
            FatalErrorInFunction << "Missing first source stage" << exit(FatalError);
        const scalar oldCChange = gMax(mag(c.oldTime().primitiveField()-fgmSourceOldC));
        const scalar oldZChange = gMax(mag(fgmSourceModel->Z().oldTime().primitiveField()-fgmSourceOldZ));
        const scalar oldRhoChange = gMax(mag(rho.oldTime().primitiveField()-fgmSourceOldRho));
        if (oldCChange != 0 || oldZChange != 0 || oldRhoChange != 0)
            FatalErrorInFunction << "Source splitting oldTime state changed" << exit(FatalError);
        Info<< "fgmSourceOldTime t=" << runTime.value() << " outer=" << ++fgmSourceOuterCount
            << " deltaC=" << oldCChange << " deltaZ=" << oldZChange
            << " deltaRho=" << oldRhoChange << endl;
        // Euler transport starts from rho_old*C_half while history stays C_old.
        tProgressSource.ref() == fgmFirstHalfRate();
    }
    Info<< "fgmAppliedSource enabled=" << (fgmProgressSourceEnabled ? 1 : 0)
        << " tabulatedKg_s=" << tabulatedIntegral
        << " appliedKg_s=" << fvc::domainIntegrate(tProgressSource()).value()
        << " integration=" << fgmSourceIntegration << endl;

    fvScalarMatrix cEqn
    (
        fvm::ddt(rho, c)
      + mvConvection->fvmDiv(phi, c)
      + thermophysicalTransport->divj(c)
     ==
        fvm::Su(tProgressSource(), c)
      + fvOptions(rho, c)
    );

    // Under-relaxation would reintroduce the previous outer iteration's reacted C.
    if (!splitFgmSource) cEqn.relax();

    fvOptions.constrain(cEqn);

    cEqn.solve();

    fvOptions.correct(c);

    if (splitFgmSource)
    {
        // Recomputed from this transport solution; never advance the last outer's result.
        const auto fgmSecondSourceStart = fgmTiming.start();
        const scalarField transportedC(c.primitiveField());
        c.primitiveFieldRef() = fgmColdFlowActive ? transportedC : fgmSourceModel->advanceProgressSource
        (
            fgmSourceModel->Z().primitiveField(), rho.primitiveField(), transportedC,
            0.5*runTime.deltaTValue(), "secondHalf"
        );
        c.correctBoundaryConditions();
        fgmTiming.stop(fgmWallTiming::sourceSecondHalf, fgmSecondSourceStart);
    }

    // Refresh composition before thermo inverts the newly solved energy.
    // Explicit mode retains its pre-solve Q time level. Split mode requires
    // absolute Ha: Q is diagnostic only; composition changes carry formation
    // energy through the unchanged absolute-energy equation.
    const auto fgmReactionStart = fgmTiming.start();
    reaction->correct();
    fgmTiming.stop(fgmWallTiming::reactionCorrection, fgmReactionStart);

    Info<< "fgm: progress variable " << c.name()
        << " min/max " << min(c).value() << " " << max(c).value() << endl;
}
