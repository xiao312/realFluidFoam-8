// Transport of the mixture fraction Z for a tabulated combustion model.
//
// This file exists because of a measured finding: the base reactingFoam path has
// no Z equation, and fgmTable constructs `Z_` with MUST_READ and never assigns
// it, so every number this lane produced before this file sat at one prescribed
// mixture fraction (0.5 in the G2 case).  Here the solver solves that exact field
// and the model then reads what the equation wrote.
//
// Why the field is taken from the mesh registry and not from an accessor:
//
//   * `fgmTable` constructs its private `volScalarField Z_` from an IOobject on
//     this mesh (fgmTable.C:209-221), so the registry entry named in
//     `fgmTableCoeffs.mixtureFractionField` IS `Z_`, not a copy;
//   * `lookupObjectRef` returns a reference to that registered object, so
//     solving it writes the model's own storage in place;
//   * the model prints `cells ... Z[min,max] ...` on every correct(), and those
//     printed bounds are the model's own view of `Z_`.  A run in which they
//     change from 0.5 to [0,1] therefore demonstrates, by the model's own
//     output, that the table reads the transported field.  That is a
//     measurement, not a pointer-identity argument.
//
// Declared modelling assumptions, neither of them measured:
//
//   * Z is diffused through the same `divj` transport the species and the
//     progress variable use, i.e. as a species mass fraction.  The table carries
//     no Z diffusivity and no Lewis number, so inventing a separate one would be
//     a silent model change.  The consequence is that Z is conserved only up to
//     that diffusion model, which is declared, not measured;
//   * the equation has no source and no chemistry coupling of its own: a
//     mixture fraction with a source would not be a mixture fraction;
//   * the boundary values are the case's, not this file's.  The inlets must
//     carry the two stream values (1 for the pure-fuel stream and 0 for the
//     oxidiser stream); otherwise the run is a prescribed profile wearing a
//     transport equation, which is exactly what this variant exists to stop.
#include "fvmSup.H"

{
    // The field name the model was told to read.  `CombustionModel` exposes no
    // dictionary accessor, so the name is literal here and the agreement is
    // enforced the other way round: the case's
    // `fgmTableCoeffs.mixtureFractionField` is `Z` (pinned in the run manifest),
    // and if a case named a different field then this literal lookup would find
    // no registered `Z` and stop below rather than transport a different field
    // from the one being tabulated.
    const word ZName("Z");

    if (!mesh.foundObject<volScalarField>(ZName))
    {
        FatalErrorInFunction
            << "no field " << ZName << " is registered on the mesh.  The "
            << "combustion model " << reaction->type()
            << " must have constructed it, and a model that prescribes the "
            << "mixture fraction does not permit this solver variant"
            << exit(FatalError);
    }

    volScalarField& Z = mesh.lookupObjectRef<volScalarField>(ZName);

    fvScalarMatrix ZEqn
    (
        fvm::ddt(rho, Z)
      + mvConvection->fvmDiv(phi, Z)
      + thermophysicalTransport->divj(Z)
     ==
        fvOptions(rho, Z)
    );

    ZEqn.relax();

    fvOptions.constrain(ZEqn);

    ZEqn.solve();

    fvOptions.correct(Z);

    // Subtract the endpoint before formatting so even a few-ulp violation is
    // visible independently of the stream's general precision.
    Info<< "fgmZEndpoint t=" << runTime.value()
        << " belowZero=" << max(scalar(0), -min(Z).value())
        << " aboveOne=" << max(scalar(0), max(Z).value()-scalar(1))
        << " transportedZModified=0" << endl;
    Info<< "fgmZ: transported mixture fraction " << Z.name()
        << " min/max " << min(Z).value() << " " << max(Z).value()
        << " (the table reports its own Z bounds on the next correct())" << endl;
}
