#include "StagedTransport.h"
#include "cantera/base/Solution.h"
#include "cantera/kinetics/Kinetics.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/transport/TransportFactory.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
using namespace Cantera;
namespace fs=std::filesystem;

std::vector<std::string> fields(const std::string& line) {
    std::stringstream stream(line);std::string value;std::vector<std::string> out;
    while(std::getline(stream,value,',')) {
        if(!value.empty() && value.back()=='\r')value.pop_back();
        out.push_back(value);
    }
    return out;
}

int main(int argc,char** argv) {
try {
    if(argc!=4 || fs::exists(argv[3]))throw std::runtime_error("Usage: model-probe INPUTS SOLVED_PROFILE NEW_OUTPUT.csv");
    fs::path input=argv[1];std::ifstream table(input/"species.txt");
    std::vector<liang::Species> parameters;std::vector<std::string> names;
    liang::Species parameter;std::string name;
    while(table>>name>>parameter.Tc>>parameter.Pc>>parameter.Vc>>parameter.W>>parameter.omega>>parameter.eos) {
        names.push_back(name);parameters.push_back(parameter);
    }
    if(names.size()!=53)throw std::runtime_error("Expected 53 species");
    ThermoFactory::factory()->reg("liang-srk",[](){auto* gas=new liang::SrkPhase;gas->stage=1;return gas;});
    TransportFactory::factory()->reg("liang-staged",[&](){auto* tr=new liang::StagedTransport;tr->stage=4;tr->parameters=parameters;return tr;});
    auto real=newSolution((input/"srk.yaml").string(),"","liang-staged");
    auto ideal=newSolution((input/"ideal.yaml").string(),"","mixture-averaged");
    auto* gas=dynamic_cast<liang::SrkPhase*>(real->thermo().get());
    auto* transport=dynamic_cast<liang::StagedTransport*>(real->transport().get());
    if(!gas || !transport)throw std::runtime_error("Custom adapter not selected");
    gas->parameters=parameters;gas->stage=3;
    std::ifstream profile(argv[2]);std::string line;std::getline(profile,line);auto header=fields(line);
    if(header.size()!=60 || header[1]!="T_K")throw std::runtime_error("Expected project profile schema");
    for(size_t k=0;k<names.size();k++)if(header[k+7]!="Y_"+names[k])throw std::runtime_error("Species order mismatch");
    std::vector<std::vector<double>> rows;
    while(std::getline(profile,line)) {
        auto row=fields(line);if(row.size()!=header.size())throw std::runtime_error("Profile width");
        std::vector<double> values;for(auto& value:row)values.push_back(std::stod(value));rows.push_back(values);
    }
    if(rows.empty())throw std::runtime_error("Empty profile");
    std::ofstream out(argv[3]);out<<std::setprecision(16)
        <<"target_T,T,p_atm,rho_ideal,rho_srk,h_ideal,h_srk,lambda_mix_ideal,lambda_mix_srk,lambda_EH_molar,lambda_EH_mass,D_CH4_base,D_CH4_Taka,D_OH_base,D_OH_Taka,min_D_Taka,rate_L1_srk_over_ideal,concentration_srk_over_ideal\n";
    for(double target:{298.,400.,600.,900.,1200.,1500.,1800.,2100.,2400.}) {
        const auto& row=*std::min_element(rows.begin(),rows.end(),[&](const auto& a,const auto& b){return std::abs(a[1]-target)<std::abs(b[1]-target);});
        std::vector<double> y(row.begin()+7,row.end());for(auto& v:y)v=std::max(0.,v);
        for(double atm:{1.,100.}) {
            double T=row[1],p=atm*101325;
            gas->setState_TPY(T,p,y.data());ideal->thermo()->setState_TPY(T,p,y.data());
            std::vector<double> x(53),v(53),cp(53),d0(53),d1(53),w0(53),w1(53);
            gas->getMoleFractions(x.data());gas->getPartialMolarVolumes(v.data());gas->getCp_R_ref(cp.data());
            std::vector<rfElyHanley::Species> species;
            for(size_t k=0;k<53;k++) {const auto& z=parameters[k];species.push_back({z.Tc,z.Pc,z.Vc,gas->molecularWeight(k),z.omega,cp[k]});}
            transport->stage=3;double base=transport->thermalConductivity();transport->getMixDiffCoeffs(d0.data());
            transport->stage=5;double eh=transport->thermalConductivity();transport->getMixDiffCoeffs(d1.data());
            double shortcut=rfElyHanley::conductivity(T,1/gas->molarDensity(),species,x,v,rfElyHanley::DensityMapping::massDensityShortcut);
            real->kinetics()->getNetProductionRates(w1.data());ideal->kinetics()->getNetProductionRates(w0.data());
            double l0=0,l1=0;for(size_t k=0;k<53;k++){l0+=std::abs(w0[k]);l1+=std::abs(w1[k]);}
            auto ch4=gas->speciesIndex("CH4"),oh=gas->speciesIndex("OH");
            out<<target<<','<<T<<','<<atm<<','<<ideal->thermo()->density()<<','<<gas->density()<<','
               <<ideal->thermo()->enthalpy_mass()<<','<<gas->enthalpy_mass()<<','<<ideal->transport()->thermalConductivity()<<','<<base<<','<<eh<<','<<shortcut<<','
               <<d0[ch4]<<','<<d1[ch4]<<','<<d0[oh]<<','<<d1[oh]<<','<<*std::min_element(d1.begin(),d1.end())<<','
               <<(l0>0?l1/l0:0)<<','<<gas->molarDensity()/ideal->thermo()->molarDensity()<<'\n';
        }
    }
    std::cout<<"Frozen-state probe completed\n";
} catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
