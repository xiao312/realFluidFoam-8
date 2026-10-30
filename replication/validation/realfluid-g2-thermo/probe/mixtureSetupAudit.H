// Exercise the real SRK mixture implementation; no property model is copied.
#include "forSRKchungTakaGases.H"
#include "SRKchungTakaMixture.H"

namespace Foam
{
typedef chungTakaTransport<species::thermo<rfJanafThermo<
    soaveRedlichKwong<rfSpecie>>, sensibleEnthalpy>> SetupThermo;
typedef SRKchungTakaMixture<SetupThermo> SetupMixture;

inline int auditSrkMixtureSetup
(
    psiReactionThermo& thermo, const fvMesh& mesh, const Time& runTime,
    const bool rawDiffusivity
)
{
    basicSpecieMixture& composition = thermo.composition();
    const SetupMixture* mixture = dynamic_cast<const SetupMixture*>(&composition);
    if (!mixture)
        FatalErrorInFunction << "Setup audit requires the exact sensible-enthalpy SRK Chung mixture" << exit(FatalError);
    if (rawDiffusivity)
    {
        const SetupThermo& state = mixture->cellMixture(0);
        Info<< "Raw Dimix access value " << state.Dimix(0, thermo.p()[0], thermo.T()[0]) << endl;
        return 0;
    }
    IOdictionary input(IOobject("mixtureSetupAudit", runTime.constant(), mesh,
        IOobject::MUST_READ, IOobject::NO_WRITE));
    const wordList names(input.lookup("species"));
    const scalarList pressures(input.lookup("pressures"));
    const scalarList temperatures(input.lookup("temperatures"));
    const List<scalarList> fractions(input.lookup("massFractions"));
    if (names != composition.species() || fractions.size() != 3 ||
        pressures.size() != 3 || temperatures.size() != 3 || mesh.boundary()[0].size() == 0)
        FatalErrorInFunction << "Audit requires three ordered physical states and a nonempty patch zero" << exit(FatalError);
    std::ofstream output((runTime.path()/"mixture-setup.csv").c_str());
    output << std::setprecision(17)
        << "state,location,p_Pa,T_K,rho,Cp,Cv,Hs,Ha,mu,kappa,alphah,TcmdRows,PcmdRows,MmdRows,sigmdRows";
    forAll(names, i) output << ",X_" << names[i] << ",Y_" << names[i];
    output << '\n';
    forAll(fractions, statei)
    {
        const scalarList& y = fractions[statei];
        if (y.size() != names.size() || mag(sum(y)-1) > 1e-12 || min(y) < 0)
            FatalErrorInFunction << "Invalid physical composition for audit" << exit(FatalError);
        forAll(y, i)
            composition.Y()[i] == dimensionedScalar("Y", dimless, y[i]);
        for (label location = 0; location < 2; ++location)
        {
            // Mixture methods share scratch storage: consume each result before
            // the next query, including the repeated A state after B.
            const SetupThermo& state = location == 0
                ? mixture->cellMixture(0) : mixture->patchFaceMixture(0, 0);
            const scalar p = pressures[statei], t = temperatures[statei];
            output << statei << ',' << location << ',' << p << ',' << t
                << ',' << state.rho(p,t) << ',' << state.Cp(p,t) << ',' << state.Cv(p,t)
                << ',' << state.Hs(p,t) << ',' << state.Ha(p,t)
                << ',' << state.mu(p,t) << ',' << state.kappa(p,t) << ',' << state.alphah(p,t)
                << ',' << state.Tcmd().size() << ',' << state.Pcmd().size()
                << ',' << state.Mmd().size() << ',' << state.sigmd().size();
            forAll(names, i) output << ',' << state.Xmd()[i] << ',' << state.Ymd()[i];
            output << '\n';
        }
    }
    output.close();
    return output ? 0 : 2;
}
}
