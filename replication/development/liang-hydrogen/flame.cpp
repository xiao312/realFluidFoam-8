#include "Profile.h"
#include "HydrogenTransport.h"
#include "EnergyFlows.h"
#include "DiffusionFlow.h"
#include "ConservativeFlow.h"
#include "../cantera-liang/PressureChemistry.h"
#include "../cantera-liang/TotalEnthalpyFlow.h"
#include "../cantera-liang/SoretCompatibleFlow.h"
#include "cantera/oneD/DomainFactory.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/transport/TransportFactory.h"
#include <iostream>
using namespace Cantera;
namespace fs=std::filesystem;

int main(int argc,char** argv) {
try {
    if(argc<5 || argc>10)throw std::runtime_error("Usage: flame INPUT CASE PHI NEW_OUTPUT [GUESS|-] [WIDTH_M] [TU_K] [VARIANT] [GRID_FACTOR]");
    fs::path input=argv[1],output=argv[4];std::string label=argv[2];
    const int stage=label=="3star"?3:std::stoi(label);
    const double phi=std::stod(argv[3]),pressure=100*OneAtm;
    const double width=argc>=7?std::stod(argv[6]):.01,Tu=argc>=8?std::stod(argv[7]):298.;
    const std::string requestedVariant=argc>=9?argv[8]:"baseline";
    const bool manualSoret=requestedVariant=="manual-soret-baseline";
    const bool soret=manualSoret || requestedVariant=="soret-baseline";
    const std::string baseVariant=soret?"baseline":requestedVariant;
    const bool concentration=baseVariant.rfind("concentration-",0)==0;
    const bool activity=baseVariant.rfind("activity-",0)==0;
    const std::string fluxVariant=concentration?baseVariant.substr(14):
                                  activity?baseVariant.substr(9):baseVariant;
    const bool midpoint=fluxVariant.rfind("midpoint-",0)==0;
    const std::string alphaVariant=midpoint?fluxVariant.substr(9):fluxVariant;
    const bool smooth=alphaVariant.rfind("smooth-",0)==0;
    const bool signedAlpha=alphaVariant.rfind("signed-",0)==0;
    const std::string variant=(smooth || signedAlpha)?alphaVariant.substr(7):alphaVariant;
    const int gridFactor=argc>=10?std::stoi(argv[9]):1;
    if(gridFactor!=1 && gridFactor!=2 && gridFactor!=4)
        throw std::runtime_error("GRID_FACTOR must be 1, 2 or 4");
    const bool pureFlux=variant=="pure-flux" || variant=="pure-flux-full-conductivity" || variant=="pure-flux-matched-energy";
    const bool fullConductivity=variant=="full-conductivity" || variant=="pure-flux-full-conductivity";
    const bool matchedEnergy=variant=="matched-energy" || variant=="pure-flux-matched-energy";
    const bool pureTemperature=variant=="pure-temperature";
    const bool cpOnlyTemperature=variant=="cp-only-temperature";
    const bool conservative=requestedVariant=="conservative";
    const bool forceTotalEnthalpy=requestedVariant=="total-enthalpy";
    if(variant!="baseline" && !pureFlux && !fullConductivity && !matchedEnergy && !pureTemperature && !cpOnlyTemperature && !conservative && !forceTotalEnthalpy)
        throw std::runtime_error("Unknown model variant");
    if((conservative || forceTotalEnthalpy) && label=="3star")
        throw std::runtime_error("Total enthalpy is not a Case 3star approximation");
    if(stage<1 || stage>5 || !(phi>=.6 && phi<=3) || !(width>0 && width<=.1)
       || !(Tu>=280 && Tu<=350) || fs::exists(output))throw std::runtime_error("Invalid input or existing output");
    if(activity && stage==2)throw std::runtime_error("Activity chemistry requires complete thermodynamics");
    std::ifstream table(input/"species.txt");std::vector<liang::Species> parameters;
    std::vector<std::string> names;std::string name;liang::Species row;
    while(table>>name>>row.Tc>>row.Pc>>row.Vc>>row.W>>row.omega>>row.eos) {
        parameters.push_back(row);names.push_back(name);
    }
    if(names.size()!=13)throw std::runtime_error("Expected 13 Burke species");
    auto pairs=hydrogen::readPairs((input/"pairs.txt").string());
    const auto collisionPairs=manualSoret?
        hydrogen::readCollisionPairs((input/"collision-pairs.txt").string()):
        std::vector<hydrogen::CollisionPair>{};
    ThermoFactory::factory()->reg("liang-srk",[](){auto* g=new liang::SrkPhase;g->stage=1;return g;});
    TransportFactory::factory()->reg("hydrogen-staged",[&](){
        auto* t=new hydrogen::Transport;t->pairs=pairs;t->parameters=parameters;t->stage=stage;
        t->manualSoret=manualSoret;t->collisionPairs=collisionPairs;
        t->denseIncrementOnly=!fullConductivity;t->boundedTakahashi=true;t->table2=true;
        t->smoothedAlpha=smooth;t->signedAlpha=signedAlpha;return t;
    });
    TransportFactory::factory()->reg("hydrogen-full",[&](){
        auto* t=new hydrogen::Transport;t->pairs=pairs;t->parameters=parameters;t->stage=5;
        t->denseIncrementOnly=!fullConductivity;t->boundedTakahashi=true;t->table2=true;
        t->smoothedAlpha=smooth;t->signedAlpha=signedAlpha;return t;
    });
    TransportFactory::factory()->reg("hydrogen-dilute",[&](){
        auto* t=new hydrogen::Transport;t->pairs=pairs;t->parameters=parameters;t->stage=1;return t;
    });
    auto activate=[&](std::shared_ptr<Solution> s,int modelStage) {
        if(auto* g=dynamic_cast<liang::SrkPhase*>(s->thermo().get())) {
            g->parameters=parameters;g->stage=modelStage;g->smoothedAlpha=smooth;
            g->signedAlpha=signedAlpha;
            g->fugacityKinetics=activity;
            g->setState_TP(Tu,pressure);
        }
    };
    auto ideal=newSolution((input/"ideal.yaml").string(),"","hydrogen-dilute");
    if(ideal->kinetics()->nReactions()!=27)throw std::runtime_error("Expected 27 Burke reactions");
    for(size_t k=0;k<names.size();k++)
        if(ideal->thermo()->speciesName(k)!=names[k])throw std::runtime_error("Species order mismatch");
    auto guess=hydrogen::initialGuess(ideal,phi,Tu,pressure,width);
    if(argc>=6 && std::string(argv[5])!="-")guess=hydrogen::readGuess(argv[5],names.size());
    std::vector<double> grid;
    for(size_t j=0;j+1<guess.x.size();j++)
        for(int part=0;part<gridFactor;part++)
            grid.push_back(guess.x[j]+double(part)/gridFactor*(guess.x[j+1]-guess.x[j]));
    grid.push_back(guess.x.back());
    auto sol=newSolution((input/(stage==1?"ideal.yaml":"srk.yaml")).string(),"",
                         "hydrogen-staged");
    activate(sol,stage);auto gas=sol->thermo();
    gas->setEquivalenceRatio(phi,"H2","O2:0.21,N2:0.79");gas->setState_TP(Tu,pressure);
    if(stage>1 && !concentration && !activity)
        liang::usePressureChemistry(sol,(input/"ideal.yaml").string());
    std::vector<double> xin(names.size()),partial(names.size());
    gas->getMoleFractions(xin.data());const double rho=gas->density();
    fs::create_directories(output);
    std::ofstream config(output/"configuration.txt");
    config<<std::setprecision(16)<<"case "<<label<<"\nphi "<<phi<<"\npressure_Pa "<<pressure
          <<"\nTu_K "<<Tu<<"\nwidth_m "<<guess.x.back()-guess.x.front()
          <<"\nkinetics "<<(activity?"Burke2012-N2-activity":
                            concentration?"Burke2012-N2-actual-concentration":"Burke2012-N2-pressure")
          <<"\ncollider_concentration "<<(activity || concentration?"physical":"pressure-based")
          <<"\ntransport author-pair-count "<<pairs.size()
          <<"\nmodel_variant "<<requestedVariant<<"\nalpha "<<(smooth?"C4-continuation":
              signedAlpha?"signed-Soave-factors":"original-Soave")
          <<"\nflux_correction "<<(midpoint?"midpoint":"left-node")
          <<"\ngrid_factor "<<gridFactor<<"\ninitial_grid_points "<<grid.size()
          <<"\nconductivity "<<(fullConductivity?"full-Ely-Hanley":"dense-increment-diagnostic")
          <<"\nTakahashi bounded-Table2"
          <<"\nSoret "<<(manualSoret?"manual-author-pairs":soret?"cantera-3.2":"off")
          <<"\nthermal_collision_pair_count "<<collisionPairs.size()
          <<"\nspecies_discretization "<<(conservative?"conservative-face":"stock-upwind")
          <<"\nenergy "<<(conservative?"conservative-total-enthalpy":
              cpOnlyTemperature?"cp-only-temperature":pureTemperature?"pure-temperature":
              matchedEnergy?"matched-total-enthalpy":
              forceTotalEnthalpy || (stage>=3 && label!="3star")?
                  "legacy-total-enthalpy":"partial-temperature")<<'\n';
    config.flush();
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
    if(conservative)flow=std::make_shared<hydrogen::ConservativeFlow>(sol);
    else if(soret && stage>=3 && label!="3star")
        flow=std::make_shared<liang::SoretCompatibleFlow<liang::TotalEnthalpyFlow>>(sol,pureFlux);
    else if(soret)flow=std::make_shared<liang::SoretCompatibleFlow<Flow1D>>(sol,"flow");
    else if(cpOnlyTemperature)flow=hydrogen::makeFlow<hydrogen::CpOnlyTemperatureFlow>(midpoint,sol);
    else if(pureTemperature)flow=hydrogen::makeFlow<hydrogen::PureTemperatureFlow>(midpoint,sol);
    else if(matchedEnergy)flow=hydrogen::makeFlow<hydrogen::EnthalpyFlow>(midpoint,sol,pureFlux);
    else if(forceTotalEnthalpy || (stage>=3 && label!="3star"))
        flow=hydrogen::makeFlow<liang::TotalEnthalpyFlow>(midpoint,sol,pureFlux);
    else flow=hydrogen::makeFlow<Flow1D>(midpoint,sol,"flow");
    flow->setFreeFlow();flow->setPressure(pressure);
    flow->setupGrid(grid.size(),grid.data());flow->setSteadyTolerances(1e-5,1e-11);
    flow->setFluxGradientBasis(ThermoBasis::molar);flow->enableSoret(soret);
    auto inlet=newDomain<Inlet1D>("inlet",sol);inlet->setTemperature(Tu);
    inlet->setMoleFractions(xin.data());inlet->setMdot(rho*guess.u[0]);
    auto outlet=newDomain<Outlet1D>("outlet",sol);
    std::vector<std::shared_ptr<Domain1D>> domains{inlet,flow,outlet};
    Sim1D flame(domains);flame.setMaxGridPoints(1,gridFactor>1?12000:6000);
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
    if(conservative)
        std::dynamic_pointer_cast<hydrogen::ConservativeFlow>(flow)->writeBalances(output);
    if(soret) {
        auto* exporter=dynamic_cast<liang::SoretOutput*>(flow.get());
        if(!exporter)throw std::runtime_error("Missing hydrogen Soret output");
        exporter->writeSoretFluxes((output/"soret-flux.csv").string());
    }
    std::ofstream callbacks(output/"callbacks.txt");
    auto* chemistry=dynamic_cast<liang::PressureChemistry*>(sol->kinetics().get());
    callbacks<<"pressure_chemistry "<<(chemistry?chemistry->calls:0)<<'\n';
    if(auto* t=dynamic_cast<liang::StagedTransport*>(sol->transport().get()))
        callbacks<<"conductivity "<<t->conductivityCalls<<"\ndiffusion "<<t->diffusionCalls<<'\n';
    if(auto* t=dynamic_cast<hydrogen::Transport*>(sol->transport().get())) {
        callbacks<<"pair_update "<<t->pairUpdates<<'\n';
        if(soret)callbacks<<std::setprecision(16)<<"thermal_calls "<<t->thermalCalls
            <<"\nauthor_collision_calls "<<t->authorCollisionCalls
            <<"\nfallback_collision_calls "<<t->fallbackCollisionCalls
            <<"\nthermal_minimum_T_K "<<t->thermalMinimumT
            <<"\nthermal_maximum_T_K "<<t->thermalMaximumT<<'\n';
    }
    std::ofstream(output/"completed.txt")<<"Solver completed; scientific acceptance pending\n";
    std::cout<<"COMPLETED "<<label<<" phi="<<phi<<" speed_cm_s="<<100*flow->values("velocity")[0]<<std::endl;
} catch(const std::exception& e) {std::cerr<<e.what()<<std::endl;return 1;}
}
