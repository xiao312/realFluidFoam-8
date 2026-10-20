// Independent polynomial expansion and thermodynamic checks across signed roots.
#include "SrkKernel.h"
#include <iostream>

void check(double a,double b,double tol,const char* label) {
    if(!std::isfinite(a) || !std::isfinite(b)
       || std::abs(a-b)>tol*std::max({1.,std::abs(a),std::abs(b)}))
        throw std::runtime_error(label);
}

int main() {
    const std::vector<liang::Species> species={
        {33.18,1.3e6,.064935,2.016,-.216},
        {154.58,5.043e6,.0734,32,.022},
        {126.2,3.3958e6,.0895,28,.0372},
        {647.1,22.064e6,.056,18.015,.344}};
    size_t states=0,negativeRoots=0;
    for(const auto& x:std::vector<std::vector<double>>{
            {.3,.1,.6,0},{.1,0,.7,.2},{0,0,1,0},{0,0,0,1}}) {
        double intercept=0,slope=0;
        std::vector<double> crossings;
        for(size_t k=0;k<species.size();k++) {
            const auto& s=species[k];
            const double m=.48+1.574*s.omega-.176*s.omega*s.omega;
            const double c=std::sqrt(.42747)*liang::R*s.Tc/std::sqrt(s.Pc);
            intercept+=x[k]*c*(1+m);
            slope+=x[k]*c*m/std::sqrt(s.Tc);
            crossings.push_back(s.Tc*std::pow(1+1/m,2));
        }
        const double rootTemperature=std::pow(intercept/slope,2);
        std::vector<double> temperatures={298,1000,1500,2400,3500,
            rootTemperature-1e-3,rootTemperature,rootTemperature+1e-3};
        temperatures.insert(temperatures.end(),crossings.begin(),crossings.end());
        for(double T:temperatures) {
            const auto z=liang::evaluate(T,10132500,x,species,false,true);
            const double q=intercept-slope*std::sqrt(T);
            if(q<0)negativeRoots++;
            // Evaluate the upstream COEF1 - COEF2 sqrt(T) + COEF3 T algebra.
            const double polynomial=intercept*intercept
                -2*intercept*slope*std::sqrt(T)+slope*slope*T;
            check(z.a/std::max(1.,intercept*intercept),
                  polynomial/std::max(1.,intercept*intercept),1e-12,"signed polynomial");
            const double dt=T*1e-5;
            const auto hi=liang::evaluate(T+dt,z.p,x,species,false,true);
            const auto lo=liang::evaluate(T-dt,z.p,x,species,false,true);
            check(z.cp,(hi.h-lo.h)/(2*dt),2e-6,"signed Cp derivative");
            double g=0;
            for(size_t k=0;k<x.size();k++) {
                check(z.hb[k],-liang::R*T*T*(hi.lnphi[k]-lo.lnphi[k])/(2*dt),
                      3e-6,"signed fugacity Gibbs Helmholtz");
                g+=x[k]*z.lnphi[k]*liang::R*T;
            }
            check(g,z.h-T*z.s,1e-8,"signed Gibbs Euler");
            for(const auto& s:species) {
                auto signedPure=liang::evaluate(T,z.p,{1},{s},false,true);
                auto absolutePure=liang::evaluate(T,z.p,{1},{s});
                check(signedPure.a,absolutePure.a,1e-12,"pure attraction parity");
                check(signedPure.h,absolutePure.h,1e-12,"pure enthalpy parity");
                check(signedPure.lnphi[0],absolutePure.lnphi[0],1e-12,"pure fugacity parity");
            }
            states++;
        }
        for(double T:crossings) {
            const double dt=1e-6;
            const auto hi=liang::evaluate(T+dt,10132500,x,species,false,true);
            const auto lo=liang::evaluate(T-dt,10132500,x,species,false,true);
            check(hi.h-lo.h,dt*(hi.cp+lo.cp),.1,"signed crossing integrability");
        }
    }
    if(negativeRoots==0)throw std::runtime_error("No negative mixture roots tested");
    std::cout<<"Signed-root states="<<states<<" negative_roots="<<negativeRoots
             <<"; polynomial, derivatives, fugacity, crossings and pure parity passed\n";
}
