#ifndef enthalpyTargetAudit_H
#define enthalpyTargetAudit_H

// Pure thermodynamic queries through the executing library; no flow steps.
inline Foam::label auditCapturedEnthalpyTargets
(
    Foam::psiReactionThermo& thermo,
    const Foam::IOdictionary& configuration,
    const Foam::Time& runTime
)
{
    using namespace Foam;
    if (!configuration.found("enthalpyTargets")) return 0;
    const scalarList targets(configuration.lookup("enthalpyTargets"));
    const scalarList guesses(configuration.lookup("targetGuesses"));
    const scalar pressure=configuration.lookup<scalar>("pressure");
    const label passes=configuration.lookupOrDefault<label>("targetCorrectionPasses",12);
    const scalar limit=configuration.lookupOrDefault<scalar>("targetRelativeLimit",1e-8);
    if (!targets.size() || !guesses.size() || passes<1 || passes>50
     || !std::isfinite(limit) || !(limit>0))
        FatalErrorInFunction << "Invalid captured-enthalpy query controls" << exit(FatalError);
    std::ofstream output((runTime.path()/"cold-target-inversion.csv").c_str());
    output<<std::setprecision(17)
        <<"targetHs_J_kg,guess_K,pass,p_Pa,T_K,storedHs_J_kg,literalHs_J_kg,Cp_J_kg_K,absolute_error_J_kg,relative_error,enthalpy_relative_error,stored_mutation_J_kg,caloric_audit_passed,converged\n";
    label failures=0;
    for (const scalar target:targets) for (const scalar guess:guesses)
    {
        if (!std::isfinite(target) || !std::isfinite(guess) || !(guess>0))
            FatalErrorInFunction << "Nonfinite target or invalid initial guess" << exit(FatalError);
        thermo.p()=dimensionedScalar("p",dimPressure,pressure);
        thermo.T()=dimensionedScalar("T",dimTemperature,guess);
        thermo.he()=dimensionedScalar("h",dimEnergy/dimMass,target);
        bool converged=false;
        for (label pass=1;pass<=passes;++pass)
        {
            thermo.correct();
            const scalar temperature=thermo.T()[0],stored=thermo.he()[0];
            const scalar actual=thermo.he(thermo.p(),thermo.T())()[0];
            const scalar cp=thermo.Cp()()[0],absolute=mag(actual-target);
            const scalar scale=max(scalar(1),max(mag(target),max(mag(actual),mag(cp*temperature))));
            const scalar relative=absolute/scale,mutation=stored-target;
            const scalar enthalpyRelative=absolute/max(scalar(1),max(mag(target),mag(actual)));
            const bool caloricPassed=std::isfinite(relative) && relative<=limit;
            converged=std::isfinite(actual+stored+cp+temperature+relative)
                && cp>0 && temperature>0 && mutation==0 && caloricPassed && enthalpyRelative<=limit;
            output<<target<<','<<guess<<','<<pass<<','<<pressure<<','<<temperature
                <<','<<stored<<','<<actual<<','<<cp<<','<<absolute<<','<<relative
                <<','<<enthalpyRelative<<','<<mutation<<','<<label(caloricPassed)<<','<<label(converged)<<std::endl;
            if (converged) break;
        }
        if (!converged) ++failures;
    }
    output.close();
    if (!output) FatalErrorInFunction << "Failed to save captured-enthalpy queries" << exit(FatalError);
    Info<<"CAPTURED_ENTHALPY_QUERY unresolvedTargets="<<failures
        <<" relativeLimit="<<limit<<" CFDsteps=0"<<endl;
    return failures;
}
#endif
