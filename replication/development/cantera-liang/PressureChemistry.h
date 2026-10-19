#pragma once
#include "cantera/base/Solution.h"
#include "cantera/kinetics/BulkKinetics.h"
#include "cantera/thermo/ThermoPhase.h"
namespace liang {
// Diagnostic source adapter for Flow1D (which calls getNetProductionRates only).
// A separate ideal phase handles ALL mass-action, third-body and falloff terms.
// Never alter the SRK phase density to imitate ideal chemistry.
class PressureChemistry : public Cantera::BulkKinetics {
public:
    std::shared_ptr<Cantera::Solution> ideal;
    size_t calls=0;
    void getNetProductionRates(double* rates) override {
        std::vector<double> y(thermo().nSpecies());thermo().getMassFractions(y.data());
        ideal->thermo()->setTemperature(thermo().temperature());
        ideal->thermo()->setMassFractions_NoNorm(y.data());
        ideal->thermo()->setPressure(thermo().pressure());
        ideal->kinetics()->getNetProductionRates(rates);calls++;
    }
};
inline void usePressureChemistry(const std::shared_ptr<Cantera::Solution>& sol,
                                 const std::string& idealFile) {
    auto adapter=std::make_shared<PressureChemistry>();
    adapter->ideal=Cantera::newSolution(idealFile,"","none");
    if(adapter->ideal->thermo()->speciesNames()!=sol->thermo()->speciesNames())
        throw std::runtime_error("Pressure chemistry species order mismatch");
    adapter->addThermo(sol->thermo());adapter->init();
    auto original=sol->kinetics();
    for(size_t i=0;i<original->nReactions();i++)adapter->addReaction(original->reaction(i));
    sol->setKinetics(adapter);
}
}
