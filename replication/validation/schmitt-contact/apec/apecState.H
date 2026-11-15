#ifndef contactAPECState_H
#define contactAPECState_H
#include "../double-flux/contactState.H"
namespace ContactAPEC
{
using namespace ContactDF;
inline scalar pressureAtDensity(const Thermo& model,scalar rho,scalar T)
{
    const scalar W=model.W(),b=model.bM()/W;
    const scalar a=(model.coef1()-model.coef2()*std::sqrt(T)+model.coef3()*T)/(W*W);
    return model.R()*rho*T/(1-b*rho)-a*rho*rho/(1+b*rho);
}
// d(rho e)/d rho at fixed p = h - rho Cp (dp/drho)_T/(dp/dT)_rho.
// Formation enthalpy is included by actual Ha; pure O2 has no composition jump.
inline scalar pressureEnergyDerivative(const Thermo& model,const Primitive& v)
{
    const scalar W=model.W(),b=model.bM()/W,rho=v.rho,T=v.T;
    const scalar a=(model.coef1()-model.coef2()*std::sqrt(T)+model.coef3()*T)/(W*W);
    const scalar aT=(-model.coef2()/(2*std::sqrt(T))+model.coef3())/(W*W);
    const scalar pr=model.R()*T/Foam::sqr(1-b*rho)-a*rho*(2+b*rho)/Foam::sqr(1+b*rho);
    const scalar pt=model.R()*rho/(1-b*rho)-aT*rho*rho/(1+b*rho);
    if(!std::isfinite(pt)||pt<=0)FatalErrorInFunction<<"Invalid APEC pressure derivative"<<Foam::exit(Foam::FatalError);
    return v.absoluteH-rho*model.Cp(v.p,T)*pr/pt;
}
inline unsigned& recoverySeedSearches()
{
    static unsigned count=0;
    return count;
}
inline Primitive recover(const Thermo& model,const Conserved& c,scalar guess)
{
    if(!(c.rho>0)||!std::isfinite(c.rho+c.momentum+c.energy))
        FatalErrorInFunction<<"Invalid conservative APEC state"<<Foam::exit(Foam::FatalError);
    const scalar u=c.momentum/c.rho,target=c.energy/c.rho-.5*u*u;
    auto query=[&](scalar T,scalar& p,scalar& e)->bool
    {
        if(!(T>0)||!std::isfinite(T)||model.limit(T)!=T)return false;
        p=pressureAtDensity(model,c.rho,T);
        if(!(p>0)||!std::isfinite(p))return false;
        const scalar rhoEOS=model.rho(p,T);
        if(!std::isfinite(rhoEOS)||Foam::mag(rhoEOS-c.rho)/c.rho>1e-8)return false;
        e=model.Ha(p,T)-p/c.rho;
        return std::isfinite(e);
    };
    scalar T=guess,p=0,e=0;
    if(!query(T,p,e))
    {
        // A valid previous-stage T need not be admissible at the new rho.
        // Find a feasible Newton seed; never change rho, energy or acceptance.
        ++recoverySeedSearches();
        bool found=false;scalar best=Foam::GREAT;
        for(unsigned k=1;k<=48;++k)for(int sign=-1;sign<=1;sign+=2)
        {
            const scalar trial=guess*std::exp(sign*.05*k);scalar tp=0,te=0;
            if(query(trial,tp,te)&&Foam::mag(te-target)<best)
            {T=trial;p=tp;e=te;best=Foam::mag(te-target);found=true;}
        }
        if(!found)FatalErrorInFunction<<"No admissible APEC rho/e Newton seed; rho="<<c.rho
            <<" target_e="<<target<<Foam::exit(Foam::FatalError);
    }
    for(unsigned iteration=0;iteration<80;++iteration)
    {
        const scalar residual=e-target,scale=Foam::max(scalar(1),Foam::max(Foam::mag(e),Foam::mag(target)));
        if(Foam::mag(residual)<=1e-11*scale)
            return physicalState(model,c.rho,u,p,T,{{0,1}});
        const scalar cv=model.Cv(p,T);
        if(!(cv>0)||!std::isfinite(cv))break;
        bool accepted=false;
        for(unsigned backtrack=0;backtrack<24;++backtrack)
        {
            const scalar trial=T-std::ldexp(residual/cv,-int(backtrack));scalar tp=0,te=0;
            if(query(trial,tp,te)&&Foam::mag(te-target)<Foam::mag(residual))
            {T=trial;p=tp;e=te;accepted=true;break;}
        }
        if(!accepted)break;
    }
    FatalErrorInFunction<<"APEC rho/e recovery did not converge; rho="<<c.rho
        <<" target_e="<<target<<" T="<<T<<" p="<<p<<" residual="<<e-target
        <<Foam::exit(Foam::FatalError);
    return Primitive();
}
}
#endif
