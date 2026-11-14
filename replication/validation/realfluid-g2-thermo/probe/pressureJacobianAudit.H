// Diagnose the actual library; this does not select a CFD pressure operator.
#include "../../../../applications/solvers/reactingFoamSolveZ/srkPressureDensitySlope.H"

namespace Foam
{
inline int auditPressureJacobian
(
    psiReactionThermo& thermo, const fvMesh& mesh, const Time& runTime
)
{
    const PressureSlopeMixture* mixture =
        dynamic_cast<const PressureSlopeMixture*>(&thermo.composition());
    if (!mixture || mesh.nCells() != 1)
        FatalErrorInFunction << "Pressure Jacobian audit requires a one-cell SRK mixture"
            << exit(FatalError);
    IOdictionary input(IOobject("pressureJacobianAudit", runTime.constant(), mesh,
        IOobject::MUST_READ, IOobject::NO_WRITE));
    const scalarList temperatures(input.lookup("temperatures"));
    const scalarList steps(input.lookup("relativePressureSteps"));
    const PressureSlopeThermo& state = mixture->cellMixture(0);
    const scalar p = thermo.p()[0];
    std::ofstream output((runTime.path()/"pressure-jacobian.csv").c_str());
    output << std::setprecision(17)
        << "p_Pa,T_K,relative_pressure_step,rho_kg_m3,Cp_J_kg_K,Cv_J_kg_K,"
        << "alpha_1_K,betaT_kg_m3_Pa,betaH_kg_m3_Pa,betaT_FD,betaH_FD,"
        << "betaT_relative_error,betaH_relative_error,Cp_FD,Cp_relative_error,"
        << "Tminus_K,Tplus_K,hminus_error_J_kg,hplus_error_J_kg,passed\n";
    bool passed = true;
    forAll(temperatures, ti)
    {
        const scalar T=temperatures[ti];
        const scalar rho=state.rho(p,T), W=state.W(), b=state.bM()/W;
        const scalar Cp=state.Cp(p,T), Cv=state.Cv(p,T);
        const scalar betaT=srkIsothermalDensitySlope(state,p,T);
        const scalar attractionT=(-0.5*state.coef2()/std::sqrt(T)
            +state.coef3())/(W*W);
        const scalar pressureT=state.R()*rho/(1-b*rho)
            -attractionT*sqr(rho)/(1+b*rho);
        const scalar alpha=pressureT*betaT/rho;
        // dh=Cp*dT+(1-T*alpha)/rho*dp. The Cv form avoids subtracting
        // two large near-critical terms in betaT+alpha*(1-T*alpha)/Cp.
        const scalar betaH=(Cv*betaT+alpha)/Cp;
        const scalar h=state.Hs(p,T), dT=1e-3;
        const scalar cpFD=(state.Hs(p,T+dT)-state.Hs(p,T-dT))/(2*dT);
        const scalar cpError=mag(cpFD-Cp)/max(scalar(1e-30),mag(Cp));
        forAll(steps, si)
        {
            const scalar step=steps[si];
            if (!(step>0 && step<0.01 && T>60+dT && T<6000-dT))
                FatalErrorInFunction << "Invalid pressure-Jacobian input"
                    << exit(FatalError);
            const scalar dp=p*step;
            const scalar tm=state.THs(h,p-dp,T), tp=state.THs(h,p+dp,T);
            const scalar hm=state.Hs(p-dp,tm)-h, hp=state.Hs(p+dp,tp)-h;
            const scalar ft=(state.rho(p+dp,T)-state.rho(p-dp,T))/(2*dp);
            const scalar fh=(state.rho(p+dp,tp)-state.rho(p-dp,tm))/(2*dp);
            const scalar et=mag(ft-betaT)/max(scalar(1e-30),mag(betaT));
            const scalar eh=mag(fh-betaH)/max(scalar(1e-30),mag(betaH));
            const scalar caloricScale=max(scalar(1),mag(T*Cp));
            const bool rowPassed=std::isfinite(ft+fh+betaH+Cp+Cv+hm+hp)
                && betaH>0 && Cp>0 && Cv>0 && et<2e-3 && eh<2e-3
                && cpError<2e-3 && max(mag(hm),mag(hp))/caloricScale<=1e-8;
            passed = passed && rowPassed;
            output << p << ',' << T << ',' << step << ',' << rho << ',' << Cp
                << ',' << Cv << ',' << alpha << ',' << betaT << ',' << betaH
                << ',' << ft << ',' << fh << ',' << et << ',' << eh << ','
                << cpFD << ',' << cpError << ',' << tm << ',' << tp << ','
                << hm << ',' << hp << ',' << rowPassed << '\n';
        }
    }
    output.close();
    return output && passed ? 0 : 3;
}
}
