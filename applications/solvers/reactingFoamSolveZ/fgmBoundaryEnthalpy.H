#ifndef fgmBoundaryEnthalpy_H
#define fgmBoundaryEnthalpy_H

#include "fixedValueFvPatchFields.H"

// Fixed temperature prescribes enthalpy through the current EOS, composition
// and pressure. Only boundary faces are evaluated: avoid a second full-volume
// thermodynamic calculation in a large tabulated-chemistry case.
inline void updateFgmFixedTemperatureEnthalpy
(
    Foam::psiReactionThermo& thermo,
    const Foam::basicSpecieMixture& composition,
    Foam::volScalarField& Ha
)
{
    thermo.T().correctBoundaryConditions();
    forAll(thermo.T().boundaryField(), patchi)
    {
        const Foam::fvPatchScalarField& temperature = thermo.T().boundaryField()[patchi];
        // Mixed/inletOutlet patches also report fixesValue(); their outflow
        // fraction is not a prescribed temperature and must not be overridden.
        if (!Foam::isA<Foam::fixedValueFvPatchScalarField>(temperature)) continue;
        Foam::fvPatchScalarField& energy = Ha.boundaryFieldRef()[patchi];
        if (!Foam::isA<Foam::fixedValueFvPatchScalarField>(energy))
        {
            FatalErrorInFunction
                << "Fixed-temperature patch " << temperature.patch().name()
                << " requires a fixed-value Ha boundary; found " << energy.type()
                << Foam::exit(Foam::FatalError);
        }
        // OF8 he(Tpatch,patchi) uses the thermo's current pressure patch and
        // current patchFaceMixture. sensibleEnthalpy is required by the mode.
        const Foam::tmp<Foam::scalarField> sensible(thermo.he(temperature, patchi));
        Foam::scalarField absolute(sensible());
        forAll(composition.Y(), i)
        {
            absolute += composition.Hf(i)*composition.Y()[i].boundaryField()[patchi];
        }
        energy == absolute;
        // Keep the stored sensible boundary consistent too; no cell change.
        thermo.he().boundaryFieldRef()[patchi] == sensible();
    }
}

#endif
