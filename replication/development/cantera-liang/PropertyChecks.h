#pragma once
#include "cantera/base/Solution.h"
#include "cantera/kinetics/Kinetics.h"
#include <fstream>
#include <iomanip>
inline void propertyChecks(const std::shared_ptr<Cantera::Solution>& sol,
                          const std::string& output) {
    auto gas=sol->thermo();std::vector<double> x(gas->nSpecies()),h(x.size()),rates(x.size()),diff(x.size());
    gas->getMoleFractions(x.data());
    std::ofstream csv(output);csv<<std::setprecision(16)<<"T_K,rho,cp,cp_finite_difference,h_euler_error,lambda,D_CH4\n";
    for(double T:{298.,900.,1800.,2115.,2400.}) {
        gas->setState_TPX(T,10132500,x.data());
        double cp=gas->cp_mole(),hmix=gas->enthalpy_mole(),rho=gas->density();
        gas->getPartialMolarEnthalpies(h.data());
        double sum=0;for(size_t k=0;k<x.size();k++)sum+=x[k]*h[k];
        double step=T*1e-5;
        gas->setState_TP(T+step,10132500);double hi=gas->enthalpy_mole();
        gas->setState_TP(T-step,10132500);double lo=gas->enthalpy_mole();
        gas->setState_TP(T,10132500);double numeric=(hi-lo)/(2*step);
        if(std::abs(cp-numeric)>1e-5*std::max(1.,std::abs(cp)) || std::abs(sum-hmix)>1e-9*std::max(1.,std::abs(hmix)))
            throw std::runtime_error("Cantera callback cp/enthalpy identity failed");
        sol->transport()->getMixDiffCoeffs(diff.data());double lambda=sol->transport()->thermalConductivity();
        if(!(lambda>0 && std::isfinite(lambda)))throw std::runtime_error("Invalid conductivity");
        for(auto d:diff)if(!(d>0 && std::isfinite(d)))throw std::runtime_error("Invalid diffusion");
        sol->kinetics()->getNetProductionRates(rates.data());
        for(auto rate:rates)if(!std::isfinite(rate))throw std::runtime_error("Invalid reaction rate");
        csv<<T<<','<<rho<<','<<cp<<','<<numeric<<','<<sum-hmix<<','<<lambda<<','<<diff[gas->speciesIndex("CH4")]<<'\n';
    }
    gas->setState_TPX(298,10132500,x.data());
}
