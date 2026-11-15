#ifndef contactAPECFlux_H
#define contactAPECFlux_H
#include "apecState.H"
namespace ContactAPEC
{
struct FaceFlux
{
    scalar mass=0,momentum=0,leftEnergy=0,rightEnergy=0;
    std::array<scalar,2> species{{0,0}};
};
struct Evaluation
{
    std::vector<Conserved> cells;
    std::vector<FaceFlux> faces;
    scalar boundaryMass=0,boundaryMomentum=0,boundaryEnergy=0,internalEnergyDefect=0;
};
// One-dimensional adaptation of Trixi flux_terashima_etal (see NOTICE.md).
inline FaceFlux faceFlux(const Thermo& model,const Primitive& l,const Primitive& r)
{
    const scalar rho=.5*(l.rho+r.rho),u=.5*(l.u+r.u),p=.5*(l.p+r.p);
    const scalar rhoe=.5*(l.rho*l.absoluteH-l.p+r.rho*r.absoluteH-r.p)
        -.25*(pressureEnergyDerivative(model,r)-pressureEnergyDerivative(model,l))*(r.rho-l.rho);
    FaceFlux f;f.mass=rho*u;f.momentum=f.mass*u+p;
    f.leftEnergy=(rhoe+.5*rho*l.u*r.u)*u+.5*(l.p*r.u+r.p*l.u);
    f.rightEnergy=f.leftEnergy;f.species[0]=0;f.species[1]=f.mass;
    return f;
}
inline Evaluation evaluate(const std::vector<Primitive>& state,const std::vector<Primitive>&,
    const Primitive& leftFar,const Primitive& rightFar,scalar dx,scalar area,
    const Thermo& model)
{
    const unsigned n=state.size();Evaluation e;e.cells.resize(n);e.faces.resize(n+1);
    for(unsigned face=0;face<=n;++face)
    {
        const Primitive& l=face?state[face-1]:(state[0].u>=0?leftFar:state[0]);
        const Primitive& r=face<n?state[face]:(state[n-1].u<=0?rightFar:state[n-1]);
        e.faces[face]=faceFlux(model,l,r);
    }
    for(unsigned i=0;i<n;++i)
    {
        const FaceFlux& l=e.faces[i];const FaceFlux& r=e.faces[i+1];Conserved& c=e.cells[i];
        c.rho=(l.mass-r.mass)/dx;c.momentum=(l.momentum-r.momentum)/dx;
        c.energy=(l.rightEnergy-r.leftEnergy)/dx;c.species[0]=0;c.species[1]=c.rho;
    }
    e.boundaryMass=area*(e.faces.front().mass-e.faces.back().mass);
    e.boundaryMomentum=area*(e.faces.front().momentum-e.faces.back().momentum);
    e.boundaryEnergy=area*(e.faces.front().rightEnergy-e.faces.back().leftEnergy);
    return e;
}
}
#endif
