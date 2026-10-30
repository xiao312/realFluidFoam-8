// Runtime factory and inversion pattern adapted from rfPropertyProbe.C.
// No EOS or caloric correlation is implemented in this diagnostic.
#include "fvCFD.H"
#include "psiReactionThermo.H"
#include "mixedFvPatchFields.H"
#include "../../../../applications/solvers/reactingFoamSolveZ/fgmBoundaryEnthalpy.H"
#include <fstream>
#include <iomanip>
#include <cmath>

int main(int argc, char *argv[])
{
    argList::addBoolOption("initialize-Ha", "Initialize existing Ha from fresh prescribed p,T,Y at time zero");
    argList::addBoolOption("boundary-pressure", "Verify fixed-T Ha update after a ten-percent pressure change");
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    autoPtr<psiReactionThermo> model(psiReactionThermo::New(mesh));
    psiReactionThermo& thermo = model();
    basicSpecieMixture& composition = thermo.composition();
    volScalarField chemical
    (
        IOobject("probeChemicalEnthalpy", runTime.timeName(), mesh), mesh,
        dimensionedScalar("zero", dimEnergy/dimMass, 0)
    );
    forAll(composition.Y(), i)
    {
        chemical += dimensionedScalar("Hf", dimEnergy/dimMass, composition.Hf(i))*composition.Y()[i];
    }
    Info<< "Executed thermo: " << thermo.type() << nl;
    if (args.optionFound("boundary-pressure"))
    {
        volScalarField Ha
        (
            IOobject("Ha", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::NO_WRITE), mesh
        );
        if (!isA<fixedValueFvPatchScalarField>(thermo.T().boundaryField()[0]))
            FatalErrorInFunction << "Boundary pressure probe requires fixed-temperature patch zero" << exit(FatalError);
        updateFgmFixedTemperatureEnthalpy(thermo, composition, Ha);
        const scalar first = Ha.boundaryField()[0][0];
        thermo.p() *= scalar(1.1);
        updateFgmFixedTemperatureEnthalpy(thermo, composition, Ha);
        const tmp<volScalarField> independent = thermo.he(thermo.p(), thermo.T()) + chemical;
        const scalar expected = independent().boundaryField()[0][0];
        const scalar actual = Ha.boundaryField()[0][0];
        const scalar error = mag(actual - expected)/max(scalar(1), mag(expected));
        std::ofstream output((runTime.path()/"boundary-pressure.csv").c_str());
        output << std::setprecision(16) << "Ha_before_J_kg,Ha_after_J_kg,Ha_expected_J_kg,relative_error,pressure_after_Pa\n"
            << first << ',' << actual << ',' << expected << ',' << error << ',' << thermo.p()[0] << '\n';
        output.close();
        return output && std::isfinite(actual+expected) && error <= 1e-12 && mag(actual-first) > 1e-8 ? 0 : 3;
    }
    if (args.optionFound("initialize-Ha"))
    {
        if (runTime.value() != 0)
            FatalErrorInFunction << "Ha preparation requires a fresh time-zero case" << exit(FatalError);
        volScalarField Ha
        (
            IOobject("Ha", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::AUTO_WRITE), mesh
        );
        // Forced assignment preserves the case-owned boundary types.
        Ha == thermo.he(thermo.p(), thermo.T()) + chemical;
        forAll(Ha.boundaryField(), patchi)
        {
            if (Ha.boundaryField()[patchi].type() == "inletOutlet")
            {
                mixedFvPatchScalarField& outlet =
                    refCast<mixedFvPatchScalarField>(Ha.boundaryFieldRef()[patchi]);
                outlet.refValue() = Ha.boundaryField()[patchi];
            }
        }
        forAll(Ha, celli)
            if (!std::isfinite(Ha[celli])) FatalErrorInFunction << "Nonfinite initialized Ha" << exit(FatalError);
        forAll(Ha.boundaryField(), patchi)
            forAll(Ha.boundaryField()[patchi], facei)
                if (!std::isfinite(Ha.boundaryField()[patchi][facei]))
                    FatalErrorInFunction << "Nonfinite initialized boundary Ha" << exit(FatalError);
        if (!Ha.write()) FatalErrorInFunction << "Failed to write initialized Ha" << exit(FatalError);
        const tmp<volScalarField> density = thermo.rho();
        std::ofstream initial((runTime.path()/"ha-initialization-boundaries.csv").c_str());
        initial << std::setprecision(16) << "patch,area_m2,T_K,p_Pa,rho_kg_m3,Ha_J_kg\n";
        forAll(mesh.boundary(), patchi)
        {
            const scalarField& areas = mesh.magSf().boundaryField()[patchi];
            const scalar area = gSum(areas);
            if (area <= 0) continue;
            initial << mesh.boundary()[patchi].name() << ',' << area << ','
                << gSum(areas*thermo.T().boundaryField()[patchi])/area << ','
                << gSum(areas*thermo.p().boundaryField()[patchi])/area << ','
                << gSum(areas*density().boundaryField()[patchi])/area << ','
                << gSum(areas*Ha.boundaryField()[patchi])/area << '\n';
        }
        initial.close();
        if (!initial) FatalErrorInFunction << "Failed to write initialization boundary audit" << exit(FatalError);
        IOdictionary initialization
        (
            IOobject
            (
                "fgmHaInitialization", runTime.constant(), mesh,
                IOobject::NO_READ, IOobject::AUTO_WRITE
            )
        );
        initialization.add("preparedTime", scalar(0));
        initialization.add("thermoType", thermo.subDict("thermoType"));
        if (!initialization.regIOobject::write())
            FatalErrorInFunction << "Failed to write Ha initialization marker" << exit(FatalError);
        Info<< "Initialized Ha using full runtime EOS departure and formation basis" << nl;
        return 0;
    }
    IOdictionary configuration
    (
        IOobject("probeProperties", runTime.constant(), mesh, IOobject::MUST_READ, IOobject::NO_WRITE)
    );
    const scalar pressure = configuration.lookup<scalar>("pressure");
    const scalarList temperatures(configuration.lookup("temperatures"));
    const scalarList increments(configuration.lookup("increments"));
    const scalar initialGuessOffset = configuration.lookup<scalar>("initialGuessOffset");
    std::ofstream properties((runTime.path()/"cold-properties.csv").c_str());
    std::ofstream inversion((runTime.path()/"cold-inversion.csv").c_str());
    properties << std::setprecision(16)
        << "p_Pa,T_K,rho_kg_m3,Cp_J_kg_K,Cv_J_kg_K,Hs_J_kg,Ha_J_kg,mu_Pa_s,kappa_W_m_K,dHs_dT_J_kg_K\n";
    inversion << std::setprecision(16)
        << "p_Pa,T_start_K,delta_T_K,T_target_K,T_guess_K,T_recovered_K,error_K,Hs_target_J_kg,Hs_recovered_J_kg\n";
    label failures = 0;
    for (const scalar temperature : temperatures)
    {
        thermo.p() = dimensionedScalar("p", dimPressure, pressure);
        thermo.T() = dimensionedScalar("T", dimTemperature, temperature);
        thermo.he() = thermo.he(thermo.p(), thermo.T());
        thermo.correct();
        const scalar rho = thermo.rho()()[0], cp = thermo.Cp()()[0], cv = thermo.Cv()()[0];
        const scalar hs = thermo.he()[0], ha = hs + chemical[0];
        const scalar mu = thermo.mu()()[0], kappa = thermo.kappa()()[0];
        const scalar epsilon = 1e-3;
        thermo.T() = dimensionedScalar("T", dimTemperature, temperature + epsilon);
        const scalar upperH = thermo.he(thermo.p(), thermo.T())()[0];
        thermo.T() = dimensionedScalar("T", dimTemperature, temperature - epsilon);
        const scalar lowerH = thermo.he(thermo.p(), thermo.T())()[0];
        const scalar derivative = (upperH - lowerH)/(2*epsilon);
        const bool finite = std::isfinite(rho+cp+cv+hs+ha+mu+kappa+derivative);
        if (!finite || min(rho, min(cp, min(cv, min(mu, kappa)))) <= 0) ++failures;
        properties << pressure << ',' << temperature << ',' << rho << ',' << cp << ',' << cv
            << ',' << hs << ',' << ha << ',' << mu << ',' << kappa << ',' << derivative << std::endl;
        for (const scalar increment : increments)
        {
            const scalar target = temperature + increment;
            thermo.T() = dimensionedScalar("T", dimTemperature, target);
            thermo.he() = thermo.he(thermo.p(), thermo.T());
            const scalar targetH = thermo.he()[0];
            const scalar guess = temperature + initialGuessOffset;
            thermo.T().primitiveFieldRef() = guess;
            thermo.correct();
            const scalar recovered = thermo.T()[0];
            const scalar recoveredH = thermo.he(thermo.p(), thermo.T())()[0];
            const scalar error = recovered - target;
            if (!std::isfinite(recovered+recoveredH) || mag(error) > 1e-5) ++failures;
            inversion << pressure << ',' << temperature << ',' << increment << ',' << target << ','
                << guess << ',' << recovered << ',' << error << ',' << targetH << ',' << recoveredH << std::endl;
        }
    }
    properties.close(); inversion.close();
    if (!properties || !inversion) return 2;
    Info<< "Cold runtime diagnostic numerical failures: " << failures << nl;
    return failures ? 3 : 0;
}
