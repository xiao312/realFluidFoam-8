#ifndef fgmDimixPolicy_H
#define fgmDimixPolicy_H

#include "fvMesh.H"
#include "Time.H"
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

// Called once before the first calculation. Runtime modification is prohibited.
// Subsequent corrections read only the existing in-memory control flag. Do not
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
    const IOdictionary thermodynamics
    (
        IOobject("thermophysicalProperties", mesh.time().constant(), mesh,
            IOobject::MUST_READ, IOobject::NO_WRITE, false)
    );
    const word combustionType = combustion.lookupOrDefault<word>("combustionModel", "");
    if
    (
        momentum.lookupOrDefault<word>("simulationType", "") != "laminar"
     || !transport.found("laminar")
     || transport.subDict("laminar").lookupOrDefault<word>("model", "") != "Fourier"
     || (combustionType != "fgmTable" && combustionType != "steadyFlamelet")
     || !thermodynamics.found("thermoType")
     || thermodynamics.subDict("thermoType").lookupOrDefault<word>("type", "") != "hePsiThermo"
    )
    {
        FatalErrorInFunction
            << "fgmSkipUnusedDimix requires explicit laminar momentum, "
            << "Fourier transport, hePsiThermo and fgmTable or steadyFlamelet combustion"
            << exit(FatalError);
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
