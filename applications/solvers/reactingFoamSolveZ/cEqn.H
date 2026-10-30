// Transport of the progress variable for a tabulated combustion model.
//
// Only models that declare transportsProgress() reach this file.  The model
// supplies the field it wants transported and the volumetric source in
// kg/(m3 s); this file supplies transport, relaxation and the fvOptions hooks,
// in the same order as the species equations so that a case using tabulated
// chemistry behaves like one using species transport.
//
// Two declared modelling assumptions, neither of them measured:
//
//   * the progress variable is diffused exactly like a species mass fraction,
//     through the same thermophysical transport model (`divj`).  The table
//     carries no progress diffusivity and no Lewis number, so inventing one
//     would be a silent model change;
//   * ZEqn.H has already transported the model's mixture fraction;
//   * the source is added explicitly, as the table gives it, with no density
//     factor and no linearisation in c.  A tabulated Sc(Z, c) is an explicit
//     function of the transported variable; making it implicit would need a
//     derivative the table does not carry.
//
// The model's correct() runs first, so the source assembled below is a lookup
// of this iteration's (Z, c) rather than a value carried in from construction.
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
    reaction->correct();
    tabulatedHeatRelease = reaction->Qdot();

    // Held in a named tmp: the progress source is owned by that tmp until the
    // matrix has consumed it.
    tmp<volScalarField> tProgressSource(reaction->progressSource());
    const scalar tabulatedIntegral = fvc::domainIntegrate(tProgressSource()).value();
    if (!fgmProgressSourceEnabled) tProgressSource.ref() *= scalar(0);
    Info<< "fgmAppliedSource enabled=" << (fgmProgressSourceEnabled ? 1 : 0)
        << " tabulatedKg_s=" << tabulatedIntegral
        << " appliedKg_s=" << fvc::domainIntegrate(tProgressSource()).value() << endl;

    fvScalarMatrix cEqn
    (
        fvm::ddt(rho, c)
      + mvConvection->fvmDiv(phi, c)
      + thermophysicalTransport->divj(c)
     ==
        fvm::Su(tProgressSource(), c)
      + fvOptions(rho, c)
    );

    cEqn.relax();

    fvOptions.constrain(cEqn);

    cEqn.solve();

    fvOptions.correct(c);

    // Refresh composition before thermo inverts the newly solved energy.
    // Keep Q from the same pre-solve state as Sc; do not silently move only
    // the energy source to a different explicit time level.
    reaction->correct();

    Info<< "fgm: progress variable " << c.name()
        << " min/max " << min(c).value() << " " << max(c).value() << endl;
}
