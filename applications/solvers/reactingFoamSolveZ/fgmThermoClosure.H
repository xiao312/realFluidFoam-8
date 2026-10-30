#ifndef fgmThermoClosure_H
#define fgmThermoClosure_H
#include <cmath>

// Audit the executing library immediately after inversion, before pressure is
// changed by a later equation. Never reconstruct h from a separate polynomial.
inline void auditFgmThermoClosure(const Foam::psiReactionThermo& thermo)
{
    using namespace Foam;
    const Time& time = thermo.T().mesh().time();
    if (!time.controlDict().lookupOrDefault<Switch>("writeFgmThermoClosure", false)) return;
    const bool writeSummary = time.value() == 0 || time.writeTime();
    if (thermo.he().name() != "h")
        FatalErrorInFunction << "FGM caloric audit currently requires sensible enthalpy" << exit(FatalError);
    const scalar limit = time.controlDict().lookupOrDefault<scalar>("fgmThermoClosureRelativeLimit", 1e-8);
    if (!(limit > 0) || !std::isfinite(limit))
        FatalErrorInFunction << "Invalid explicit caloric closure limit" << exit(FatalError);
    const tmp<volScalarField> evaluated = thermo.he(thermo.p(), thermo.T());
    const tmp<volScalarField> heatCapacity = thermo.Cp();
    scalar maxAbsolute = 0, maxRelative = 0, squareSum = 0;
    scalar boundaryMaxAbsolute = 0, boundaryMaxRelative = 0;
    label cells = 0, faces = 0, invalid = 0;
    forAll(thermo.he(), celli)
    {
        const scalar actual = evaluated()[celli], stored = thermo.he()[celli];
        const scalar cpT = heatCapacity()[celli]*thermo.T()[celli];
        if (!std::isfinite(actual) || !std::isfinite(stored) || !(cpT > 0) || !std::isfinite(cpT)) { ++invalid; continue; }
        const scalar error = mag(actual-stored);
        const scalar scale = max(scalar(1), max(mag(actual), max(mag(stored), mag(cpT))));
        maxAbsolute = max(maxAbsolute, error);
        maxRelative = max(maxRelative, error/scale);
        squareSum += sqr(error);
        ++cells;
    }
    forAll(thermo.he().boundaryField(), patchi)
    {
        const fvPatchScalarField& stored = thermo.he().boundaryField()[patchi];
        forAll(stored, facei)
        {
            const scalar actual = evaluated().boundaryField()[patchi][facei];
            const scalar cpT = heatCapacity().boundaryField()[patchi][facei]*thermo.T().boundaryField()[patchi][facei];
            if (!std::isfinite(actual) || !std::isfinite(stored[facei]) || !(cpT > 0) || !std::isfinite(cpT)) { ++invalid; continue; }
            const scalar error = mag(actual-stored[facei]);
            const scalar scale = max(scalar(1), max(mag(actual), max(mag(stored[facei]), mag(cpT))));
            boundaryMaxAbsolute = max(boundaryMaxAbsolute, error);
            boundaryMaxRelative = max(boundaryMaxRelative, error/scale);
            ++faces;
        }
    }
    reduce(maxAbsolute, maxOp<scalar>()); reduce(maxRelative, maxOp<scalar>());
    reduce(boundaryMaxAbsolute, maxOp<scalar>()); reduce(boundaryMaxRelative, maxOp<scalar>());
    reduce(squareSum, sumOp<scalar>()); reduce(cells, sumOp<label>());
    reduce(faces, sumOp<label>()); reduce(invalid, sumOp<label>());
    const bool failed = invalid || !cells || maxRelative > limit || boundaryMaxRelative > limit;
    // Checking and summary frequency are deliberately separate. Always report
    // a failure, including one on a timestep which does not write fields.
    if (writeSummary || failed)
    {
        Info<< "thermoClosure t=" << time.value() << " initial=" << (time.value() == 0 ? 1 : 0)
            << " afterInversion=" << 1
            << " cells=" << cells << " boundaryFaces=" << faces << " invalid=" << invalid
            << " maxAbs_J_kg=" << maxAbsolute << " rms_J_kg=" << std::sqrt(squareSum/max(label(1), cells))
            << " maxRelative=" << maxRelative << " boundaryMaxAbs_J_kg=" << boundaryMaxAbsolute
            << " boundaryMaxRelative=" << boundaryMaxRelative << " limit=" << limit << endl;
    }
    if (failed)
        FatalErrorInFunction << "Stored h is inconsistent with executing h(p,T,Y); see thermoClosure"
            << exit(FatalError);
}
#endif
