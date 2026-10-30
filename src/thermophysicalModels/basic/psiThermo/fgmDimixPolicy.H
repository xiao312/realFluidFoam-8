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

// An explicit development closure, not a blanket permission for turbulent
// transport. This exact model uses alphaEff for both Ha and Z, never Dimix.
inline bool validateFgmRansUnityLeDiagnostic
(
    const fvMesh& mesh, const dictionary& momentum,
    const dictionary& transport, const word& combustionType
)
{
    if (!mesh.time().controlDict().lookupOrDefault<Switch>
        ("fgmRansUnityLeDiagnostic", false)) return false;
    if
    (
        combustionType != "steadyFlamelet"
     || momentum.lookupOrDefault<word>("simulationType", "") != "RAS"
     || !momentum.found("RAS")
     || momentum.subDict("RAS").lookupOrDefault<word>("model", "") != "kEpsilon"
     || !momentum.subDict("RAS").lookupOrDefault<Switch>("turbulence", false)
     || !transport.found("RAS")
     || transport.subDict("RAS").lookupOrDefault<word>("model", "") != "eddyDiffusivity"
     || transport.subDict("RAS").optionalSubDict("eddyDiffusivityCoeffs")
            .lookupOrDefault<scalar>("Prt", -1) != scalar(0.7)
    )
    {
        FatalErrorInFunction
            << "fgmRansUnityLeDiagnostic requires steadyFlamelet, RAS kEpsilon "
            << "with turbulence on, and RAS eddyDiffusivity Prt 0.7"
            << exit(FatalError);
    }
    return true;
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
    const bool laminarFourier =
        momentum.lookupOrDefault<word>("simulationType", "") == "laminar"
     && transport.found("laminar")
     && transport.subDict("laminar").lookupOrDefault<word>("model", "") == "Fourier";
    const bool ransUnityLe = validateFgmRansUnityLeDiagnostic
        (mesh, momentum, transport, combustionType);
    if
    (
        !(laminarFourier || ransUnityLe)
     || (combustionType != "fgmTable" && combustionType != "steadyFlamelet")
     || !thermodynamics.found("thermoType")
     || thermodynamics.subDict("thermoType").lookupOrDefault<word>("type", "") != "hePsiThermo"
    )
    {
        FatalErrorInFunction
            << "fgmSkipUnusedDimix requires the explicit laminar/Fourier path "
            << "or the declared RAS kEpsilon/unity-Le diagnostic, hePsiThermo "
            << "and a supported tabulated combustion model"
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
