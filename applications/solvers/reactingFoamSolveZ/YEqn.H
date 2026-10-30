tmp<fv::convectionScheme<scalar>> mvConvection
(
    fv::convectionScheme<scalar>::New
    (
        mesh,
        fields,
        phi,
        mesh.divScheme("div(phi,Yi_h)")
    )
);

// A tabulated model prescribes the composition, so the species must not also be
// solved: doing both would mix a transported mixture with a tabulated one.  The
// guard is the model's own property, so a case cannot forget it, and every model
// that reacts the species directly reports false and takes exactly the path it
// took before this guard existed.
if (!reaction->compositionTabulated())
{
    const auto fgmReactionStart = fgmTiming.start();
    reaction->correct();
    fgmTiming.stop(fgmWallTiming::reactionCorrection, fgmReactionStart);
    volScalarField Yt(0.0*Y[0]);

    forAll(Y, i)
    {
        if (i != inertIndex && composition.active(i))
        {
            volScalarField& Yi = Y[i];

            fvScalarMatrix YiEqn
            (
                fvm::ddt(rho, Yi)
              + mvConvection->fvmDiv(phi, Yi)
              + thermophysicalTransport->divj(Yi)
             ==
                reaction->R(Yi)
              + fvOptions(rho, Yi)
            );

            YiEqn.relax();

            fvOptions.constrain(YiEqn);

            YiEqn.solve("Yi");

            fvOptions.correct(Yi);

            Yi.max(0.0);
            Yt += Yi;
        }
    }

    Y[inertIndex] = scalar(1) - Yt;
    Y[inertIndex].max(0.0);
}
else
{
    // The model fills the composition itself and the table has already been
    // refused if its species do not sum to one within the contract limit, so
    // the solver performs no further bookkeeping: the inert species is not
    // overwritten here, because that would be a second, silent repair of a
    // quantity the model owns.
    // Progress models retain their established pre-Z/source lifecycle.
    // Non-progress steady tables refresh after Z in the main loop instead.
    if (reaction->transportsProgress())
    {
        const auto fgmReactionStart = fgmTiming.start();
        reaction->correct();
        fgmTiming.stop(fgmWallTiming::reactionCorrection, fgmReactionStart);
    }

    volScalarField Ysum(0.0*Y[0]);
    forAll(Y, i)
    {
        Ysum += Y[i];
    }

    Info<< "YEqn: tabulated composition from " << reaction->type()
        << ", species equations skipped; sum(Y) min/max "
        << min(Ysum).value() << " " << max(Ysum).value() << endl;
}
