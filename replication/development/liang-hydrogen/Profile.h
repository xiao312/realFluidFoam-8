#pragma once
#include "cantera/onedim.h"
#include "../cantera-liang/StagedTransport.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace hydrogen {
struct Profile {
    std::vector<double> x,T,u;
    std::vector<std::vector<double>> y;
};
inline Profile initialGuess(const std::shared_ptr<Cantera::Solution>& ideal,
                            double phi,double Tu,double pressure,double width) {
    auto gas=ideal->thermo();const size_t n=gas->nSpecies();
    gas->setEquivalenceRatio(phi,"H2","O2:0.21,N2:0.79");gas->setState_TP(Tu,pressure);
    std::vector<double> yu(n),yb(n);gas->getMassFractions(yu.data());
    const double rho=gas->density();
    gas->equilibrate("HP");gas->getMassFractions(yb.data());
    const double Tb=gas->temperature(),ub=.6*rho/gas->density();
    Profile a;a.y.resize(n);
    // Resolved piecewise initial transition; adaptive refinement selects the
    // physical thickness. This is a steady numerical guess, not CFD startup.
    for(size_t j=0;j<21;j++) {
        const double x=double(j)/20;
        const double q=std::clamp((x-.3)/.2,0.,1.);
        a.x.push_back(width*x);a.T.push_back(Tu+q*(Tb-Tu));
        a.u.push_back(.6+q*(ub-.6));
        for(size_t k=0;k<n;k++)a.y[k].push_back(yu[k]+q*(yb[k]-yu[k]));
    }
    gas->setState_TPY(Tu,pressure,yu.data());return a;
}
inline Profile readGuess(const std::filesystem::path& file,size_t n) {
    std::ifstream stream(file);if(!stream)throw std::runtime_error("Missing guess");
    std::string line;std::getline(stream,line);
    Profile a;a.y.resize(n);
    while(std::getline(stream,line)) {
        std::stringstream row(line);std::string part;std::vector<double> v;
        while(std::getline(row,part,','))v.push_back(std::stod(part));
        if(v.size()!=7+n)throw std::runtime_error("Guess profile width mismatch");
        a.x.push_back(v[0]);a.T.push_back(v[1]);a.u.push_back(v[2]);
        for(size_t k=0;k<n;k++)a.y[k].push_back(v[7+k]);
    }
    if(a.x.size()<10)throw std::runtime_error("Guess has too few points");
    return a;
}
inline void writeProfiles(const std::filesystem::path& out,
                          const std::shared_ptr<Cantera::Flow1D>& flow,
                          const std::shared_ptr<Cantera::Solution>& sol,
                          const std::shared_ptr<Cantera::Solution>& ideal,
                          const std::shared_ptr<Cantera::Solution>& real,double pressure) {
    auto gas=sol->thermo();const size_t n=gas->nSpecies();
    auto x=flow->grid(),T=flow->values("T"),u=flow->values("velocity");
    std::vector<std::vector<double>> ys;
    for(auto& name:gas->speciesNames())ys.push_back(flow->values(name));
    std::ofstream csv(out/"profile.csv"),tr(out/"transport.csv");
    csv<<std::setprecision(16)<<"x_m,T_K,U_m_s,rho_kg_m3,h_J_kg,cp_J_kgK,lambda_W_mK";
    for(auto& name:gas->speciesNames())csv<<",Y_"<<name;csv<<'\n';
    tr<<std::setprecision(16)<<"x_m,T_K,lambda_ideal_over_real,Dmix_H2_real_over_ideal,Dmix_O2_real_over_ideal,Dmix_N2_real_over_ideal,Dbin_H2_N2_real_over_ideal,Dbin_H2_O2_real_over_ideal\n";
    std::vector<double> y(n),d0(n),d1(n),b0(n*n),b1(n*n);
    const size_t h=gas->speciesIndex("H2"),o=gas->speciesIndex("O2"),nit=gas->speciesIndex("N2");
    for(size_t j=0;j<x.size();j++) {
        for(size_t k=0;k<n;k++)y[k]=ys[k][j];
        gas->setState_TPY(T[j],pressure,y.data());
        csv<<x[j]<<','<<T[j]<<','<<u[j]<<','<<gas->density()<<','<<gas->enthalpy_mass()
           <<','<<gas->cp_mass()<<','<<sol->transport()->thermalConductivity();
        for(auto v:y)csv<<','<<v;csv<<'\n';
        ideal->thermo()->setState_TPY(T[j],pressure,y.data());
        real->thermo()->setState_TPY(T[j],pressure,y.data());
        ideal->transport()->getMixDiffCoeffs(d0.data());real->transport()->getMixDiffCoeffs(d1.data());
        ideal->transport()->getBinaryDiffCoeffs(n,b0.data());real->transport()->getBinaryDiffCoeffs(n,b1.data());
        tr<<x[j]<<','<<T[j]<<','<<ideal->transport()->thermalConductivity()/real->transport()->thermalConductivity()
          <<','<<d1[h]/d0[h]<<','<<d1[o]/d0[o]<<','<<d1[nit]/d0[nit]
          <<','<<b1[h+n*nit]/b0[h+n*nit]<<','<<b1[h+n*o]/b0[h+n*o]<<'\n';
    }
}
}
