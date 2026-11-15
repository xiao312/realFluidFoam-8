#ifndef relaxationProbe_H
#define relaxationProbe_H
#include "steadyFlameletTable.H"
#include "relaxationClock.H"
#include <fstream>
#include <iomanip>
#include <cmath>

// Model-source/property qualification only: no flow equation or Time++.
// This is not a sealed-volume mass/energy experiment or a CFD restart.
template<class Model>
Foam::label auditRelaxedSpeciesSource
(
    Foam::psiReactionThermo& thermo, Model& reaction, Foam::fvMesh& mesh,
    const Foam::Time& runTime, Foam::volScalarField& Ha
)
{
    using namespace Foam;
    if (mesh.nCells() != 1 || runTime.value() != 0)
        FatalErrorInFunction << "Relaxation probe requires a fresh one-cell relaxedTable case"
            << exit(FatalError);
    const IOdictionary configuration(IOobject("combustionProperties",runTime.constant(),mesh,
        IOobject::MUST_READ,IOobject::NO_WRITE,false));
    if (configuration.lookupOrDefault<word>("combustionModel", "") != "relaxedTable")
        FatalErrorInFunction << "relaxedTable required" << exit(FatalError);
    const dictionary& coefficients = configuration.subDict("relaxedTableCoeffs");
    const auto clock = Foam::combustionModels::relaxedTableClock(coefficients, runTime.deltaTValue());
    const scalar Cr = 1/clock.alpha;
    const fileName tableFile(coefficients.lookup("table"));
    const forgeSteady::Table table(tableFile.c_str());
    const volScalarField& Z = mesh.lookupObject<volScalarField>("Z");
    const forgeSteady::State target = table.lookup(Z[0]);
    basicSpecieMixture& composition = thermo.composition();
    PtrList<volScalarField>& y = composition.Y();
    labelList map(table.species.size(), -1);
    scalarField initial(table.species.size(), scalar(0));
    forAll(map, s)
    {
        forAll(y, i) if (y[i].name() == table.species[s].c_str()) map[s] = i;
        if (map[s] < 0) FatalErrorInFunction << "Reference target species missing" << exit(FatalError);
        initial[s] = y[map[s]][0];
    }
    const label steps = runTime.controlDict().lookupOrDefault<label>("relaxationProbeSteps",20);
    if (steps < 1) FatalErrorInFunction << "Positive relaxationProbeSteps required" << exit(FatalError);
    const scalar initialHa = Ha[0], dt = runTime.deltaTValue();
    std::ofstream output((runTime.path()/"relaxation-probe.csv").c_str());
    output << std::setprecision(17)
        << "pseudoStep,Cr,alpha,dt_s,T_K,p_Pa,maxYReferenceError,sumYError,"
        << "HaMutation_J_kg,HsRelativeError,Qdot_W_m3,QdotRelativeIdentityError,passed,mode,tau_s\n";
    bool allPassed = true;
    for (label step=1; step<=steps; ++step)
    {
        const scalar beforeChemical = fgmChemicalEnthalpy(mesh,composition)()[0];
        const scalar sourceDensity = reaction.rho()[0];
        reaction.correct();
        reaction.correctSpeciesAfterTransport();
        const scalar afterChemical = fgmChemicalEnthalpy(mesh,composition)()[0];
        thermo.he() == Ha-fgmChemicalEnthalpy(mesh,composition);
        for (label pass=0; pass<3; ++pass) thermo.correct();
        auditFgmThermoClosure(thermo);
        scalar worst = 0, sum = 0;
        const scalar factor = std::pow(1-clock.alpha,step);
        forAll(map, s)
        {
            const scalar expected = target.y[s] + (initial[s]-target.y[s])*factor;
            worst = max(worst,mag(y[map[s]][0]-expected));
            sum += y[map[s]][0];
        }
        const scalar literal = thermo.he(thermo.p(),thermo.T())()[0];
        const scalar cp = thermo.Cp()()[0], t = thermo.T()[0], stored = thermo.he()[0];
        const scalar scale = max(scalar(1),max(mag(stored),max(mag(literal),mag(cp*t))));
        const scalar relative = mag(literal-stored)/scale;
        const scalar q = reaction.Qdot()()[0];
        const scalar expectedQ = -sourceDensity*(afterChemical-beforeChemical)/dt;
        const scalar qError = mag(q-expectedQ)/max(scalar(1),max(mag(q),mag(expectedQ)));
        const scalar mutation = Ha[0]-initialHa;
        const bool passed = std::isfinite(worst+relative+qError+t)
            && worst<=1e-12 && mag(sum-1)<=1e-8 && mutation==0
            && relative<=1e-8 && qError<=1e-10;
        allPassed = allPassed && passed;
        output << step << ',' << Cr << ',' << 1/Cr << ',' << dt << ',' << t << ','
            << thermo.p()[0] << ',' << worst << ',' << mag(sum-1) << ',' << mutation
            << ',' << relative << ',' << q << ',' << qError << ',' << label(passed)
            << ',' << clock.mode.c_str() << ',' << clock.time << std::endl;
    }
    output.close();
    Info<< "RELAXATION_SOURCE_PROBE steps=" << steps << " allPassed=" << allPassed
        << " CFDsteps=0 physicalTimeUnchanged=1 massConservationNotTested=1" << endl;
    return output && allPassed ? 0 : 3;
}
#endif
