#include "SrkKernel.h"
#include <iostream>
int main(int argc,char**) {
    bool smooth=argc==1; // An extra argument replays the failing legacy control.
    std::vector<liang::Species> species={{190.56,4.5992e6,.0986,16.04,.011},
        {154.58,5.043e6,.0734,32,.022},{126.2,3.3958e6,.0895,28,.0372}};
    std::vector<double> x={.1,.2,.7};
    for(const auto& s:species) {
        double m=.48+1.574*s.omega-.176*s.omega*s.omega;
        double T=s.Tc*std::pow(1+1/m,2),dt=1e-6;
        auto lo=liang::evaluate(T-dt,10132500,x,species,smooth);
        auto hi=liang::evaluate(T+dt,10132500,x,species,smooth);
        double residual=hi.h-lo.h-dt*(hi.cp+lo.cp);
        std::cout<<"crossing_K="<<T<<" enthalpy_integrability_residual_J_kmol="<<residual<<'\n';
        if(std::abs(residual)>.1)return 1;
    }
}
