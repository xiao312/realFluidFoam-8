// Chemical part of mixture enthalpy from the executing thermo package.
// Hf is J/kg of species. No table or external gas constant is used here.
inline Foam::tmp<Foam::volScalarField> fgmChemicalEnthalpy
(
    const Foam::fvMesh& mesh,
    const Foam::basicSpecieMixture& composition
)
{
    Foam::tmp<Foam::volScalarField> result = Foam::volScalarField::New
    (
        "fgmChemicalEnthalpy", mesh,
        Foam::dimensionedScalar(Foam::dimEnergy/Foam::dimMass, 0)
    );
    const Foam::PtrList<Foam::volScalarField>& species = composition.Y();
    forAll(species, i)
    {
        result.ref() += Foam::dimensionedScalar
        (
            "Hf", Foam::dimEnergy/Foam::dimMass, composition.Hf(i)
        )*species[i];
    }
    return result;
}
