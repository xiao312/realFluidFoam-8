#ifndef fgmDimixPolicy_H
#define fgmDimixPolicy_H

#include "fvMesh.H"
#include "IOdictionary.H"
#include "Switch.H"

namespace Foam
{

inline bool fgmDimixSuppressed(const fvMesh& mesh)
{
    return mesh.time().controlDict().lookupOrDefault<Switch>
    (
        "fgmSkipUnusedDimix", false
    );
}

// Called before the first calculation and every subsequent correction. Do not
// infer Fourier from an absent dictionary: this optimization needs an explicit
// selection, and its public Dimix accessors remain guarded independently.
inline bool validateFgmDimixSuppression(const fvMesh& mesh)
{
    if (!fgmDimixSuppressed(mesh)) return false;
    const dictionary& control = mesh.time().controlDict();
    if
    (
        control.lookupOrDefault<Switch>("runTimeModifiable", true)
     || control.lookupOrDefault<word>("fgmEnergyForm", "") != "absoluteEnthalpy"
    )
    {
        FatalErrorInFunction
            << "fgmSkipUnusedDimix requires absoluteEnthalpy and "
            << "runTimeModifiable no" << exit(FatalError);
    }

    const IOdictionary momentum
    (
        IOobject("momentumTransport", mesh.time().constant(), mesh,
            IOobject::MUST_READ, IOobject::NO_WRITE, false)
    );
    const IOdictionary transport
    (
        IOobject("thermophysicalTransport", mesh.time().constant(), mesh,
            IOobject::MUST_READ, IOobject::NO_WRITE, false)
    );
    const IOdictionary combustion
    (
        IOobject("combustionProperties", mesh.time().constant(), mesh,
            IOobject::MUST_READ, IOobject::NO_WRITE, false)
    );
    if
    (
        momentum.lookupOrDefault<word>("simulationType", "") != "laminar"
     || !transport.found("laminar")
     || transport.subDict("laminar").lookupOrDefault<word>("model", "") != "Fourier"
     || combustion.lookupOrDefault<word>("combustionModel", "") != "fgmTable"
    )
    {
        FatalErrorInFunction
            << "fgmSkipUnusedDimix requires explicit laminar momentum, "
            << "Fourier transport and fgmTable combustion" << exit(FatalError);
    }
    return true;
}

inline void requireCalculatedDimix(const fvMesh& mesh)
{
    if (fgmDimixSuppressed(mesh))
    {
        FatalErrorInFunction
            << "Dimix was requested while fgmSkipUnusedDimix is enabled. "
            << "This caller is outside the qualified Fourier/unity-Le path; "
            << "disable the optimization and restart from time zero."
            << exit(FatalError);
    }
}

}
#endif
