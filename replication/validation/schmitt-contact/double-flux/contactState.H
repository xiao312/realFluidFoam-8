#ifndef contactState_H
#define contactState_H
#include "forSRKchungTakaGases.H"
#include "SRKchungTakaMixture.H"
#include <array>
#include <vector>
#include <cmath>

namespace ContactDF
{
using Foam::scalar;
typedef Foam::chungTakaTransport<Foam::species::thermo<Foam::rfJanafThermo<
    Foam::soaveRedlichKwong<Foam::rfSpecie>>,Foam::sensibleEnthalpy>> Thermo;
typedef Foam::SRKchungTakaMixture<Thermo> Mixture;

struct Conserved
{
    scalar rho=0,momentum=0,energy=0;
    std::array<scalar,2> species{{0,0}};
};
struct Primitive
{
    scalar rho=0,u=0,p=0,T=0,sound=0,gamma=0,e0=0,absoluteH=0;
    std::array<scalar,2> species{{0,0}};
};
inline Conserved combine(const Conserved& a,const Conserved& b,scalar x,scalar y)
{
    Conserved c;c.rho=x*a.rho+y*b.rho;c.momentum=x*a.momentum+y*b.momentum;
    c.energy=x*a.energy+y*b.energy;
    for(unsigned k=0;k<2;++k)c.species[k]=x*a.species[k]+y*b.species[k];
    return c;
}

// Algebraic inversion of this library's SRK a(T)=c1-c2*sqrt(T)+c3*T.
// No coefficient is reconstructed from an independent critical-property model.
inline scalar temperatureAtDensity(const Thermo& model,scalar rho,scalar p,scalar guess)
{
    const scalar W=model.W(),b=model.bM()/W;
    if(!(rho>0&&p>0&&1-b*rho>0))
        FatalErrorInFunction<<"Invalid SRK pressure/density projection"<<Foam::exit(Foam::FatalError);
    const scalar factor=rho*rho/(W*W*(1+b*rho));
    const scalar a=model.R()*rho/(1-b*rho)-factor*model.coef3();
    const scalar d=factor*model.coef2(),c=-factor*model.coef1()-p;
    const scalar discriminant=d*d-4*a*c;
    if(!(discriminant>=0)||!std::isfinite(discriminant))
        FatalErrorInFunction<<"No real SRK temperature at transported density"<<Foam::exit(Foam::FatalError);
    const scalar q=-.5*(d+std::copysign(std::sqrt(discriminant),d));
    const scalar roots[2]={q/a,c/q};
    scalar chosen=-1,distance=Foam::GREAT;
    for(const scalar root:roots)if(root>0&&std::isfinite(root))
    {
        const scalar candidate=root*root,error=Foam::mag(candidate-guess);
        if(error<distance){chosen=candidate;distance=error;}
    }
    if(!(chosen>0)||model.limit(chosen)!=chosen)
        FatalErrorInFunction<<"SRK temperature projection outside declared thermo range"<<Foam::exit(Foam::FatalError);
    return chosen;
}

inline Primitive physicalState(const Thermo& model,scalar rho,scalar u,scalar p,scalar T,
    const std::array<scalar,2>& fractions)
{
    Primitive v;v.rho=rho;v.u=u;v.p=p;v.T=T;v.species=fractions;
    const scalar discrepancy=Foam::mag(model.rho(p,T)-rho)/rho;
    if(!std::isfinite(discrepancy)||discrepancy>1e-8)
        FatalErrorInFunction<<"Transport/EOS root mismatch="<<discrepancy
            <<" p="<<p<<" T="<<T<<" rho="<<rho<<Foam::exit(Foam::FatalError);
    const scalar W=model.W(),b=model.bM()/W;
    const scalar attraction=(model.coef1()-model.coef2()*std::sqrt(T)+model.coef3()*T)/(W*W);
    const scalar derivative=model.R()*T/Foam::sqr(1-b*rho)
        -attraction*rho*(2+b*rho)/Foam::sqr(1+b*rho);
    const scalar cp=model.Cp(p,T),cv=model.Cv(p,T),soundSquared=cp/cv*derivative;
    if(!(soundSquared>0&&cp>0&&cv>0)||!std::isfinite(soundSquared))
        FatalErrorInFunction<<"Non-hyperbolic actual SRK state"<<Foam::exit(Foam::FatalError);
    v.sound=std::sqrt(soundSquared);v.gamma=rho*soundSquared/p;
    if(!std::isfinite(v.gamma)||!(v.gamma>0)||Foam::mag(v.gamma-1)<1e-10)
        FatalErrorInFunction<<"Degenerate double-flux thermodynamic tangent"<<Foam::exit(Foam::FatalError);
    v.absoluteH=model.Ha(p,T);
    v.e0=v.absoluteH-p/rho-p/(rho*(v.gamma-1));
    return v;
}
}
#endif
