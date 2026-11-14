#ifndef manifoldEnthalpyAudit_H
#define manifoldEnthalpyAudit_H
#include "../../../../applications/solvers/reactingFoamSolveZ/srkPressureDensitySlope.H"

// Direct queries through the same concrete SRK mixture/inversion as the solver.
// No cubic EOS, caloric polynomial, phase rule or tolerance is reimplemented.
inline Foam::label auditManifoldEnthalpy
(
    Foam::psiReactionThermo& thermo, const Foam::fvMesh& mesh,
    const Foam::Time& runTime
)
{
    using namespace Foam;
    const PressureSlopeMixture* mixture =
        dynamic_cast<const PressureSlopeMixture*>(&thermo.composition());
    const speciesTable& species = thermo.composition().species();
    if (!mixture || mesh.nCells() != 1 || runTime.value() != 0
        || !species.found("O2") || !species.found("CH4"))
        FatalErrorInFunction << "Fresh one-cell O2/CH4-containing SRK query required"
            << exit(FatalError);
    IOdictionary input(IOobject("manifoldEnthalpyAudit", runTime.constant(), mesh,
        IOobject::MUST_READ, IOobject::NO_WRITE));
    const wordList names(input.lookup("species"));
    const scalar referencePressure = input.lookup<scalar>("referencePressure");
    const scalar oxygenTemperature = input.lookup<scalar>("oxygenTemperature");
    const scalar fuelTemperature = input.lookup<scalar>("fuelTemperature");
    const scalarList pressures(input.lookup("pressures"));
    const scalarList fractions(input.lookup("mixtureFractions"));
    const scalarList temperatures(input.lookup("temperatures"));
    const List<scalarList> compositions(input.lookup("massFractions"));
    if (names != species || fractions.size() != compositions.size()
        || temperatures.size() != fractions.size() || !fractions.size()
        || !pressures.size() || !(referencePressure > 0)
        || !(oxygenTemperature > 0 && fuelTemperature > 0))
        FatalErrorInFunction << "Invalid manifold query inventory/conditions"
            << exit(FatalError);
    const label oxygen = species["O2"], fuel = species["CH4"];
    auto assign = [&](const scalarList& y)
    {
        if (y.size() != species.size() || min(y) < 0 || mag(sum(y)-1) > 1e-8)
            FatalErrorInFunction << "Invalid unmodified composition row"
                << exit(FatalError);
        forAll(y, i) thermo.composition().Y()[i] = dimensionedScalar("Y", dimless, y[i]);
    };
    auto chemicalEnthalpy = [&]()
    {
        scalar value = 0;
        forAll(species, i)
            value += thermo.composition().Y()[i][0]*thermo.composition().Hf(i);
        return value;
    };
    std::ofstream inlets((runTime.path()/"manifold-inlets.csv").c_str());
    inlets << std::setprecision(17)
        << "species,p_Pa,T_K,Hs_J_kg,Hchemical_J_kg,Ha_basis_J_kg,Ha_api_J_kg\n";
    scalar inletHa[2];
    for (label endpoint = 0; endpoint < 2; ++endpoint)
    {
        scalarList y(species.size(), 0);
        const label selected = endpoint == 0 ? oxygen : fuel;
        const scalar t = endpoint == 0 ? oxygenTemperature : fuelTemperature;
        y[selected] = 1; assign(y);
        const PressureSlopeThermo& state = mixture->cellMixture(0);
        if (state.limit(t) != t)
            FatalErrorInFunction << "Inlet outside unchanged thermo bounds" << exit(FatalError);
        const scalar hs = state.Hs(referencePressure, t), hc = chemicalEnthalpy();
        inletHa[endpoint] = hs + hc;
        inlets << species[selected] << ',' << referencePressure << ',' << t << ','
            << hs << ',' << hc << ',' << inletHa[endpoint] << ','
            << state.Ha(referencePressure, t) << '\n';
    }
    inlets.close();
    std::ofstream output((runTime.path()/"manifold-inversion.csv").c_str());
    output << std::setprecision(17)
        << "closure,p_Pa,Z,tableT_K,guess_K,Ha_target_J_kg,Hchemical_J_kg,"
        << "Hs_target_J_kg,T_recovered_K,rho_kg_m3,Cp_J_kg_K,Cv_J_kg_K,"
        << "literalHs_J_kg,absolute_error_J_kg,caloric_relative_error,"
        << "enthalpy_relative_error,finite_positive,caloric_passed,strict_passed\n";
    label failed = 0, queries = 0;
    forAll(fractions, row)
    {
        const scalar z = fractions[row], tableT = temperatures[row];
        if (!std::isfinite(z+tableT) || z < 0 || z > 1 || !(tableT > 0))
            FatalErrorInFunction << "Invalid query Z/T" << exit(FatalError);
        const scalar targetHa = (1-z)*inletHa[0] + z*inletHa[1];
        for (label closure = 0; closure < 2; ++closure)
        {
            scalarList y = compositions[row];
            if (closure == 1)
            {
                forAll(y, i) y[i] = 0;
                y[oxygen] = 1-z; y[fuel] = z;
            }
            assign(y);
            const scalar hc = chemicalEnthalpy(), target = targetHa-hc;
            const PressureSlopeThermo& state = mixture->cellMixture(0);
            const scalar coldGuess = (1-z)*oxygenTemperature + z*fuelTemperature;
            const scalar guesses[3] = {tableT, coldGuess, 300};
            forAll(pressures, pi) for (label gi = 0; gi < 3; ++gi)
            {
                const scalar p = pressures[pi], guess = guesses[gi];
                if (!std::isfinite(p+guess) || !(p > 0) || state.limit(guess) != guess)
                    FatalErrorInFunction << "Query p/guess outside input bounds" << exit(FatalError);
                std::ofstream progress((runTime.path()/"manifold-progress.txt").c_str());
                progress << std::setprecision(17) << "closure=" << closure
                    << " p=" << p << " Z=" << z << " guess=" << guess << '\n';
                progress.close();
                const scalar t = state.THs(target, p, guess);
                const scalar actual = state.Hs(p,t), rho = state.rho(p,t);
                const scalar cp = state.Cp(p,t), cv = state.Cv(p,t);
                const scalar error = mag(actual-target);
                const scalar scale = max(scalar(1),max(mag(target),max(mag(actual),mag(cp*t))));
                const scalar relative = error/scale;
                const scalar strict = error/max(scalar(1),max(mag(target),mag(actual)));
                const bool finite = std::isfinite(t+rho+cp+cv+actual+relative+strict)
                    && t > 0 && rho > 0 && cp > 0 && cv > 0;
                const bool caloric = finite && relative <= 1e-8;
                const bool strictPassed = caloric && strict <= 1e-8;
                output << (closure == 0 ? "reacting" : "passive") << ',' << p << ','
                    << z << ',' << tableT << ',' << guess << ',' << targetHa << ',' << hc
                    << ',' << target << ',' << t << ',' << rho << ',' << cp << ',' << cv
                    << ',' << actual << ',' << error << ',' << relative << ',' << strict
                    << ',' << label(finite) << ',' << label(caloric) << ','
                    << label(strictPassed) << std::endl;
                ++queries; if (!strictPassed) ++failed;
            }
        }
    }
    output.close();
    if (!output || !inlets)
        FatalErrorInFunction << "Manifold output write failed" << exit(FatalError);
    Info << "MANIFOLD_ENTHALPY_QUERY queries=" << queries << " failed=" << failed
        << " CFDsteps=0 acceptanceChanged=0 rootPolicyChanged=0" << endl;
    return failed ? 3 : 0;
}
#endif
