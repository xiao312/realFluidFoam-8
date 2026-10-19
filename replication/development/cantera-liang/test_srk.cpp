#include "SrkKernel.h"
#include <iostream>
void check(double a,double b,double tol,const char* label) {
    if(std::abs(a-b)>tol*std::max({1.,std::abs(a),std::abs(b)}))
        throw std::runtime_error(label);
}
int main() {
    std::vector<liang::Species> s={{190.56,4.5992e6,.0986,16.04,.011},
        {154.58,5.043e6,.0734,32,.022},{126.2,3.3958e6,.0895,28,.0372}};
    std::vector<double> x={.1,.2,.7};
    for(double T:{298.,500.,1000.,1800.,2500.}) for(double p:{1e3,101325.,10132500.}) {
        auto z=liang::evaluate(T,p,x,s);
        check(p,liang::R*T/(z.v-z.b)-z.a/(z.v*(z.v+z.b)),1e-10,"pressure root");
        double dt=T*1e-5;
        auto hi=liang::evaluate(T+dt,p,x,s),lo=liang::evaluate(T-dt,p,x,s);
        check(z.cp,(hi.h-lo.h)/(2*dt),2e-6,"cp derivative");
        double hs=0,vs=0,gs=0;
        for(size_t k=0;k<x.size();k++) {
            hs+=x[k]*z.hb[k];vs+=x[k]*z.vb[k];gs+=x[k]*z.lnphi[k]*liang::R*T;
            check(z.hb[k],-liang::R*T*T*(hi.lnphi[k]-lo.lnphi[k])/(2*dt),3e-6,"Gibbs Helmholtz");
            auto xp=x,xm=x;double dx=1e-5;
            xp[k]+=dx;xm[k]-=dx;
            for(size_t j=0;j<x.size();j++){xp[j]/=1+dx;xm[j]/=1-dx;}
            auto a=liang::evaluate(T,p,xp,s),b=liang::evaluate(T,p,xm,s);
            check(z.hb[k],z.h+(a.h-b.h)/(2*dx),3e-6,"partial enthalpy");
        }
        check(hs,z.h,1e-10,"enthalpy Euler");check(vs,z.v,1e-10,"volume Euler");
        check(gs,z.h-T*z.s,1e-8,"Gibbs Euler");
    }
    std::cout<<"SRK pressure, cp, partial enthalpy, volume and fugacity checks passed\n";
}
