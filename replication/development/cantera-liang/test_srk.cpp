#include "SrkKernel.h"
#include "../liang-properties/ElyHanley.H"
#include <iostream>
void check(double a,double b,double tol,const char* label) {
    if(std::abs(a-b)>tol*std::max({1.,std::abs(a),std::abs(b)}))
        throw std::runtime_error(std::string(label)+" analytical="+std::to_string(a)+" numerical="+std::to_string(b));
}
int main() {
    auto shape=rfElyHanley::shape(298.,-.01,{647.1,22.064e6,.056,18.015,.344,4.});
    if(!(shape.f>0 && shape.h>0))throw std::runtime_error("signed partial-volume shape");
    double lambda=rfElyHanley::conductivity(1800.,1.,{{33.18,1.3e6,.064935,2.016,-.216,2.5-2e-8}}, {1.},{1.});
    if(!(lambda>0))throw std::runtime_error("NASA-fit internal heat capacity tolerance");
    lambda=rfElyHanley::conductivity(2115.,1.,{{126.2,3.4e6,.09,14.007,0,2.498637672358062}}, {1.},{1.});
    if(!(lambda>0))throw std::runtime_error("atomic-N NASA-fit correction");
    std::vector<liang::Species> s={{190.56,4.5992e6,.0986,16.04,.011},
        {154.58,5.043e6,.0734,32,.022},{126.2,3.3958e6,.0895,28,.0372}};
    std::vector<double> x={.1,.2,.7};
    for(int alpha:{0,1,2}) for(double T:{298.,500.,1000.,1800.,2500.}) for(double p:{1e3,101325.,10132500.}) {
        const bool smooth=alpha==1,signedAlpha=alpha==2;
        std::cout<<"T="<<T<<" p="<<p<<std::endl;
        auto z=liang::evaluate(T,p,x,s,smooth,signedAlpha);
        check(p,liang::R*T/(z.v-z.b)-z.a/(z.v*(z.v+z.b)),1e-10,"pressure root");
        double dt=T*1e-5;
        auto hi=liang::evaluate(T+dt,p,x,s,smooth,signedAlpha),lo=liang::evaluate(T-dt,p,x,s,smooth,signedAlpha);
        check(z.cp,(hi.h-lo.h)/(2*dt),2e-6,"cp derivative");
        double hs=0,vs=0,gs=0;
        for(size_t k=0;k<x.size();k++) {
            hs+=x[k]*z.hb[k];vs+=x[k]*z.vb[k];gs+=x[k]*z.lnphi[k]*liang::R*T;
            check(z.hb[k],-liang::R*T*T*(hi.lnphi[k]-lo.lnphi[k])/(2*dt),3e-6,"Gibbs Helmholtz");
            auto xp=x,xm=x;double dx=1e-5;
            xp[k]+=dx;xm[k]-=dx;
            for(size_t j=0;j<x.size();j++){xp[j]/=1+dx;xm[j]/=1-dx;}
            auto a=liang::evaluate(T,p,xp,s,smooth,signedAlpha),b=liang::evaluate(T,p,xm,s,smooth,signedAlpha);
            check(z.hb[k],z.h+(a.h-b.h)/(2*dx),3e-6,"partial enthalpy");
            double gibbsDuhem=0;
            for(size_t j=0;j<x.size();j++)
                gibbsDuhem+=x[j]*(a.lnphi[j]-b.lnphi[j])/(2*dx);
            check(gibbsDuhem,0,1e-8,"constant-TP Gibbs-Duhem");
        }
        check(hs,z.h,1e-10,"enthalpy Euler");check(vs,z.v,1e-10,"volume Euler");
        check(gs,z.h-T*z.s,1e-8,"Gibbs Euler");
    }
    std::cout<<"SRK pressure, cp, partial enthalpy, volume, fugacity and Gibbs-Duhem checks passed\n";
}
