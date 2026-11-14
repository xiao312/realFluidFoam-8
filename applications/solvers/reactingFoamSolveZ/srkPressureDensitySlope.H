#ifndef srkPressureDensitySlope_H
#define srkPressureDensitySlope_H
#include "forSRKchungTakaGases.H"
#include "SRKchungTakaMixture.H"
#include <cmath>

namespace Foam
{
typedef chungTakaTransport<species::thermo<rfJanafThermo<
    soaveRedlichKwong<rfSpecie>>, sensibleEnthalpy>> PressureSlopeThermo;
typedef SRKchungTakaMixture<PressureSlopeThermo> PressureSlopeMixture;

// Fixed-T,Y derivative of p=R*T*rho/(1-b*rho)-a*rho^2/(1+b*rho).
// Parameters and selected root come from the executing mixture; no critical
// properties or phase branch are reconstructed here.
inline scalar srkIsothermalDensitySlope
(
    const PressureSlopeThermo& model, const scalar p, const scalar T
)
{
    const scalar density=model.rho(p,T), W=model.W(), b=model.bM()/W;
    const scalar attraction=(model.coef1()-model.coef2()*std::sqrt(T)
        +model.coef3()*T)/(W*W);
    const scalar derivative=model.R()*T/sqr(1-b*density)
        -attraction*density*(2+b*density)/sqr(1+b*density);
    if (!(p>0 && T>0 && density>0 && 1-b*density>0 && derivative>0)
        || !std::isfinite(derivative))
        FatalErrorInFunction << "Invalid SRK differential pressure state: p=" << p
            << " T=" << T << " rho=" << density << " dpdrho=" << derivative
            << exit(FatalError);
    return 1/derivative;
}

inline void updateSrkPressureDensitySlope
(
    const psiReactionThermo& thermo, volScalarField& slope
)
{
    const PressureSlopeMixture* mixture=
        dynamic_cast<const PressureSlopeMixture*>(&thermo.composition());
    if (!mixture)
        FatalErrorInFunction << "Differential pressure mode requires exact sensible-enthalpy SRK Chung mixture"
            << exit(FatalError);
    forAll(slope, celli)
        slope[celli]=srkIsothermalDensitySlope(mixture->cellMixture(celli),
            thermo.p()[celli],thermo.T()[celli]);
    forAll(slope.boundaryField(), patchi)
        forAll(slope.boundaryField()[patchi], facei)
            slope.boundaryFieldRef()[patchi][facei]=srkIsothermalDensitySlope
            (
                mixture->patchFaceMixture(patchi,facei),
                thermo.p().boundaryField()[patchi][facei],
                thermo.T().boundaryField()[patchi][facei]
            );
}
}
#endif
