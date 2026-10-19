if (flameSpeed.due())
{
    const label oh=composition.species()["OH"];
    const volScalarField& marker=Y[oh];
    // calculate() touches chemistry scratch arrays/RR, but no thermochemical fields.
    // Restore every RR so Qdot/reaction consumers retain the integrated sources.
    basicChemistryModel& chemistry=const_cast<basicChemistryModel&>
    (
        mesh.lookupObject<basicChemistryModel>("chemistryProperties")
    );
    List<scalarField> savedRates(Y.size());
    forAll(Y,k) savedRates[k]=chemistry.RR(k);
    chemistry.calculate();
    scalarField instantaneous(chemistry.RR(oh));
    forAll(Y,k) chemistry.RR(k).field()=savedRates[k];
    volScalarField diffusion
    (
        "diagnosticDiffusion",
        fvc::laplacian(rho*Dimix[oh],marker)
        + fvc::laplacian(rho*Dimix[oh]*marker/Wmix,Wmix)
    );
    forAll(Y,k)
    {
        diffusion-=fvc::laplacian(marker*rho*Dimix[k],Y[k]);
        diffusion-=fvc::laplacian(marker*rho*Dimix[k]*Y[k]/Wmix,Wmix);
    }
    flameSpeed.write("instantaneous_end_step",rho,U,T,p,marker,instantaneous,diffusion);
}
