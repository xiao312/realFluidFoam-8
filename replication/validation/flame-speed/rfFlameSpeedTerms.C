// SPDX-License-Identifier: GPL-3.0-or-later
// Read-only constitutive evaluation; see README for the splitting distinction.
#include "fvCFD.H"
#include "psiReactionThermo.H"
#include "BasicChemistryModel.H"
#include "timeSelector.H"
#include <fstream>
#include <iomanip>

int main(int argc, char *argv[])
{
    argList::noParallel();
    timeSelector::addOptions();
    #include "setRootCase.H"
    #include "createTime.H"
    const instantList times(timeSelector::select0(runTime, args));
    forAll(times, timei)
    {
        runTime.setTime(times[timei], timei);
        #include "createMesh.H"
        autoPtr<psiReactionThermo> thermop(psiReactionThermo::New(mesh));
        psiReactionThermo& thermo = thermop();
        autoPtr<BasicChemistryModel<psiReactionThermo>> chemistry
        (
            BasicChemistryModel<psiReactionThermo>::New(thermo)
        );
        if (!chemistry->chemistry())
        {
            FatalErrorInFunction << "Chemistry disabled" << exit(FatalError);
        }
        const basicSpecieMixture& mixture = thermo.composition();
        const PtrList<volScalarField>& Y = mixture.Y();
        const label oh = mixture.species()["OH"];
        const label fuel = mixture.species()["CH4"];
        volScalarField rho("diagnosticRho", thermo.rho());
        volScalarField Wmix("Wmix", thermo.W());
        volScalarField savedRho
        (
            IOobject("rho", runTime.timeName(), mesh, IOobject::MUST_READ,
                     IOobject::NO_WRITE), mesh
        );
        volVectorField U
        (
            IOobject("U", runTime.timeName(), mesh, IOobject::MUST_READ,
                     IOobject::NO_WRITE), mesh
        );
        PtrList<volScalarField> diffusivity(Y.size());
        forAll(Y, k)
        {
            diffusivity.set(k, new volScalarField
            (
                "Dimix_" + mixture.species()[k], thermo.Dimix(k)
            ));
        }
        chemistry->calculate();
        const volScalarField& marker = Y[oh];
        volScalarField ordinary
        (
            "ordinary", fvc::laplacian(rho*diffusivity[oh], marker)
        );
        volScalarField molecularWeight
        (
            "molecularWeight",
            fvc::laplacian(rho*diffusivity[oh]*marker/Wmix, Wmix)
        );
        volScalarField correction1("correction1", 0.0*ordinary);
        volScalarField correction2("correction2", 0.0*ordinary);
        forAll(Y, k)
        {
            correction1 += fvc::laplacian(marker*rho*diffusivity[k], Y[k]);
            correction2 += fvc::laplacian
            (
                marker*rho*diffusivity[k]*Y[k]/Wmix, Wmix
            );
        }
        volVectorField gradient("gradientOH", fvc::grad(marker));
        const fileName output(mesh.time().path()/
            ("eq40-" + runTime.timeName() + ".csv"));
        if (isFile(output))
        {
            FatalErrorInFunction << "Refusing overwrite: " << output
                                << exit(FatalError);
        }
        std::ofstream stream(output.c_str());
        stream << std::setprecision(17)
            << "x,y,z,volume,T,p,rho,rhoSaved,Ux,YOH,gradOHx,magGradOH,"
            << "omegaOH,ordinaryDiffusion,molecularWeightDiffusion,"
            << "correction1,correction2,minusDivJOH,omegaCH4\n";
        forAll(marker, celli)
        {
            const vector& x = mesh.C()[celli];
            const scalar diffusion = ordinary[celli] + molecularWeight[celli]
                - correction1[celli] - correction2[celli];
            stream << x.x() << ',' << x.y() << ',' << x.z() << ','
                << mesh.V()[celli] << ',' << thermo.T()[celli] << ','
                << thermo.p()[celli] << ',' << rho[celli] << ','
                << savedRho[celli] << ',' << U[celli].x() << ',' << marker[celli]
                << ',' << gradient[celli].x() << ',' << mag(gradient[celli])
                << ',' << chemistry->RR(oh)[celli] << ',' << ordinary[celli]
                << ',' << molecularWeight[celli] << ',' << correction1[celli]
                << ',' << correction2[celli] << ',' << diffusion << ','
                << chemistry->RR(fuel)[celli] << '\n';
        }
        stream.close();
        if (!stream) FatalErrorInFunction << "CSV write failed" << exit(FatalError);
        Info << "Wrote " << output << nl;
    }
    Info << "End" << endl;
    return 0;
}
