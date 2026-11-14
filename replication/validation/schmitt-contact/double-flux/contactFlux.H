#ifndef contactFlux_H
#define contactFlux_H
#include "contactState.H"

// Double-flux energy localization follows Ma, Lv and Ihme (2017).
// See NOTICE.md. Mass/momentum share one physical-acoustic HLLC face flux.
namespace ContactDF
{
struct FaceFlux
{
    scalar mass=0,momentum=0,leftEnergy=0,rightEnergy=0;
    std::array<scalar,2> species{{0,0}};
};
struct Waves {scalar left,right,middle,pressure;};
inline Waves waveSpeeds(const Primitive& l,const Primitive& r)
{
    Waves w;w.left=Foam::min(l.u-l.sound,r.u-r.sound);
    w.right=Foam::max(l.u+l.sound,r.u+r.sound);
    const scalar denominator=l.rho*(w.left-l.u)-r.rho*(w.right-r.u);
    w.middle=(r.p-l.p+l.rho*l.u*(w.left-l.u)-r.rho*r.u*(w.right-r.u))/denominator;
    w.pressure=l.p+l.rho*(w.left-l.u)*(w.middle-l.u);
    return w;
}
inline scalar energyFlux(const Primitive& l,const Primitive& r,const Waves& w,scalar gamma,scalar e0)
{
    const scalar el=l.p/(gamma-1)+l.rho*(e0+.5*l.u*l.u);
    const scalar er=r.p/(gamma-1)+r.rho*(e0+.5*r.u*r.u);
    if(w.left>=0)return l.u*(el+l.p);
    if(w.right<=0)return r.u*(er+r.p);
    if(w.middle>=0)
    {
        const scalar star=((w.left-l.u)*el-l.p*l.u+w.pressure*w.middle)/(w.left-w.middle);
        return l.u*(el+l.p)+w.left*(star-el);
    }
    const scalar star=((w.right-r.u)*er-r.p*r.u+w.pressure*w.middle)/(w.right-w.middle);
    return r.u*(er+r.p)+w.right*(star-er);
}
inline FaceFlux faceFlux(const Primitive& l,const Primitive& r,
    scalar gammaLeft,scalar e0Left,scalar gammaRight,scalar e0Right)
{
    const Waves w=waveSpeeds(l,r);FaceFlux f;
    if(w.left>=0){f.mass=l.rho*l.u;f.momentum=l.rho*l.u*l.u+l.p;}
    else if(w.right<=0){f.mass=r.rho*r.u;f.momentum=r.rho*r.u*r.u+r.p;}
    else if(w.middle>=0)
    {
        const scalar star=l.rho*(w.left-l.u)/(w.left-w.middle);
        f.mass=l.rho*l.u+w.left*(star-l.rho);
        f.momentum=l.rho*l.u*l.u+l.p+w.left*(star*w.middle-l.rho*l.u);
    }
    else
    {
        const scalar star=r.rho*(w.right-r.u)/(w.right-w.middle);
        f.mass=r.rho*r.u+w.right*(star-r.rho);
        f.momentum=r.rho*r.u*r.u+r.p+w.right*(star*w.middle-r.rho*r.u);
    }
    f.leftEnergy=energyFlux(l,r,w,gammaLeft,e0Left);
    f.rightEnergy=energyFlux(l,r,w,gammaRight,e0Right);
    const auto& y=w.middle>=0?l.species:r.species;
    for(unsigned k=0;k<2;++k)f.species[k]=f.mass*y[k];
    return f;
}
struct Evaluation
{
    std::vector<Conserved> cells;
    std::vector<FaceFlux> faces;
    scalar boundaryMass=0,boundaryMomentum=0,boundaryEnergy=0,internalEnergyDefect=0;
};
inline Evaluation evaluate(const std::vector<Primitive>& state,const std::vector<Primitive>& frozen,
    const Primitive& leftFar,const Primitive& rightFar,scalar dx,scalar area)
{
    const unsigned n=state.size();Evaluation e;e.cells.resize(n);e.faces.resize(n+1);
    for(unsigned face=0;face<=n;++face)
    {
        const Primitive& l=face?state[face-1]:(state[0].u>=0?leftFar:state[0]);
        const Primitive& r=face<n?state[face]:(state[n-1].u<=0?rightFar:state[n-1]);
        const Primitive& fl=frozen[face?face-1:0];const Primitive& fr=frozen[face<n?face:n-1];
        e.faces[face]=faceFlux(l,r,fl.gamma,fl.e0,fr.gamma,fr.e0);
    }
    scalar energyRate=0;
    for(unsigned i=0;i<n;++i)
    {
        const FaceFlux& l=e.faces[i];const FaceFlux& r=e.faces[i+1];Conserved& c=e.cells[i];
        c.rho=(l.mass-r.mass)/dx;c.momentum=(l.momentum-r.momentum)/dx;
        c.energy=(l.rightEnergy-r.leftEnergy)/dx;
        for(unsigned k=0;k<2;++k)c.species[k]=(l.species[k]-r.species[k])/dx;
        energyRate+=c.energy*dx*area;
    }
    e.boundaryMass=area*(e.faces.front().mass-e.faces.back().mass);
    e.boundaryMomentum=area*(e.faces.front().momentum-e.faces.back().momentum);
    e.boundaryEnergy=area*(e.faces.front().rightEnergy-e.faces.back().leftEnergy);
    e.internalEnergyDefect=energyRate-e.boundaryEnergy;
    return e;
}
}
#endif
