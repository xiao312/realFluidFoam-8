#ifndef thermoInversionWitness_H
#define thermoInversionWitness_H
#include "psiReactionThermo.H"
#include <fstream>
#include <iomanip>
#include <cstdio>
#include <cmath>

// A rolling pre-call input witness, separate from numerical time directories.
// It performs no EOS evaluation or field mutation, and no MPI collective.
inline void writeThermoInversionWitness
(
    const Foam::psiReactionThermo& thermo,
    const Foam::volScalarField& rho,
    const Foam::volScalarField& Ha,
    const Foam::word& stage
)
{
    using namespace Foam;
    const Time& time = rho.mesh().time();
    if (!time.controlDict().lookupOrDefault<Switch>
        ("writeThermoInversionWitness", false)) return;
    const scalar start = time.controlDict().lookupOrDefault<scalar>
        ("thermoInversionWitnessStartTime", 0);
    if (!std::isfinite(start) || start < 0)
        FatalErrorInFunction << "Witness start time must be finite and nonnegative"
            << exit(FatalError);
    if (time.value() < start) return;

    const fileName directory = time.path()/"thermo-inversion-witness";
    mkDir(directory);
    const fileName destination = directory/(stage + ".csv");
    const fileName temporary = destination + ".tmp";
    std::ofstream out(temporary.c_str());
    static unsigned long sequence = 0;
    out << std::setprecision(17)
        << "#schema=thermo-before-inversion/v1,time_s=" << time.value()
        << ",rank=" << Pstream::myProcNo() << ",stage=" << stage
        << ",sequence=" << ++sequence
        << ",accepted=false,authorizedForRestart=false\n"
        << "kind,patch,localIndex,p_Pa,T_K,Hs_J_kg,rho_kg_m3,Ha_J_kg";
    const auto& species = thermo.composition().Y();
    forAll(species, i) out << ",Y_" << species[i].name();
    out << '\n';
    forAll(thermo.he(), cell)
    {
        out << "cell,-," << cell << ',' << thermo.p()[cell] << ','
            << thermo.T()[cell] << ',' << thermo.he()[cell] << ','
            << rho[cell] << ',' << Ha[cell];
        forAll(species, i) out << ',' << species[i][cell];
        out << '\n';
    }
    forAll(thermo.p().boundaryField(), patch)
    {
        forAll(thermo.p().boundaryField()[patch], face)
        {
            out << "face," << rho.mesh().boundary()[patch].name() << ',' << face
                << ',' << thermo.p().boundaryField()[patch][face]
                << ',' << thermo.T().boundaryField()[patch][face]
                << ',' << thermo.he().boundaryField()[patch][face]
                << ',' << rho.boundaryField()[patch][face]
                << ',' << Ha.boundaryField()[patch][face];
            forAll(species, i)
                out << ',' << species[i].boundaryField()[patch][face];
            out << '\n';
        }
    }
    out.close();
    if (!out || std::rename(temporary.c_str(), destination.c_str()) != 0)
        FatalErrorInFunction << "Cannot retain pre-inversion witness "
            << destination << exit(FatalError);
}
#endif
