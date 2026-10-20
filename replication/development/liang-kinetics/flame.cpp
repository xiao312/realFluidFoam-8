#include "cantera/onedim.h"
#include "cantera/oneD/DomainFactory.h"
#include "Guess.h"
#include "PairTransport.h"
#include "cantera/transport/TransportFactory.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
using namespace Cantera;
namespace fs=std::filesystem;

int main(int argc,char** argv) {
try {
    if(argc<4 || argc>6)throw std::runtime_error("Usage: kinetics-flame MECHANISM PHI NEW_OUTPUT [GUESS|-] [PAIRS|-]");
    const double phi=std::stod(argv[2]),pressure=100*OneAtm,Tu=298.,width=.01;
    const fs::path output=argv[3];
    if(phi<.8 || phi>1.5 || fs::exists(output))
        throw std::runtime_error("Expected phi 0.8-1.5 and new output");
    auto pairs=kinetics_control::readPairs(argc==6?argv[5]:"-");
    TransportFactory::factory()->reg("kinetics-author-pairs",[&](){
        auto* transport=new kinetics_control::PairTransport;transport->pairs=pairs;return transport;});
    auto sol=newSolution(argv[1],"",pairs.empty()?"mixture-averaged":"kinetics-author-pairs");
    auto gas=sol->thermo();
    gas->setEquivalenceRatio(phi,"CH4","O2:0.21,N2:0.79");gas->setState_TP(Tu,pressure);
    const size_t n=gas->nSpecies();
    std::vector<double> yu(n),yb(n),xin(n);
    gas->getMassFractions(yu.data());gas->getMoleFractions(xin.data());
    const double rhou=gas->density();
    gas->equilibrate("HP");gas->getMassFractions(yb.data());
    const double Tb=gas->temperature(),uu=.035,ub=uu*rhou/gas->density();
    if(Tb>3500)throw std::runtime_error("Equilibrium exceeds rate qualification range");
    gas->setState_TPY(Tu,pressure,yu.data());
    std::vector<double> grid,loc,temperatures,velocities;
    std::vector<std::vector<double>> ys(n);
    for(size_t j=0;j<21;j++) {
        const double z=double(j)/20,q=std::clamp((z-.3)/.2,0.,1.);
        grid.push_back(width*z);loc.push_back(z);
        temperatures.push_back(Tu+q*(Tb-Tu));velocities.push_back(uu+q*(ub-uu));
        for(size_t k=0;k<n;k++)ys[k].push_back(yu[k]+q*(yb[k]-yu[k]));
    }
    const bool suppliedGuess=argc>=5 && std::string(argv[4])!="-";
    const double discarded=suppliedGuess?kinetics_control::readGuess(
        argv[4],*gas,grid,loc,temperatures,velocities,ys):0.;
    auto flow=newDomain<Flow1D>("gas-flow",sol,"flow");
    flow->setFreeFlow();flow->setPressure(pressure);
    flow->setupGrid(grid.size(),grid.data());
    flow->setSteadyTolerances(1e-5,1e-11);
    flow->setFluxGradientBasis(ThermoBasis::molar);flow->enableSoret(false);
    auto inlet=newDomain<Inlet1D>("inlet",sol);
    inlet->setTemperature(Tu);inlet->setMoleFractions(xin.data());inlet->setMdot(rhou*velocities[0]);
    auto outlet=newDomain<Outlet1D>("outlet",sol);
    std::vector<std::shared_ptr<Domain1D>> domains{inlet,flow,outlet};
    Sim1D flame(domains);flame.setMaxGridPoints(1,6000);
    flow->setProfile("T",loc,temperatures);flow->setProfile("velocity",loc,velocities);
    for(size_t k=0;k<n;k++)flow->setProfile(gas->speciesName(k),loc,ys[k]);
    flame.setFixedTemperature(Tu+.3*(Tb-Tu));
    fs::create_directories(output);
    std::ofstream config(output/"configuration.txt");
    config<<std::setprecision(16)<<"case 1\nfuel CH4\nphi "<<phi<<"\npressure_Pa "<<pressure
          <<"\nTu_K "<<Tu<<"\nwidth_m "<<grid.back()-grid.front()<<"\nspecies "<<n
          <<"\nreactions "<<sol->kinetics()->nReactions()
          <<"\ntransport mixture-averaged-molar\nSoret off\nradiation off"
          <<"\nauthor_diffusion_pairs "<<pairs.size()
          <<"\nsupplied_steady_guess "<<suppliedGuess<<"\nmaximum_discarded_guess_mass_fraction "<<discarded<<'\n';
    config.flush();
    std::ofstream results(output/"refinement.csv");
    results<<"case,phi,slope,curve,points,speed_cm_s,Tb_K\n"<<std::setprecision(16);
    // The fixed-temperature solve prepares a numerical species/velocity guess;
    // all reported levels solve the complete energy equation.
    flow->setRefineCriteria(3,.08,.1,0);
    if(!suppliedGuess){flow->setEnergyEnabled(false);flame.solve(1,true);}
    flow->setEnergyEnabled(true);
    for(auto level:std::vector<std::pair<double,double>>{{.08,.1},{.03,.05},{.015,.025},{.0075,.0125},{.00375,.00625}}) {
        flow->setRefineCriteria(3,level.first,level.second,0);flame.solve(1,true);
        const auto t=flow->values("T");
        if(*std::max_element(t.begin(),t.end())>3500)
            throw std::runtime_error("Solution exceeds rate qualification range");
        results<<"1,"<<phi<<','<<level.first<<','<<level.second<<','<<flow->nPoints()
               <<','<<100*flow->values("velocity")[0]<<','<<t.back()<<'\n';results.flush();
        flame.save((output/"flame.yaml").string(),"flame","Ideal author-mechanism control",true);
    }
    grid=flow->grid();temperatures=flow->values("T");velocities=flow->values("velocity");
    for(size_t k=0;k<n;k++)ys[k]=flow->values(gas->speciesName(k));
    std::ofstream csv(output/"profile.csv");
    csv<<std::setprecision(16)<<"x_m,T_K,U_m_s,rho_kg_m3,h_J_kg,cp_J_kgK,lambda_W_mK";
    for(const auto& name:gas->speciesNames())csv<<",Y_"<<name;csv<<'\n';
    std::vector<double> y(n);
    for(size_t j=0;j<grid.size();j++) {
        for(size_t k=0;k<n;k++)y[k]=ys[k][j];
        gas->setState_TPY(temperatures[j],pressure,y.data());
        csv<<grid[j]<<','<<temperatures[j]<<','<<velocities[j]<<','<<gas->density()
           <<','<<gas->enthalpy_mass()<<','<<gas->cp_mass()<<','<<sol->transport()->thermalConductivity();
        for(auto v:y)csv<<','<<v;csv<<'\n';
    }
    std::ofstream(output/"completed.txt")<<"Numerical solve completed; paper acceptance pending\n";
    if(auto* transport=dynamic_cast<kinetics_control::PairTransport*>(sol->transport().get()))
        std::ofstream(output/"callbacks.txt")<<"author_pair_updates "<<transport->pairUpdates<<'\n';
    std::cout<<"COMPLETED speed_cm_s="<<100*velocities[0]<<std::endl;
} catch(const std::exception& e) {std::cerr<<e.what()<<std::endl;return 1;}
}
