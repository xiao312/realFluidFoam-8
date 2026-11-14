#ifndef contactReconstruction_H
#define contactReconstruction_H
#include "contactState.H"

namespace ContactDF
{
// Uniform-grid MC slope. Zero slopes retain first-order treatment at boundaries.
inline scalar mcSlope(const scalar left,const scalar center,const scalar right)
{
    const scalar a=2*(center-left),b=.5*(right-left),c=2*(right-center);
    if(a>0 && b>0 && c>0)return Foam::min(a,Foam::min(b,c));
    if(a<0 && b<0 && c<0)return Foam::max(a,Foam::max(b,c));
    return 0;
}

inline Primitive reconstructFace
(
    const std::vector<Primitive>& state,const unsigned cell,const scalar side
)
{
    Primitive face=state[cell];
    if(cell==0 || cell+1==state.size())return face;
    const Primitive& l=state[cell-1];
    const Primitive& c=state[cell];
    const Primitive& r=state[cell+1];
    face.rho+=side*.5*mcSlope(l.rho,c.rho,r.rho);
    face.u+=side*.5*mcSlope(l.u,c.u,r.u);
    face.p+=side*.5*mcSlope(l.p,c.p,r.p);
    face.sound+=side*.5*mcSlope(l.sound,c.sound,r.sound);
    face.species[0]+=side*.5*mcSlope(l.species[0],c.species[0],r.species[0]);
    face.species[1]=1-face.species[0];
    if(!(face.rho>0 && face.p>0 && face.sound>0))
        FatalErrorInFunction<<"Invalid limited-linear face state"<<Foam::exit(Foam::FatalError);
    return face;
}
}
#endif
