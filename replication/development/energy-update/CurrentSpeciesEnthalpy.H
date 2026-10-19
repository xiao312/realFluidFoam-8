#ifndef CurrentSpeciesEnthalpy_H
#define CurrentSpeciesEnthalpy_H

#include "psiReactionThermo.H"

// Same HE convention as the native species thermodynamics, evaluated at the
// current flow state. Do not read the constructor-only thermo.hei() cache.
inline Foam::tmp<Foam::volScalarField> currentSpeciesEnthalpy
(
    const Foam::psiReactionThermo& thermo,
    const Foam::label species
)
{
    return thermo.composition().HE(species, thermo.p(), thermo.T());
}

#endif
