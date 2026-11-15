#ifndef rhoHaStateAudit_H
#define rhoHaStateAudit_H
#include "../../../../applications/solvers/reactingFoamSolveZ/srkRhoHaRecovery.H"

inline Foam::label auditRhoHaState
(
    Foam::psiReactionThermo& thermo, const Foam::fvMesh& mesh, const Foam::Time& time
)
{
    using namespace Foam;
    const PressureSlopeMixture* mixture=dynamic_cast<const PressureSlopeMixture*>(&thermo.composition());
    if (!mixture || mesh.nCells()!=1 || time.value()!=0)
        FatalErrorInFunction<<"Fresh one-cell SRK state query required"<<exit(FatalError);
    IOdictionary input(IOobject("rhoHaAudit",time.constant(),mesh,IOobject::MUST_READ,IOobject::NO_WRITE));
    const scalar rho=input.lookup<scalar>("density");
    const scalar ha=input.lookup<scalar>("absoluteEnthalpy");
    const scalar pressure=input.lookup<scalar>("referencePressure");
    const scalarList guesses(input.lookup("guesses"));
    if (!guesses.size()) FatalErrorInFunction<<"At least one recovery guess required"<<exit(FatalError);
    const PressureSlopeThermo& model=mixture->cellMixture(0);
    std::ofstream out((time.path()/"rho-ha-state.csv").c_str());
    out<<std::setprecision(17)<<"rho_kg_m3,Ha_target_J_kg,guess_K,T_K,p_Pa,deltaP_Pa,Ha_error_J_kg,Cv_J_kg_K,dp_drho_T,selectedRhoRelativeError,selectedHaRelativeError,iterations,caloricConverged,mechanicallyStable,selectedRootMatches,passed,reason\n";
    label failed=0;
    for (const scalar guess:guesses)
    {
        const auto result=recoverSrkDensityEnthalpy(model,rho,ha,pressure,guess);
        if (!result.passed()) ++failed;
        out<<rho<<','<<ha<<','<<guess<<','<<result.temperature<<','<<result.pressure
            <<','<<result.pressure-pressure<<','<<result.enthalpyError<<','<<result.cv
            <<','<<result.isothermalSlope<<','<<result.selectedDensityRelativeError
            <<','<<result.selectedEnthalpyRelativeError<<','<<result.iterations
            <<','<<label(result.caloricConverged)<<','<<label(result.mechanicallyStable)
            <<','<<label(result.selectedRootMatches)<<','<<label(result.passed())
            <<','<<result.reason.c_str()<<std::endl;
    }
    out.close();
    Info<<"RHO_HA_STATE_QUERY failed="<<failed<<" CFDsteps=0 fieldsModified=0"<<endl;
    return out && !failed ? 0 : 3;
}
#endif
