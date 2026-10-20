#include "../cantera-liang/SrkPhase.h"
#include "../cantera-liang/PressureChemistry.h"
#include "cantera/thermo/ThermoFactory.h"
#include <fstream>
#include <iostream>

// At fixed T,Y, actual-concentration chemistry must equal an ideal phase at
// p/Z, including third bodies and falloff. The pressure adapter must instead
// equal the ideal phase at physical p without changing the SRK density.
int main(int argc,char** argv) {
try {
    if(argc!=2)throw std::runtime_error("Usage: test-chemistry INPUT");
    const std::string input=argv[1];
    Cantera::ThermoFactory::factory()->reg("liang-srk",[](){return new liang::SrkPhase;});
    auto real=Cantera::newSolution(input+"/srk.yaml","","none");
    auto ideal=Cantera::newSolution(input+"/ideal.yaml","","none");
    auto* phase=dynamic_cast<liang::SrkPhase*>(real->thermo().get());
    if(!phase)throw std::runtime_error("Expected SRK phase");
    std::ifstream table(input+"/species.txt");
    std::string name;liang::Species row;
    while(table>>name>>row.Tc>>row.Pc>>row.Vc>>row.W>>row.omega>>row.eos)
        phase->parameters.push_back(row);
    if(phase->parameters.size()!=real->thermo()->nSpecies())
        throw std::runtime_error("Species table mismatch");
    phase->stage=3;
    auto original=real->kinetics();
    const size_t count=phase->nSpecies();
    std::vector<double> y(count),fresh(count),a(count),b(count);
    double largestError=0,lawSeparation=0;
    for(double phi:{1.,1.4}) {
        ideal->thermo()->setEquivalenceRatio(phi,"H2","O2:0.21,N2:0.79");
        ideal->thermo()->setState_TP(298.,100*Cantera::OneAtm);
        ideal->thermo()->getMassFractions(fresh.data());
        ideal->thermo()->equilibrate("HP");
        ideal->thermo()->getMassFractions(y.data());
        for(size_t k=0;k<count;k++)y[k]=.5*(y[k]+fresh[k]);
        for(double temperature:{900.,1500.,2200.}) {
            const double pressure=100*Cantera::OneAtm;
            phase->setState_TPY(temperature,pressure,y.data());
            const double density=phase->density();
            const double equivalentPressure=phase->molarDensity()
                *Cantera::GasConstant*temperature;
            real->setKinetics(original);
            original->getNetProductionRates(a.data());
            ideal->thermo()->setState_TPY(temperature,equivalentPressure,y.data());
            ideal->kinetics()->getNetProductionRates(b.data());
            double scale=1e-30;
            for(double v:b)scale=std::max(scale,std::abs(v));
            for(size_t k=0;k<count;k++)
                largestError=std::max(largestError,std::abs(a[k]-b[k])/scale);
            liang::usePressureChemistry(real,input+"/ideal.yaml");
            real->kinetics()->getNetProductionRates(a.data());
            for(size_t k=0;k<count;k++)
                lawSeparation=std::max(lawSeparation,std::abs(a[k]-b[k])/scale);
            ideal->thermo()->setState_TPY(temperature,pressure,y.data());
            ideal->kinetics()->getNetProductionRates(b.data());
            scale=1e-30;
            for(double v:b)scale=std::max(scale,std::abs(v));
            for(size_t k=0;k<count;k++)
                largestError=std::max(largestError,std::abs(a[k]-b[k])/scale);
            if(std::abs(phase->density()/density-1)>1e-13)
                throw std::runtime_error("Chemistry changed physical density");
        }
    }
    std::cout<<"six_states_max_relative_error "<<largestError
             <<"\nmaximum_law_separation "<<lawSeparation<<std::endl;
    if(largestError>1e-9 || lawSeparation<1e-3)
        throw std::runtime_error("Chemistry law control failed");
} catch(const std::exception& error) {std::cerr<<error.what()<<std::endl;return 1;}
}
