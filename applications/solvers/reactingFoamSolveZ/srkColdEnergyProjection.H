#ifndef srkColdEnergyProjection_H
#define srkColdEnergyProjection_H
#include "srkPressureDensitySlope.H"

namespace Foam
{
// Same executing-coefficient algebra used by the separately qualified contact
// double-flux application. This does not change the library's cubic root policy.
inline scalar coldContactTemperatureAtDensity
(
    const PressureSlopeThermo& model, scalar rho, scalar p, scalar guess
)
{
    const scalar W=model.W(),b=model.bM()/W;
    if (!(rho>0 && p>0 && 1-b*rho>0))
        FatalErrorInFunction << "Invalid cold projection density/pressure: rho="
            << rho << " p=" << p << exit(FatalError);
    const scalar factor=rho*rho/(W*W*(1+b*rho));
    const scalar a=model.R()*rho/(1-b*rho)-factor*model.coef3();
    const scalar d=factor*model.coef2(),c=-factor*model.coef1()-p;
    const scalar discriminant=d*d-4*a*c;
    if (!(discriminant>=0) || !std::isfinite(discriminant))
        FatalErrorInFunction << "No real cold SRK temperature: rho=" << rho
            << " p=" << p << exit(FatalError);
    const scalar q=-.5*(d+std::copysign(std::sqrt(discriminant),d));
    const scalar roots[2]={q/a,c/q};
    scalar chosen=-1,distance=GREAT;
    for (const scalar root:roots) if (root>0 && std::isfinite(root))
    {
        const scalar candidate=root*root,error=mag(candidate-guess);
        if (error<distance) { chosen=candidate;distance=error; }
    }
    if (!(chosen>0) || model.limit(chosen)!=chosen)
        FatalErrorInFunction << "Cold projection outside declared range: rho="
            << rho << " p=" << p << " T=" << chosen << exit(FatalError);
    return chosen;
}

inline void applySrkColdEnergyProjection
(
    psiReactionThermo& thermo, const volScalarField& rho
)
{
    const Time& time=rho.mesh().time();
    if (!time.controlDict().lookupOrDefault<Switch>("realFluidColdEnergyProjection",false)) return;
    const PressureSlopeMixture* mixture=
        dynamic_cast<const PressureSlopeMixture*>(&thermo.composition());
    if (!mixture || thermo.he().name()!="h")
        FatalErrorInFunction << "Cold projection requires sensible-enthalpy SRK Chung mixture"
            << exit(FatalError);
    scalar signedJ=0,absoluteJ=0,maxDeltaH=0; label changed=0;
    forAll(rho,celli)
    {
        const PressureSlopeThermo& point=mixture->cellMixture(celli);
        const scalar pressure=thermo.p()[celli],density=rho[celli];
        const scalar targetT=coldContactTemperatureAtDensity(point,density,pressure,thermo.T()[celli]);
        const scalar compressibility=pressure/(density*point.R()*targetT);
        if (compressibility>=.9) continue;
        const scalar error=mag(point.rho(pressure,targetT)-density)/density;
        if (!std::isfinite(error) || error>1e-8)
            FatalErrorInFunction << "Cold projection selected-root mismatch=" << error
                << " cell=" << celli << " rho=" << density << " p=" << pressure
                << " T=" << targetT << exit(FatalError);
        const scalar targetH=point.Hs(pressure,targetT);
        const scalar deltaH=targetH-thermo.he()[celli];
        if (!std::isfinite(targetH))
            FatalErrorInFunction << "Nonfinite cold projected enthalpy" << exit(FatalError);
        const scalar defect=density*deltaH*rho.mesh().V()[celli];
        signedJ+=defect;absoluteJ+=mag(defect);maxDeltaH=max(maxDeltaH,mag(deltaH));++changed;
        thermo.he()[celli]=targetH;
        thermo.T()[celli]=targetT;
    }
    reduce(signedJ,sumOp<scalar>());reduce(absoluteJ,sumOp<scalar>());
    reduce(maxDeltaH,maxOp<scalar>());reduce(changed,sumOp<label>());
    Info<< "coldEnergyProjection t=" << time.value() << " cells=" << changed
        << " thresholdZ=0.9 appliedSigned_J=" << signedJ << " appliedAbsolute_J=" << absoluteJ
        << " maxDeltaH_J_kg=" << maxDeltaH
        << " budgetScope=eachEquationApplication cumulativePhysicalBalance=0" << endl;
}
}
#endif
