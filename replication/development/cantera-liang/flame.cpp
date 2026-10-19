#include "StagedTransport.h"
#include "DiagnosticOptions.h"
#include "PressureChemistry.h"
#include "PropertyChecks.h"
#include "EquilibriumCheck.h"
#include "cantera/onedim.h"
#include "cantera/oneD/DomainFactory.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/transport/TransportFactory.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
using namespace Cantera;
namespace fs=std::filesystem;
std::vector<std::string> split(const std::string& line) {
    std::stringstream in(line);std::string part;std::vector<std::string> out;
    while(std::getline(in,part,',')) {
        if(!part.empty() && part.back()=='\r')part.pop_back();
        out.push_back(part);
    }
    return out;
}
int main(int argc,char** argv) {
try {
    if(argc<5 || argc>7)throw std::runtime_error("Usage: liang-flame INPUTS CASE PHI NEW_OUTPUT [OPTIONS] [PRESSURE_ATM]");
    std::string variant=argc>=6?argv[5]:"full";
    liang::DiagnosticOptions options(variant);
    double pressure=(argc==7?std::stod(argv[6]):100.)*101325.;
    if(!std::isfinite(pressure) || pressure<101325 || pressure>10132500)throw std::runtime_error("Pressure must be 1--100 atm");
    fs::path input=argv[1],output=argv[4];int stage=std::stoi(argv[2]);double phi=std::stod(argv[3]);
    if(stage<1 || stage>5 || !(phi>0) || fs::exists(output))throw std::runtime_error("Invalid stage/phi or existing output");
    std::ifstream table(input/"species.txt");std::vector<liang::Species> parameters;
    std::vector<std::string> species;std::string name;liang::Species row;
    while(table>>name>>row.Tc>>row.Pc>>row.Vc>>row.W>>row.omega>>row.eos) {parameters.push_back(row);species.push_back(name);}
    if(parameters.size()!=53)throw std::runtime_error("Expected 53 explicit species rows");
    ThermoFactory::factory()->reg("liang-srk",[&](){
        // Cantera queries pressure before all species have been installed.
        // Load reference thermo first; activate SRK only on the complete phase.
        auto* gas=new liang::SrkPhase;gas->stage=1;return gas;});
    TransportFactory::factory()->reg("liang-staged",[&](){
        auto* tr=new liang::StagedTransport;tr->stage=stage;tr->parameters=parameters;
        tr->highTemperature=options.highTemperature;
        tr->table2=options.table2;tr->smoothedAlpha=options.smoothedAlpha;tr->denseIncrementOnly=options.dense;tr->boundedTakahashi=options.bounded;return tr;});
    auto sol=newSolution((input/(stage==1?"ideal.yaml":"srk.yaml")).string(),"",stage==1?"mixture-averaged":"liang-staged");
    auto gas=sol->thermo();
    for(size_t k=0;k<species.size();k++) if(gas->speciesName(k)!=species[k])throw std::runtime_error("Species order mismatch");
    if(auto* model=dynamic_cast<liang::SrkPhase*>(gas.get())) {
        model->smoothedAlpha=options.smoothedAlpha;model->parameters=parameters;model->stage=stage;model->setState_TP(298,pressure);
    }
    gas->setEquivalenceRatio(phi,"CH4","O2:0.21,N2:0.79");gas->setState_TP(298,pressure);
    if(options.pressureChemistry)liang::usePressureChemistry(sol,(input/"ideal.yaml").string());
    fs::create_directories(output);
    std::ofstream(output/"pressure-Pa.txt")<<std::setprecision(16)<<pressure<<'\n';
    std::ofstream(output/"model-variant.txt")<<variant<<'\n';
    propertyChecks(sol,(output/"property-checks.csv").string(),pressure);
    if(stage!=2)equilibriumCheck(*gas,(output/"equilibrium.csv").string());
    std::vector<double> xin(gas->nSpecies());gas->getMoleFractions(xin.data());double rho=gas->density();
    std::ifstream file(input/"guess.csv");std::string line;std::getline(file,line);auto columns=split(line);
    std::vector<std::vector<double>> values(columns.size());
    while(std::getline(file,line)) {auto fields=split(line);if(fields.size()!=columns.size())throw std::runtime_error("CSV width");
        for(size_t k=0;k<fields.size();k++)values[k].push_back(std::stod(fields[k]));}
    if(values[0].size()<10 || columns[0]!="x_m")throw std::runtime_error("Invalid initial profile");
    auto flow=newDomain<Flow1D>("gas-flow",sol,"flow");flow->setFreeFlow();flow->setPressure(pressure);
    flow->setupGrid(values[0].size(),values[0].data());flow->setSteadyTolerances(1e-5,1e-11);
    flow->setFluxGradientBasis(ThermoBasis::molar);flow->enableSoret(false);
    auto inlet=newDomain<Inlet1D>("inlet",sol);inlet->setTemperature(298);inlet->setMoleFractions(xin.data());
    inlet->setMdot(rho*values[2][0]);auto outlet=newDomain<Outlet1D>("outlet",sol);
    std::vector<std::shared_ptr<Domain1D>> domains{inlet,flow,outlet};
    Sim1D flame(domains);flame.setMaxGridPoints(1,6000);
    auto loc=values[0];for(auto& x:loc)x=(x-values[0][0])/(values[0].back()-values[0][0]);
    flow->setProfile("T",loc,values[1]);flow->setProfile("velocity",loc,values[2]);
    for(size_t k=5;k<columns.size();k++)flow->setProfile(columns[k],loc,values[k]);
    flame.setFixedTemperature(298+.3*(values[1].back()-298));flow->setEnergyEnabled(true);
    std::ofstream results(output/"refinement.csv");results<<"stage,phi,slope,curve,points,speed_cm_s\n"<<std::setprecision(16);
    std::vector<std::pair<double,double>> levels{{.0075,.0125},{.00375,.00625}};
    if(options.fineGrid)levels.push_back({.001875,.003125});
    for(auto level:levels) {
        flow->setRefineCriteria(3,level.first,level.second,0);flame.solve(1,true);
        results<<stage<<','<<phi<<','<<level.first<<','<<level.second<<','<<flow->nPoints()<<','<<100*flow->values("velocity")[0]<<'\n';results.flush();
    }
    // Save numerical fields explicitly; custom factories must also be registered on reload.
    flame.save((output/"flame.yaml").string(),"flame","Staged SRK, concentration-law kinetics",true);
    auto grid=flow->grid(),T=flow->values("T"),u=flow->values("velocity");
    std::vector<std::vector<double>> ys;for(auto& n:species)ys.push_back(flow->values(n));
    std::ofstream csv(output/"profile.csv");csv<<std::setprecision(16)<<"x_m,T_K,U_m_s,rho_kg_m3,h_J_kg,cp_J_kgK,lambda_W_mK";
    for(auto& n:species)csv<<",Y_"<<n;csv<<'\n';
    std::vector<double> y(species.size());
    for(size_t j=0;j<grid.size();j++) {
        for(size_t k=0;k<y.size();k++)y[k]=ys[k][j];gas->setState_TPY(T[j],pressure,y.data());
        csv<<grid[j]<<','<<T[j]<<','<<u[j]<<','<<gas->density()<<','<<gas->enthalpy_mass()<<','<<gas->cp_mass()<<','<<sol->transport()->thermalConductivity();
        for(auto v:y)csv<<','<<v;csv<<'\n';
    }
    std::ofstream counters(output/"callbacks.txt");
    if(auto* g=dynamic_cast<liang::SrkPhase*>(gas.get()))counters<<"eos "<<g->eosCalls<<" cp "<<g->cpCalls<<" partial_enthalpy "<<g->partialCalls<<'\n';
    if(auto* t=dynamic_cast<liang::StagedTransport*>(sol->transport().get()))counters<<"conductivity "<<t->conductivityCalls<<" diffusion "<<t->diffusionCalls<<" negative_partial_volume_calls "<<t->negativePartialVolumeCalls<<" bounded_pair_calls "<<t->boundedPairCalls<<" projected_composition_calls "<<t->projectedCompositionCalls<<'\n';
    if(auto* k=dynamic_cast<liang::PressureChemistry*>(sol->kinetics().get()))counters<<"pressure_chemistry_calls "<<k->calls<<'\n';
    std::cout<<"COMPLETED stage="<<stage<<" phi="<<phi<<" speed_cm_s="<<100*u[0]<<std::endl;
} catch(const std::exception& e) {std::cerr<<e.what()<<std::endl;return 1;}
}
