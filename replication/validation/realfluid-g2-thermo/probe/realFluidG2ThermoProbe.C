// Runtime factory and inversion pattern adapted from rfPropertyProbe.C.
// No EOS or caloric correlation is implemented in this diagnostic.
#include "fvCFD.H"
#include "psiReactionThermo.H"
#include "mixedFvPatchFields.H"
#include "../../../../applications/solvers/reactingFoamSolveZ/fgmBoundaryEnthalpy.H"
#include <fstream>
#include <iomanip>
#include <cmath>
#include <chrono>
#include "mixtureSetupAudit.H"
#include "enthalpyTargetAudit.H"

int main(int argc, char *argv[])
{
    argList::addBoolOption("initialize-Ha", "Initialize existing Ha from fresh prescribed p,T,Y at time zero");
    argList::addBoolOption("boundary-pressure", "Verify fixed-T Ha update after a ten-percent pressure change");
    argList::addBoolOption("read-Dimix", "Negative control: read internal diffusivity while suppressed");
    argList::addBoolOption("read-boundary-Dimix", "Negative control: read boundary diffusivity while suppressed");
    argList::addBoolOption("read-raw-Dimix", "Negative control: read raw SRK mixture diffusivity while suppressed");
    argList::addBoolOption("audit-mixture-setup", "Audit alternating physical cell and patch SRK mixture queries");
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    Info<< "FGM_HA_PHASE stage=thermo-construction-start elapsedWall_s=" << runTime.elapsedClockTime() << endl;
    autoPtr<psiReactionThermo> model(psiReactionThermo::New(mesh));
    Info<< "FGM_HA_PHASE stage=thermo-construction-complete elapsedWall_s=" << runTime.elapsedClockTime() << endl;
    psiReactionThermo& thermo = model();
    basicSpecieMixture& composition = thermo.composition();
    if (args.optionFound("audit-mixture-setup") || args.optionFound("read-raw-Dimix"))
        return auditSrkMixtureSetup(thermo, mesh, runTime, args.optionFound("read-raw-Dimix"));
    if (args.optionFound("read-Dimix"))
    {
        Info<< "Dimix access value " << thermo.Dimix(0)()[0] << endl;
        return 0;
    }
    if (args.optionFound("read-boundary-Dimix"))
    {
        Info<< "Boundary Dimix access value " << thermo.Dimix(0, 0)()[0] << endl;
        return 0;
    }
    volScalarField chemical
    (
        IOobject("probeChemicalEnthalpy", runTime.timeName(), mesh), mesh,
        dimensionedScalar("zero", dimEnergy/dimMass, 0)
    );
    forAll(composition.Y(), i)
    {
        chemical += dimensionedScalar("Hf", dimEnergy/dimMass, composition.Hf(i))*composition.Y()[i];
    }
    Info<< "FGM_HA_PHASE stage=formation-basis-complete elapsedWall_s=" << runTime.elapsedClockTime() << endl;
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
        Info<< "FGM_HA_PHASE stage=Ha-evaluation-start elapsedWall_s=" << runTime.elapsedClockTime() << endl;
        Ha == thermo.he(thermo.p(), thermo.T()) + chemical;
        Info<< "FGM_HA_PHASE stage=Ha-evaluation-complete elapsedWall_s=" << runTime.elapsedClockTime() << endl;
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
        Info<< "FGM_HA_PHASE stage=Ha-output-start elapsedWall_s=" << runTime.elapsedClockTime() << endl;
        if (!Ha.write()) FatalErrorInFunction << "Failed to write initialized Ha" << exit(FatalError);
        const tmp<volScalarField> density = thermo.rho();
        std::ofstream initial((runTime.path()/"ha-initialization-boundaries.csv").c_str());
        initial << std::setprecision(16) << "patch,area_m2,T_K,p_Pa,rho_kg_m3,Ha_J_kg\n";
        forAll(mesh.boundary(), patchi)
        {
            const scalarField& areas = mesh.magSf().boundaryField()[patchi];
            // Each rank has a different processor-patch list. Do not put
            // collective reductions inside this local boundary loop.
            const scalar area = sum(areas);
            if (area <= 0) continue;
            initial << mesh.boundary()[patchi].name() << ',' << area << ','
                << sum(areas*thermo.T().boundaryField()[patchi])/area << ','
                << sum(areas*thermo.p().boundaryField()[patchi])/area << ','
                << sum(areas*density().boundaryField()[patchi])/area << ','
                << sum(areas*Ha.boundaryField()[patchi])/area << '\n';
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
        initialization.add("preparedRank", Pstream::myProcNo());
        initialization.add("preparedRanks", Pstream::nProcs());
        initialization.add("thermoType", thermo.subDict("thermoType"));
        if (!initialization.regIOobject::write())
            FatalErrorInFunction << "Failed to write Ha initialization marker" << exit(FatalError);
        Info<< "FGM_HA_PHASE stage=Ha-initialization-complete elapsedWall_s=" << runTime.elapsedClockTime() << endl;
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
        << "p_Pa,T_K,rho_kg_m3,Cp_J_kg_K,Cv_J_kg_K,Hs_J_kg,Ha_J_kg,mu_Pa_s,kappa_W_m_K,dHs_dT_J_kg_K,alpha_kg_m_s,T_recovered_K\n";
    inversion << std::setprecision(16)
        << "p_Pa,T_start_K,delta_T_K,T_target_K,T_guess_K,T_recovered_K,error_K,Hs_target_J_kg,Hs_recovered_J_kg\n";
    label failures = auditCapturedEnthalpyTargets(thermo, configuration, runTime);
    for (const scalar temperature : temperatures)
    {
        thermo.p() = dimensionedScalar("p", dimPressure, pressure);
        thermo.T() = dimensionedScalar("T", dimTemperature, temperature);
        thermo.he() = thermo.he(thermo.p(), thermo.T());
        thermo.correct();
        const scalar rho = thermo.rho()()[0], cp = thermo.Cp()()[0], cv = thermo.Cv()()[0];
        const scalar hs = thermo.he()[0], ha = hs + chemical[0];
        const scalar mu = thermo.mu()()[0], kappa = thermo.kappa()()[0];
        const scalar alpha = thermo.alpha()[0], correctedT = thermo.T()[0];
        const scalar epsilon = 1e-3;
        thermo.T() = dimensionedScalar("T", dimTemperature, temperature + epsilon);
        const scalar upperH = thermo.he(thermo.p(), thermo.T())()[0];
        thermo.T() = dimensionedScalar("T", dimTemperature, temperature - epsilon);
        const scalar lowerH = thermo.he(thermo.p(), thermo.T())()[0];
        const scalar derivative = (upperH - lowerH)/(2*epsilon);
        const bool finite = std::isfinite(rho+cp+cv+hs+ha+mu+kappa+derivative+alpha+correctedT);
        if (!finite || min(rho, min(cp, min(cv, min(mu, min(kappa, alpha))))) <= 0) ++failures;
        properties << pressure << ',' << temperature << ',' << rho << ',' << cp << ',' << cv
            << ',' << hs << ',' << ha << ',' << mu << ',' << kappa << ',' << derivative
            << ',' << alpha << ',' << correctedT << std::endl;
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
    const label timingCorrections = configuration.lookupOrDefault<label>("timingCorrections", 0);
    if (timingCorrections < 0 || timingCorrections > 1000)
        FatalErrorInFunction << "timingCorrections must be in 0..1000" << exit(FatalError);
    if (timingCorrections)
    {
        const auto start = std::chrono::steady_clock::now();
        for (label repeat = 0; repeat < timingCorrections; ++repeat) thermo.correct();
        const double wall = std::chrono::duration<double>
        (
            std::chrono::steady_clock::now() - start
        ).count();
        std::ofstream timing((runTime.path()/"thermo-correction-timing.csv").c_str());
        timing << std::setprecision(16) << "corrections,cells,wall_s\n"
            << timingCorrections << ',' << mesh.nCells() << ',' << wall << '\n';
        timing.close();
        if (!timing) return 2;
    }
    Info<< "Cold runtime diagnostic numerical failures: " << failures << nl;
    return failures ? 3 : 0;
}
