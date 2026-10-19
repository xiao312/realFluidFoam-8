#pragma once
#include "cantera/thermo/ThermoPhase.h"
#include <fstream>
#include <iomanip>
// A thermodynamic equilibrium diagnostic, separate from concentration-law kinetics
// and separate from the flame's ideal-profile numerical initial guess.
inline void equilibriumCheck(Cantera::ThermoPhase& gas,const std::string& output) {
    std::vector<double> x(gas.nSpecies());gas.getMoleFractions(x.data());
    const double T=gas.temperature(),p=gas.pressure(),h=gas.enthalpy_mass();
    std::vector<double> elements(gas.nElements());
    for(size_t m=0;m<elements.size();m++)elements[m]=gas.elementalMassFraction(m);
    std::ofstream file(output);file<<std::setprecision(16);
    gas.equilibrate("HP","vcs",1e-10,5000,1000,0,0);
    double herr=std::abs(gas.enthalpy_mass()-h)/std::max(1.,std::abs(h)),elementError=0;
    for(size_t m=0;m<elements.size();m++)elementError=std::max(elementError,std::abs(elements[m]-gas.elementalMassFraction(m)));
    if(herr>1e-7 || elementError>1e-9)throw std::runtime_error("HP equilibrium conservation failed");
    file<<"T_K,rho_kg_m3,h_J_kg,h_relative_error,element_mass_error";
    for(size_t k=0;k<x.size();k++)file<<",X_"<<gas.speciesName(k);
    file<<'\n'<<gas.temperature()<<','<<gas.density()<<','<<gas.enthalpy_mass()<<','<<herr<<','<<elementError;
    for(size_t k=0;k<x.size();k++)file<<','<<gas.moleFraction(k);file<<'\n';
    gas.setState_TPX(T,p,x.data());
}
