#include "Profile.h"
#include "HydrogenTransport.h"
#include "../cantera-liang/PressureChemistry.h"
#include "../cantera-liang/TotalEnthalpyFlow.h"
#include "cantera/oneD/DomainFactory.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/transport/TransportFactory.h"
#include <iostream>
using namespace Cantera;
namespace fs=std::filesystem;

int main(int argc,char** argv) {
try {
    if(argc<5 || argc>8)throw std::runtime_error("Usage: flame INPUT CASE PHI NEW_OUTPUT [GUESS|-] [WIDTH_M] [TU_K]");
    fs::path input=argv[1],output=argv[4];std::string label=argv[2];
    const int stage=label=="3star"?3:std::stoi(label);
    const double phi=std::stod(argv[3]),pressure=100*OneAtm;
    const double width=argc>=7?std::stod(argv[6]):.01,Tu=argc>=8?std::stod(argv[7]):298.;
    if(stage<1 || stage>5 || !(phi>=.6 && phi<=3) || !(width>0 && width<=.1)
       || !(Tu>=280 && Tu<=350) || fs::exists(output))throw std::runtime_error("Invalid input or existing output");
    std::ifstream table(input/"species.txt");std::vector<liang::Species> parameters;
    std::vector<std::string> names;std::string name;liang::Species row;
    while(table>>name>>row.Tc>>row.Pc>>row.Vc>>row.W>>row.omega>>row.eos) {
        parameters.push_back(row);names.push_back(name);
    }
    if(names.size()!=13)throw std::runtime_error("Expected 13 Burke species");
    auto pairs=hydrogen::readPairs((input/"pairs.txt").string());
    ThermoFactory::factory()->reg("liang-srk",[](){auto* g=new liang::SrkPhase;g->stage=1;return g;});
    TransportFactory::factory()->reg("hydrogen-staged",[&](){
        auto* t=new hydrogen::Transport;t->pairs=pairs;t->parameters=parameters;t->stage=stage;
        t->denseIncrementOnly=true;t->boundedTakahashi=true;t->table2=true;return t;
    });
    TransportFactory::factory()->reg("hydrogen-full",[&](){
        auto* t=new hydrogen::Transport;t->pairs=pairs;t->parameters=parameters;t->stage=5;
        t->denseIncrementOnly=true;t->boundedTakahashi=true;t->table2=true;return t;
    });
    TransportFactory::factory()->reg("hydrogen-dilute",[&](){
        auto* t=new hydrogen::Transport;t->pairs=pairs;t->parameters=parameters;t->stage=1;return t;
    });
    auto activate=[&](std::shared_ptr<Solution> s,int modelStage) {
        if(auto* g=dynamic_cast<liang::SrkPhase*>(s->thermo().get())) {
            g->parameters=parameters;g->stage=modelStage;g->setState_TP(Tu,pressure);
        }
    };
    auto ideal=newSolution((input/"ideal.yaml").string(),"","hydrogen-dilute");
    if(ideal->kinetics()->nReactions()!=27)throw std::runtime_error("Expected 27 Burke reactions");
    for(size_t k=0;k<names.size();k++)
        if(ideal->thermo()->speciesName(k)!=names[k])throw std::runtime_error("Species order mismatch");
    auto guess=hydrogen::initialGuess(ideal,phi,Tu,pressure,width);
    if(argc>=6 && std::string(argv[5])!="-")guess=hydrogen::readGuess(argv[5],names.size());
    auto sol=newSolution((input/(stage==1?"ideal.yaml":"srk.yaml")).string(),"",
                         "hydrogen-staged");
    activate(sol,stage);auto gas=sol->thermo();
    gas->setEquivalenceRatio(phi,"H2","O2:0.21,N2:0.79");gas->setState_TP(Tu,pressure);
    if(stage>1)liang::usePressureChemistry(sol,(input/"ideal.yaml").string());
    std::vector<double> xin(names.size()),partial(names.size());
    gas->getMoleFractions(xin.data());const double rho=gas->density();
    fs::create_directories(output);
    std::ofstream config(output/"configuration.txt");
    config<<std::setprecision(16)<<"case "<<label<<"\nphi "<<phi<<"\npressure_Pa "<<pressure
          <<"\nTu_K "<<Tu<<"\nwidth_m "<<guess.x.back()-guess.x.front()
          <<"\nkinetics Burke2012-N2-pressure\ntransport author-pair-count "<<pairs.size()
          <<"\nconductivity dense-increment-diagnostic\nTakahashi bounded-Table2"
          <<"\nSoret off\nenergy "<<(stage>=3 && label!="3star"?"total-enthalpy":"temperature")<<'\n';
    std::ofstream checks(output/"property-checks.csv");
    checks<<"T_K,relative_cp_fd_error,relative_enthalpy_euler_error\n"<<std::setprecision(16);
    for(double T:{Tu,900.,1800.,2400.}) {
        gas->setState_TPX(T,pressure,xin.data());
        const double h=gas->enthalpy_mole(),cp=gas->cp_mole(),dt=T*1e-5;
        gas->getPartialMolarEnthalpies(partial.data());
        double sum=0;for(size_t k=0;k<names.size();k++)sum+=xin[k]*partial[k];
        gas->setState_TP(T+dt,pressure);const double hi=gas->enthalpy_mole();
        gas->setState_TP(T-dt,pressure);const double lo=gas->enthalpy_mole();
        const double ec=std::abs(cp-(hi-lo)/(2*dt))/std::max(1.,std::abs(cp));
        const double eh=std::abs(h-sum)/std::max(1.,std::abs(h));
        checks<<T<<','<<ec<<','<<eh<<'\n';
        if(ec>1e-5 || eh>1e-9)throw std::runtime_error("Thermo identity failed");
    }
    gas->setState_TPX(Tu,pressure,xin.data());
    std::shared_ptr<Flow1D> flow;
    if(stage>=3 && label!="3star")flow=std::make_shared<liang::TotalEnthalpyFlow>(sol,false);
    else flow=newDomain<Flow1D>("gas-flow",sol,"flow");
    flow->setFreeFlow();flow->setPressure(pressure);
    flow->setupGrid(guess.x.size(),guess.x.data());flow->setSteadyTolerances(1e-5,1e-11);
    flow->setFluxGradientBasis(ThermoBasis::molar);flow->enableSoret(false);
    auto inlet=newDomain<Inlet1D>("inlet",sol);inlet->setTemperature(Tu);
    inlet->setMoleFractions(xin.data());inlet->setMdot(rho*guess.u[0]);
    auto outlet=newDomain<Outlet1D>("outlet",sol);
    std::vector<std::shared_ptr<Domain1D>> domains{inlet,flow,outlet};
    Sim1D flame(domains);flame.setMaxGridPoints(1,6000);
    auto loc=guess.x;for(auto& x:loc)x=(x-guess.x.front())/(guess.x.back()-guess.x.front());
    flow->setProfile("T",loc,guess.T);flow->setProfile("velocity",loc,guess.u);
    for(size_t k=0;k<names.size();k++)flow->setProfile(names[k],loc,guess.y[k]);
    flame.setFixedTemperature(Tu+.3*(guess.T.back()-Tu));flow->setEnergyEnabled(true);
    std::ofstream results(output/"refinement.csv");
    results<<"case,phi,slope,curve,points,speed_cm_s,Tb_K,rhou_kg_m3,massflux_kg_m2s\n"<<std::setprecision(16);
    for(auto level:std::vector<std::pair<double,double>>{{.08,.1},{.03,.05},{.015,.025},{.0075,.0125},{.00375,.00625}}) {
        flow->setRefineCriteria(3,level.first,level.second,0);flame.solve(1,true);
        const double speed=flow->values("velocity")[0];
        results<<label<<','<<phi<<','<<level.first<<','<<level.second<<','<<flow->nPoints()
               <<','<<100*speed<<','<<flow->values("T").back()<<','<<rho<<','<<rho*speed<<'\n';results.flush();
        // Preserve each converged grid even if the next refinement fails.
        flame.save((output/"flame.yaml").string(),"flame","Burke H2 steady numerical solution",true);
    }
    auto real=newSolution((input/"srk.yaml").string(),"","hydrogen-full");activate(real,5);
    hydrogen::writeProfiles(output,flow,sol,ideal,real,pressure);
    std::ofstream callbacks(output/"callbacks.txt");
    if(auto* t=dynamic_cast<liang::StagedTransport*>(sol->transport().get()))
        callbacks<<"conductivity "<<t->conductivityCalls<<"\ndiffusion "<<t->diffusionCalls<<'\n';
    if(auto* t=dynamic_cast<hydrogen::Transport*>(sol->transport().get()))
        callbacks<<"pair_update "<<t->pairUpdates<<'\n';
    std::ofstream(output/"completed.txt")<<"Solver completed; scientific acceptance pending\n";
    std::cout<<"COMPLETED "<<label<<" phi="<<phi<<" speed_cm_s="<<100*flow->values("velocity")[0]<<std::endl;
} catch(const std::exception& e) {std::cerr<<e.what()<<std::endl;return 1;}
}
