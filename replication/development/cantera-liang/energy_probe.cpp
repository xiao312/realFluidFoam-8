#include "StagedTransport.h"
#include "DiagnosticOptions.h"
#include "cantera/base/Solution.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/transport/TransportFactory.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
using namespace Cantera;
namespace fs=std::filesystem;
int main(int argc,char** argv) {
try {
    if(argc!=7 || fs::exists(argv[4]))throw std::runtime_error("Usage: energy-probe INPUTS CASE PROFILE NEW_OUTPUT OPTIONS ATM");
    fs::path input=argv[1];int stage=std::stoi(argv[2]);double pressure=101325*std::stod(argv[6]);
    if(stage<1 || stage>5 || pressure<101325 || pressure>10132500)throw std::runtime_error("Invalid stage/pressure");
    liang::DiagnosticOptions options(argv[5]);
    if(options.soret)throw std::runtime_error("Use the recorded native soret-flux.csv; this energy probe has no thermal-diffusion term");
    std::ifstream table(input/"species.txt");std::vector<liang::Species> parameters;
    std::vector<std::string> names;std::string name;liang::Species item;
    while(table>>name>>item.Tc>>item.Pc>>item.Vc>>item.W>>item.omega>>item.eos) {names.push_back(name);parameters.push_back(item);}
    if(names.size()!=53)throw std::runtime_error("Expected 53 species");
    ThermoFactory::factory()->reg("liang-srk",[](){auto* g=new liang::SrkPhase;g->stage=1;return g;});
    TransportFactory::factory()->reg("liang-staged",[&](){auto* t=new liang::StagedTransport;
        t->highTemperature=options.highTemperature;
        t->bulkTakahashi=options.bulkTakahashi;
        t->table2=options.table2;t->smoothedAlpha=options.smoothedAlpha;t->parameters=parameters;t->stage=stage;t->denseIncrementOnly=options.dense;t->boundedTakahashi=options.bounded;return t;});
    auto sol=newSolution((input/(stage==1?"ideal.yaml":"srk.yaml")).string(),"",stage==1?"mixture-averaged":"liang-staged");
    auto gas=sol->thermo();if(auto* g=dynamic_cast<liang::SrkPhase*>(gas.get())) {g->smoothedAlpha=options.smoothedAlpha;g->parameters=parameters;g->stage=stage;}
    std::vector<double> formation(53);gas->setTemperature(298.15);
    gas->getEnthalpy_RT_ref(formation.data());
    for(auto& value:formation)value*=Cantera::GasConstant*298.15;
    std::ifstream file(argv[3]);std::string line,value;std::getline(file,line);
    if(!line.empty() && line.back()=='\r')line.pop_back();
    std::string expected="x_m,T_K,U_m_s,rho_kg_m3,h_J_kg,cp_J_kgK,lambda_W_mK";
    for(auto& n:names)expected+=",Y_"+n;
    if(line!=expected)throw std::runtime_error("Profile schema/species mismatch");
    std::vector<std::vector<double>> rows,xs;
    while(std::getline(file,line)) {
        std::stringstream stream(line);std::vector<double> row;
        while(std::getline(stream,value,','))row.push_back(std::stod(value));
        if(row.size()!=60)throw std::runtime_error("Profile width");
        gas->setTemperature(row[1]);gas->setMassFractions_NoNorm(row.data()+7);gas->setPressure(pressure);
        std::vector<double> x(53);gas->getMoleFractions(x.data());xs.push_back(x);rows.push_back(row);
    }
    if(rows.size()<3)throw std::runtime_error("Empty profile");
    std::ofstream out(argv[4]);out<<std::setprecision(16)
        <<"x_mid_m,advective_W_m2,conductive_W_m2,species_enthalpy_W_m2,total_W_m2,mass_diffusion_sum_kg_m2s,pure_species_total_W_m2,pure_minus_partial_W_m2,upwind_total_W_m2,upwind_pure_total_W_m2,inert_minus_mass_corrected_sensible_W_m2\n";
    for(size_t j=0;j+1<rows.size();j++) {
        auto& a=rows[j];auto& b=rows[j+1];double dz=b[0]-a[0];
        if(!(dz>0))throw std::runtime_error("Nonmonotone grid");
        std::vector<double> y(53),d(53),h(53),flux(53);
        for(size_t k=0;k<53;k++)y[k]=.5*(a[k+7]+b[k+7]);
        gas->setTemperature(.5*(a[1]+b[1]));gas->setMassFractions_NoNorm(y.data());gas->setPressure(pressure);
        if(options.massGradient)sol->transport()->getMixDiffCoeffsMass(d.data());
        else sol->transport()->getMixDiffCoeffs(d.data());
        gas->getPartialMolarEnthalpies(h.data());
        double correction=0;
        for(size_t k=0;k<53;k++) {
            flux[k]=options.massGradient
                ? d[k]*gas->density()*(a[k+7]-b[k+7])/dz
                : d[k]*gas->molecularWeight(k)*gas->density()/gas->meanMolecularWeight()*(xs[j][k]-xs[j+1][k])/dz;
            correction-=flux[k];
        }
        double speciesFlux=0,massFlux=0,pureDifference=0;
        const auto* srk=dynamic_cast<const liang::SrkPhase*>(gas.get());
        for(size_t k=0;k<53;k++) {
            flux[k]+=correction*a[k+7]; // Flow1D uses left-node Y for correction.
            speciesFlux+=flux[k]*h[k]/gas->molecularWeight(k);massFlux+=flux[k];
            if(srk && stage>=3) {
                const auto pure=liang::evaluate(gas->temperature(),pressure,{1.},
                                                {parameters[k]},options.smoothedAlpha);
                pureDifference+=flux[k]*(pure.h-srk->state().hb[k])/gas->molecularWeight(k);
            }
        }
        double conductive=-sol->transport()->thermalConductivity()*(b[1]-a[1])/dz;
        double advective=.5*(a[2]*a[3]*a[4]+b[2]*b[3]*b[4]);
        double mdot=.5*(a[2]*a[3]+b[2]*b[3]);
        double upwind=mdot*(mdot>=0?a[4]:b[4])+conductive+speciesFlux;
        size_t inert=gas->speciesIndex("N2");double inertFlux=0,correctedSensibleFlux=0;
        const double inertH=(h[inert]-formation[inert])/gas->molecularWeight(inert);
        for(size_t k=0;k<53;k++) {
            const double sensible=(h[k]-formation[k])/gas->molecularWeight(k);
            correctedSensibleFlux+=flux[k]*sensible;
            if(k!=inert)inertFlux+=(flux[k]-correction*a[k+7])*(sensible-inertH);
        }
        out<<.5*(a[0]+b[0])<<','<<advective<<','<<conductive<<','<<speciesFlux<<','
           <<advective+conductive+speciesFlux<<','<<massFlux<<','
           <<advective+conductive+speciesFlux+pureDifference<<','<<pureDifference<<','
           <<upwind<<','<<upwind+pureDifference<<','<<inertFlux-correctedSensibleFlux<<'\n';
    }
    std::cout<<"Energy flux reconstruction completed\n";
} catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
