#ifndef srkRhoHaRecovery_H
#define srkRhoHaRecovery_H
#include "srkPressureDensitySlope.H"

namespace Foam
{
struct SrkDensityProperties
{
    scalar pressure, absoluteEnthalpy, cv, dHaDT, dPDRho;
};

// Existing SRK/caloric model expressed with density as an independent variable.
// The positive reference pressure is used only to cancel EOS departure from Ha.
inline SrkDensityProperties srkPropertiesAtDensity
(
    const PressureSlopeThermo& model, scalar rho, scalar T, scalar referencePressure
)
{
    const scalar W=model.W(), RR=model.R()*W, b=model.bM(), v=W/rho;
    const scalar a=model.coef1()-model.coef2()*std::sqrt(T)+model.coef3()*T;
    const scalar da=-model.coef2()/(2*std::sqrt(T))+model.coef3();
    const scalar d2a=model.coef2()/(4*std::pow(T,scalar(1.5)));
    const scalar logarithm=std::log1p(b/v);
    const scalar idealHa=model.Ha(referencePressure,T)-model.H(referencePressure,T);
    const scalar pressure=RR*T/(v-b)-a/(v*(v+b));
    const scalar internalEnergy=idealHa-model.R()*T+(T*da-a)*logarithm/(b*W);
    const scalar cv=model.CpIdeal(referencePressure,T)-model.R()
        +T*d2a*logarithm/(b*W);
    const scalar dPDT=RR/(v-b)-da/(v*(v+b));
    const scalar dPDV=-RR*T/sqr(v-b)+a*(2*v+b)/(sqr(v)*sqr(v+b));
    return {pressure,internalEnergy+pressure/rho,cv,cv+dPDT/rho,-W*dPDV/sqr(rho)};
}

struct SrkRhoHaRecovery
{
    scalar temperature=0,pressure=0,enthalpyError=GREAT;
    scalar selectedDensityRelativeError=GREAT,selectedEnthalpyRelativeError=GREAT;
    scalar cv=0,isothermalSlope=0;
    label iterations=0;
    bool caloricConverged=false,mechanicallyStable=false,selectedRootMatches=false;
    word reason="invalidInput";
    bool passed() const
    {
        return caloricConverged && mechanicallyStable && selectedRootMatches;
    }
};

inline SrkRhoHaRecovery recoverSrkDensityEnthalpy
(
    const PressureSlopeThermo& model, scalar rho, scalar targetHa,
    scalar referencePressure, scalar guess
)
{
    SrkRhoHaRecovery result;
    if (!std::isfinite(rho+targetHa+referencePressure+guess)
        || !(rho>0 && referencePressure>0 && guess>0)
        || !(model.bM()>0 && model.W()/rho>model.bM())) return result;
    scalar low=model.limit(60), high=model.limit(6000);
    if (!(low>0 && high>low && guess>=low && guess<=high)) return result;
    const scalar fLow=srkPropertiesAtDensity(model,rho,low,referencePressure).absoluteEnthalpy-targetHa;
    const scalar fHigh=srkPropertiesAtDensity(model,rho,high,referencePressure).absoluteEnthalpy-targetHa;
    if (!std::isfinite(fLow+fHigh) || fLow>0 || fHigh<0)
    {
        result.reason="unbracketed";return result;
    }
    scalar T=guess;
    for (label iteration=0;iteration<100;++iteration)
    {
        const SrkDensityProperties state=srkPropertiesAtDensity(model,rho,T,referencePressure);
        const scalar residual=state.absoluteEnthalpy-targetHa;
        result.iterations=iteration+1;result.temperature=T;result.pressure=state.pressure;
        result.enthalpyError=residual;result.cv=state.cv;result.isothermalSlope=state.dPDRho;
        if (!std::isfinite(residual+state.pressure+state.cv+state.dHaDT+state.dPDRho))
        {
            result.reason="nonfiniteState";return result;
        }
        const scalar scale=max(scalar(1),max(mag(targetHa),mag(state.absoluteEnthalpy)));
        if (mag(residual)<=1e-11*scale)
        {
            result.caloricConverged=true;break;
        }
        if (residual>0) high=T;else low=T;
        const scalar candidate=T-residual/state.dHaDT;
        T=state.dHaDT>0 && std::isfinite(candidate) && candidate>low && candidate<high
            ? candidate : (low+high)/2;
    }
    if (!result.caloricConverged) {result.reason="iterationCeiling";return result;}
    result.mechanicallyStable=result.pressure>0 && result.cv>0 && result.isothermalSlope>0;
    if (!result.mechanicallyStable) {result.reason="unstableState";return result;}
    const scalar selectedRho=model.rho(result.pressure,result.temperature);
    const scalar selectedHa=model.Ha(result.pressure,result.temperature);
    result.selectedDensityRelativeError=mag(selectedRho-rho)/rho;
    result.selectedEnthalpyRelativeError=mag(selectedHa-targetHa)
        /max(scalar(1),max(mag(targetHa),mag(selectedHa)));
    result.selectedRootMatches=std::isfinite(selectedRho+selectedHa)
        && result.selectedDensityRelativeError<=1e-8 && result.selectedEnthalpyRelativeError<=1e-8;
    result.reason=result.selectedRootMatches ? "converged" : "selectedRootMismatch";
    return result;
}
}
#endif
