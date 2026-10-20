#include "../cantera-liang/SrkPhase.h"
#include "cantera/base/Solution.h"
#include "cantera/kinetics/Kinetics.h"
#include "cantera/thermo/ThermoFactory.h"
#include <fstream>
#include <iostream>

int main(int argc,char** argv) {
try {
    using namespace Cantera;
    if(argc!=2)throw std::runtime_error("Usage: test-activity INPUT");
    const std::string input=argv[1];
    ThermoFactory::factory()->reg("liang-srk",[](){return new liang::SrkPhase;});
    auto real=newSolution(input+"/srk.yaml","","none");
    auto ideal=newSolution(input+"/ideal.yaml","","none");
    auto* gas=dynamic_cast<liang::SrkPhase*>(real->thermo().get());
    if(!gas)throw std::runtime_error("Expected SRK phase");
    std::ifstream table(input+"/species.txt");std::string name;liang::Species row;
    while(table>>name>>row.Tc>>row.Pc>>row.Vc>>row.W>>row.omega>>row.eos) {
        if(name!=gas->speciesName(gas->parameters.size()))
            throw std::runtime_error("Species order mismatch");
        gas->parameters.push_back(row);
    }
    if(gas->parameters.size()!=gas->nSpecies())throw std::runtime_error("Missing parameters");
    gas->stage=3;
    auto kinetics=real->kinetics();
    const size_t n=gas->nSpecies(),nr=kinetics->nReactions();
    std::vector<double> y(n),fresh(n),x(n),f(nr),r(nr),fa(nr),ra(nr);
    double largest=0,balance=0,elementError=0;
    for(double phi:{1.,1.4}) {
        ideal->thermo()->setEquivalenceRatio(phi,"H2","O2:0.21,N2:0.79");
        ideal->thermo()->setState_TP(298.,100*OneAtm);
        ideal->thermo()->getMassFractions(fresh.data());
        ideal->thermo()->equilibrate("HP");
        ideal->thermo()->getMassFractions(y.data());
        for(size_t k=0;k<n;k++)y[k]=.5*(y[k]+fresh[k]);
        for(double temperature:{900.,1500.,2200.}) {
            gas->setState_TPY(temperature,100*OneAtm,y.data());
            const double density=gas->density(),pressure=gas->pressure();
            gas->fugacityKinetics=false;kinetics->invalidateCache();
            kinetics->getFwdRatesOfProgress(f.data());kinetics->getRevRatesOfProgress(r.data());
            const auto state=gas->state();
            const double z=pressure*state.v/(GasConstant*temperature);
            gas->fugacityKinetics=true;kinetics->invalidateCache();
            kinetics->getFwdRatesOfProgress(fa.data());kinetics->getRevRatesOfProgress(ra.data());
            for(size_t j=0;j<nr;j++) {
                double forward=1,reverse=1;
                for(size_t k=0;k<n;k++) {
                    const double factor=z*std::exp(state.lnphi[k]);
                    forward*=std::pow(factor,kinetics->reactantStoichCoeff(k,j));
                    reverse*=std::pow(factor,kinetics->productStoichCoeff(k,j));
                }
                for(auto values:{std::pair<double,double>{fa[j],f[j]*forward},
                                 std::pair<double,double>{ra[j],r[j]*reverse}}) {
                    const double scale=std::max({std::abs(values.first),std::abs(values.second),1e-250});
                    largest=std::max(largest,std::abs(values.first-values.second)/scale);
                }
            }
            if(gas->density()!=density || std::abs(gas->pressure()/pressure-1)>1e-13)
                throw std::runtime_error("Activity switch changed physical state");
        }
        gas->setState_TPY(2200.,100*OneAtm,fresh.data());
        std::vector<double> elements(gas->nElements());
        for(size_t m=0;m<elements.size();m++)elements[m]=gas->elementalMassFraction(m);
        gas->equilibrate("TP","vcs",1e-11,5000,1000,0,0);
        for(size_t m=0;m<elements.size();m++)
            elementError=std::max(elementError,std::abs(elements[m]-gas->elementalMassFraction(m)));
        kinetics->getFwdRatesOfProgress(fa.data());kinetics->getRevRatesOfProgress(ra.data());
        double scale=1e-250;
        for(size_t j=0;j<nr;j++)scale=std::max({scale,std::abs(fa[j]),std::abs(ra[j])});
        for(size_t j=0;j<nr;j++)balance=std::max(balance,std::abs(fa[j]-ra[j])/scale);
    }
    std::cout<<"six_states_activity_relative_error "<<largest
             <<"\nequilibrium_detailed_balance_scaled "<<balance
             <<"\nelemental_mass_fraction_error "<<elementError<<std::endl;
    if(largest>1e-9 || balance>1e-7 || elementError>1e-9)
        throw std::runtime_error("Activity law or equilibrium check failed");
} catch(const std::exception& error) {std::cerr<<error.what()<<std::endl;return 1;}
}
