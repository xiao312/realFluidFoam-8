#ifndef contactAveragingAudit_H
#define contactAveragingAudit_H
#include "../../../../applications/solvers/reactingFoamSolveZ/srkPressureDensitySlope.H"

inline Foam::label auditContactAveraging
(
    Foam::psiReactionThermo& thermo, const Foam::fvMesh& mesh,
    const Foam::Time& runTime
)
{
    using namespace Foam;
    const PressureSlopeMixture* mixture=
        dynamic_cast<const PressureSlopeMixture*>(&thermo.composition());
    const speciesTable& species=thermo.composition().species();
    if (!mixture || mesh.nCells()!=1 || species.size()!=2
     || !species.found("H2") || !species.found("O2") || runTime.value()!=0)
        FatalErrorInFunction << "Contact averaging requires a fresh one-cell H2/O2 SRK case"
            << exit(FatalError);
    IOdictionary configuration
    (
        IOobject("contactAveragingAudit",runTime.constant(),mesh,
            IOobject::MUST_READ,IOobject::NO_WRITE)
    );
    const scalar pressure=configuration.lookup<scalar>("pressure");
    const scalar temperature=configuration.lookup<scalar>("temperature");
    const label intervals=configuration.lookup<label>("compositionIntervals");
    const label volumeIntervals=configuration.lookup<label>("volumeFractionIntervals");
    if (!(pressure>0 && temperature>0) || intervals<2 || volumeIntervals<2)
        FatalErrorInFunction << "Positive p/T and at least two intervals required"
            << exit(FatalError);
    const label oxygen=species["O2"],hydrogen=species["H2"];
    auto compositionAt = [&](scalar oxygenMassFraction)
    {
        // Uniform one-cell state, including its patches: leaving a pure-stream
        // patch composition while assigning a mixed enthalpy would test a
        // different boundary inversion rather than the intended volume state.
        thermo.composition().Y()[oxygen]=dimensionedScalar("Y_O2",dimless,oxygenMassFraction);
        thermo.composition().Y()[hydrogen]=dimensionedScalar("Y_H2",dimless,1-oxygenMassFraction);
    };
    std::ofstream scan((runTime.path()/"contact-isothermal-composition.csv").c_str());
    scan<<std::setprecision(17)
        <<"Y_O2,p_Pa,T_K,rho_kg_m3,Hs_J_kg,Cp_J_kg_K,Cv_J_kg_K,finite_positive\n";
    scalar rhoH=0,rhoO=0,hH=0,hO=0;
    label failures=0;
    for (label i=0;i<=intervals;++i)
    {
        const scalar fraction=scalar(i)/intervals;
        compositionAt(fraction);
        const PressureSlopeThermo& point=mixture->cellMixture(0);
        if (point.limit(temperature)!=temperature)
            FatalErrorInFunction << "Prescribed temperature outside unchanged input bounds"
                << exit(FatalError);
        const scalar density=point.rho(pressure,temperature);
        const scalar h=point.Hs(pressure,temperature);
        const scalar cp=point.Cp(pressure,temperature),cv=point.Cv(pressure,temperature);
        const bool finite=std::isfinite(density+h+cp+cv) && density>0 && cp>0 && cv>0;
        scan<<fraction<<','<<pressure<<','<<temperature<<','<<density<<','<<h
            <<','<<cp<<','<<cv<<','<<label(finite)<<'\n';
        if (!finite) ++failures;
        if (i==0) {rhoH=density;hH=h;}
        if (i==intervals) {rhoO=density;hO=h;}
    }
    scan.close();
    if (!(rhoH>0 && rhoO>0) || !std::isfinite(rhoH+rhoO+hH+hO))
        FatalErrorInFunction << "Invalid pure-stream controls" << exit(FatalError);
    std::ofstream averages((runTime.path()/"contact-volume-averaging.csv").c_str());
    averages<<std::setprecision(17)
        <<"oxygen_volume_fraction,Y_O2,rho_average_kg_m3,Hs_average_J_kg,"
        <<"homogeneous_Hs_at_initialT_J_kg,T_reconstructed_K,rho_reconstructed_kg_m3,"
        <<"absolute_caloric_error_J_kg,caloric_relative_error,density_relative_error,"
        <<"caloric_passed,density_passed,endpoint_control\n";
    for (label i=0;i<=volumeIntervals;++i)
    {
        const scalar volumeFraction=scalar(i)/volumeIntervals;
        const scalar density=volumeFraction*rhoO+(1-volumeFraction)*rhoH;
        const scalar fraction=volumeFraction*rhoO/density;
        const scalar target=(volumeFraction*rhoO*hO+(1-volumeFraction)*rhoH*hH)/density;
        compositionAt(fraction);
        // Read the fresh mixture after each composition change. Its cache is
        // mutable and must not be retained across thermo.correct() patch calls.
        const scalar homogeneousInitialH=mixture->cellMixture(0).Hs(pressure,temperature);
        thermo.p()=dimensionedScalar("p",dimPressure,pressure);
        thermo.T()=dimensionedScalar("T",dimTemperature,temperature);
        thermo.he()=dimensionedScalar("h",dimEnergy/dimMass,target);
        for (label pass=0;pass<12;++pass) thermo.correct();
        const scalar reconstructedT=thermo.T()[0];
        const PressureSlopeThermo& point=mixture->cellMixture(0);
        const scalar actualH=point.Hs(pressure,reconstructedT);
        const scalar actualRho=point.rho(pressure,reconstructedT);
        const scalar cp=point.Cp(pressure,reconstructedT);
        const scalar absolute=mag(actualH-target);
        const scalar scale=max(scalar(1),max(mag(target),max(mag(actualH),mag(cp*reconstructedT))));
        const scalar caloricError=absolute/scale,densityError=mag(actualRho-density)/density;
        const bool finite=std::isfinite(actualH+actualRho+reconstructedT+cp)
            && actualRho>0 && cp>0 && reconstructedT>0 && thermo.he()[0]==target;
        const bool caloricPassed=finite && caloricError<=1e-8;
        const bool densityPassed=finite && densityError<=1e-8;
        averages<<volumeFraction<<','<<fraction<<','<<density<<','<<target<<','<<homogeneousInitialH
            <<','<<reconstructedT<<','<<actualRho<<','<<absolute<<','<<caloricError
            <<','<<densityError<<','<<label(caloricPassed)<<','<<label(densityPassed)
            <<','<<label(i==0 || i==volumeIntervals)<<std::endl;
        if (!caloricPassed || !densityPassed) ++failures;
    }
    averages.close();
    if (!scan || !averages)
        FatalErrorInFunction << "Failed to write contact-averaging diagnostics" << exit(FatalError);
    Info<< "CONTACT_AVERAGING_QUERY failedOrIncompatibleRows=" << failures
        << " CFDsteps=0 acceptanceChanged=0 rootPolicyChanged=0" << endl;
    return failures ? 3 : 0;
}
#endif
