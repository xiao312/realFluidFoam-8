#include "bridge.h"
#include "../cantera-liang/StagedTransport.h"
#include "../cantera-liang/DiagnosticOptions.h"
#include "../cantera-liang/PressureChemistry.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/zeroD/ConstPressureReactor.h"
#include "cantera/zeroD/ReactorNet.h"
#include <cstring>
#include <filesystem>
#include <fstream>
#include <memory>
#include <mutex>

struct rf_ct_context {
    std::shared_ptr<Cantera::Solution> solution;
    std::shared_ptr<Cantera::ConstPressureReactor> reactor;
    std::shared_ptr<Cantera::ReactorNet> network;
    bool supportsConstantPressureIntegration=false;
    std::string error;
};
namespace {
void message(char* buffer,size_t capacity,const std::string& text) {
    if(buffer && capacity) {
        size_t count=std::min(capacity-1,text.size());
        std::memcpy(buffer,text.data(),count);buffer[count]='\0';
    }
}
void validate(double temperature,double pressure,const double* y,size_t n,size_t expected) {
    if(!y || n!=expected || !std::isfinite(temperature) || !std::isfinite(pressure)
       || temperature<=0 || pressure<=0)throw std::runtime_error("Invalid TPY state or species count");
    double sum=0;
    for(size_t k=0;k<n;k++) {
        if(!std::isfinite(y[k]) || y[k]<-1e-9)throw std::runtime_error("Invalid mass fraction");
        sum+=y[k];
    }
    if(std::abs(sum-1)>1e-8)throw std::runtime_error("Mass fractions do not sum to one");
}
}
extern "C" rf_ct_context* rf_ct_create(const char* inputs,int stage,const char* text,
                                        char* error,size_t capacity) {
    try {
        if(!inputs || !text || stage<1 || stage>5)throw std::runtime_error("Invalid model configuration");
        liang::DiagnosticOptions options(text);
        if(options.fineGrid)throw std::runtime_error("fine-grid is not a property model option");
        std::filesystem::path directory=std::filesystem::canonical(inputs);
        std::ifstream table(directory/"species.txt");
        std::vector<liang::Species> parameters;std::vector<std::string> names;
        std::string name;liang::Species row;
        while(table>>name>>row.Tc>>row.Pc>>row.Vc>>row.W>>row.omega>>row.eos) {
            names.push_back(name);parameters.push_back(row);
        }
        if(parameters.size()!=53)throw std::runtime_error("Expected 53 explicit species rows");
        static std::once_flag registered;
        std::call_once(registered,[](){Cantera::ThermoFactory::factory()->reg("liang-srk",[](){
            auto* gas=new liang::SrkPhase;gas->stage=1;return gas;});});
        auto context=std::make_unique<rf_ct_context>();
        auto solution=Cantera::newSolution((directory/(stage==1?"ideal.yaml":"srk.yaml")).string(),
                                          "",stage==1?"mixture-averaged":"none");
        auto gas=solution->thermo();
        if(gas->speciesNames()!=names)throw std::runtime_error("Species ordering differs from model table");
        if(auto* model=dynamic_cast<liang::SrkPhase*>(gas.get())) {
            model->smoothedAlpha=options.smoothedAlpha;model->parameters=parameters;model->stage=stage;
            model->setState_TP(298,10132500);
            auto transport=std::make_shared<liang::StagedTransport>();
            transport->parameters=parameters;transport->stage=stage;
            transport->smoothedAlpha=options.smoothedAlpha;transport->table2=options.table2;
            transport->denseIncrementOnly=options.dense;transport->boundedTakahashi=options.bounded;
            transport->init(gas.get());solution->setTransport(transport);
        }
        if(options.pressureChemistry)liang::usePressureChemistry(solution,(directory/"ideal.yaml").string());
        context->supportsConstantPressureIntegration=stage<3 || options.smoothedAlpha;
        context->solution=solution;message(error,capacity,"");return context.release();
    }catch(const std::exception& e){message(error,capacity,e.what());}
    catch(...){message(error,capacity,"Unknown bridge initialization error");}
    return nullptr;
}
extern "C" void rf_ct_destroy(rf_ct_context* context) {delete context;}
extern "C" size_t rf_ct_species_count(const rf_ct_context* context) {
    return context?context->solution->thermo()->nSpecies():0;
}
extern "C" const char* rf_ct_error(const rf_ct_context* context) {
    return context?context->error.c_str():"Null Cantera bridge context";
}
extern "C" int rf_ct_species_name(rf_ct_context* context,size_t index,char* name,size_t capacity) {
    if(!context)return 1;
    try {
        if(index>=rf_ct_species_count(context))throw std::runtime_error("Species index out of range");
        auto value=context->solution->thermo()->speciesName(index);
        if(!name || capacity<=value.size())throw std::runtime_error("Species-name buffer too small");
        message(name,capacity,value);context->error.clear();return 0;
    }catch(const std::exception& e){context->error=e.what();return 1;}
    catch(...){context->error="Unknown species-name error";return 1;}
}
extern "C" int rf_ct_evaluate(rf_ct_context* context,double temperature,double pressure,
                               const double* y,size_t n,rf_ct_properties* properties,
                               double* enthalpies,double* diffusion,double* sources) {
    if(!context)return 1;
    try {
        validate(temperature,pressure,y,n,rf_ct_species_count(context));
        if(!properties || !diffusion)throw std::runtime_error("Null required output buffer");
        auto gas=context->solution->thermo();auto transport=context->solution->transport();
        gas->setTemperature(temperature);gas->setMassFractions_NoNorm(y);gas->setPressure(pressure);
        *properties={gas->density(),gas->enthalpy_mass(),gas->cp_mass(),transport->thermalConductivity(),
                     transport->viscosity(),gas->meanMolecularWeight()};
        if(enthalpies)gas->getPartialMolarEnthalpies(enthalpies);
        transport->getMixDiffCoeffs(diffusion);
        if(sources)context->solution->kinetics()->getNetProductionRates(sources);
        for(size_t k=0;k<n;k++) {
            if(enthalpies)enthalpies[k]/=gas->molecularWeight(k);
            if(sources)sources[k]*=gas->molecularWeight(k);
            if((enthalpies && !std::isfinite(enthalpies[k])) || (sources && !std::isfinite(sources[k]))
               || !std::isfinite(diffusion[k]) || !(diffusion[k]>0))
                throw std::runtime_error("Nonfinite species property or nonpositive diffusivity");
        }
        if(!(properties->density>0 && properties->cp>0 && properties->conductivity>0 && properties->viscosity>0)
           || !std::isfinite(properties->enthalpy) || !std::isfinite(properties->density)
           || !std::isfinite(properties->cp) || !std::isfinite(properties->conductivity)
           || !std::isfinite(properties->viscosity))throw std::runtime_error("Invalid mixture property");
        context->error.clear();return 0;
    }catch(const std::exception& e){context->error=e.what();return 1;}
    catch(...){context->error="Unknown state-evaluation error";return 1;}
}

extern "C" int rf_ct_advance_cp(rf_ct_context* context,double temperature,double pressure,
                                 const double* y,size_t n,double duration,
                                 double relativeTolerance,double absoluteTolerance,
                                 double* finalTemperature,double* finalY) {
    if(!context)return 1;
    try {
        validate(temperature,pressure,y,n,rf_ct_species_count(context));
        if(!context->supportsConstantPressureIntegration)
            throw std::runtime_error("Departure calorics require smoothed-alpha for CP integration");
        if(!finalTemperature || !finalY || !std::isfinite(duration) || duration<=0
           || !std::isfinite(relativeTolerance) || relativeTolerance<=0 || relativeTolerance>1e-3
           || !std::isfinite(absoluteTolerance) || absoluteTolerance<=0 || absoluteTolerance>1e-6)
            throw std::runtime_error("Invalid reactor outputs, duration or tolerances");
        auto gas=context->solution->thermo();
        gas->setTemperature(temperature);gas->setMassFractions_NoNorm(y);gas->setPressure(pressure);
        if(!context->reactor) {
            context->reactor=std::make_shared<Cantera::ConstPressureReactor>(context->solution,false);
            context->network=std::make_shared<Cantera::ReactorNet>(context->reactor);
        }
        context->reactor->setInitialVolume(1.0);
        context->reactor->syncState();
        context->network->setTolerances(relativeTolerance,absoluteTolerance);
        context->network->setMaxSteps(20000);
        context->network->setInitialTime(0.0);
        context->network->advance(duration);
        *finalTemperature=gas->temperature();gas->getMassFractions(finalY);
        if(std::abs(gas->pressure()/pressure-1)>1e-10)
            throw std::runtime_error("Constant-pressure reactor pressure drift");
        validate(*finalTemperature,pressure,finalY,n,n);
        context->error.clear();return 0;
    }catch(const std::exception& e){context->error=e.what();}
    catch(...){context->error="Unknown constant-pressure integration error";}
    context->network.reset();context->reactor.reset();return 1;
}
