#include "StagedTransport.h"
#include "cantera/base/Solution.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/transport/TransportFactory.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>

// Frozen-state audit, not a flame solve. Binary-matrix reconstruction provides
// an independent check of Cantera's mixture coefficient conversion.
using namespace Cantera;
namespace fs=std::filesystem;

std::vector<std::string> split(const std::string& line) {
    std::stringstream stream(line);std::string item;std::vector<std::string> result;
    while(std::getline(stream,item,',')) {
        if(!item.empty() && item.back()=='\r')item.pop_back();
        result.push_back(item);
    }
    return result;
}

int main(int argc,char** argv) {
try {
    if(argc!=4 || fs::exists(argv[3]))
        throw std::runtime_error("Usage: diffusion-probe INPUTS PROFILE NEW_OUTPUT.csv");
    fs::path input=argv[1];std::ifstream table(input/"species.txt");
    std::vector<liang::Species> parameters;std::vector<std::string> names;
    liang::Species parameter;std::string name;
    while(table>>name>>parameter.Tc>>parameter.Pc>>parameter.Vc>>parameter.W
               >>parameter.omega>>parameter.eos) {
        parameters.push_back(parameter);names.push_back(name);
    }
    if(names.size()!=53)throw std::runtime_error("Expected 53 species");
    ThermoFactory::factory()->reg("liang-srk",[](){
        auto* gas=new liang::SrkPhase;gas->stage=1;return gas;
    });
    TransportFactory::factory()->reg("liang-staged",[&](){
        auto* transport=new liang::StagedTransport;
        transport->parameters=parameters;transport->stage=5;
        transport->boundedTakahashi=true;transport->table2=true;
        return transport;
    });
    auto solution=newSolution((input/"srk.yaml").string(),"","liang-staged");
    auto* gas=dynamic_cast<liang::SrkPhase*>(solution->thermo().get());
    auto* transport=dynamic_cast<liang::StagedTransport*>(solution->transport().get());
    if(!gas || !transport)throw std::runtime_error("Custom adapter missing");
    gas->parameters=parameters;gas->stage=5;
    const size_t n=names.size();
    std::ifstream profile(argv[2]);std::string line;std::getline(profile,line);
    auto header=split(line);
    if(header.size()!=60 || header[1]!="T_K")throw std::runtime_error("Profile schema");
    for(size_t k=0;k<n;k++)
        if(header[k+7]!="Y_"+names[k] || gas->speciesName(k)!=names[k])
            throw std::runtime_error("Species order mismatch");
    std::vector<std::vector<double>> rows;
    while(std::getline(profile,line)) {
        auto fields=split(line);std::vector<double> row;
        if(fields.size()!=60)throw std::runtime_error("Profile width");
        for(const auto& field:fields)row.push_back(std::stod(field));
        rows.push_back(row);
    }
    if(rows.size()<10)throw std::runtime_error("Incomplete profile");
    std::ofstream out(argv[3]);out<<std::setprecision(16)
        <<"target_T,T_K,critical_rule,species,X,Y,D_dilute,D_corrected,D_mass,"
          "binary_reconstruction_relative_error,mole_flux_kg_m2s,mass_flux_kg_m2s,"
          "sum_mole_flux,sum_mass_flux,bulk_Tc_K,bulk_Pc_Pa,"
          "nonideal_driving_flux_kg_m2s,extra_driving_flux_kg_m2s,sum_driving_flux\n";
    double maxError=0,maxSymmetry=0,maxFluxError=0;
    size_t checks=0;
    for(double target:{300.,400.,600.,900.,1200.,1500.,1800.,2100.}) {
        size_t j=0;
        for(size_t k=1;k+1<rows.size();k++)
            if(std::abs(rows[k][1]-target)<std::abs(rows[j][1]-target))j=k;
        const auto& left=rows[j];const auto& right=rows[j+1];
        const double dx=right[0]-left[0],temperature=.5*(left[1]+right[1]);
        if(!(dx>0))throw std::runtime_error("Nonmonotone grid");
        std::vector<double> y(n),x(n),xl(n),xr(n),yl(n),yr(n);
        gas->setState_TPY(left[1],10132500,left.data()+7);
        gas->getMoleFractions(xl.data());gas->getMassFractions(yl.data());
        gas->setState_TPY(right[1],10132500,right.data()+7);
        gas->getMoleFractions(xr.data());gas->getMassFractions(yr.data());
        for(size_t k=0;k<n;k++)y[k]=.5*(yl[k]+yr[k]);
        gas->setState_TPY(temperature,10132500,y.data());
        gas->getMoleFractions(x.data());gas->getMassFractions(y.data());
        // Composition contribution only: both fugacities use identical T,p.
        // Differencing each side's own T would inadvertently add thermodiffusion.
        const auto phiLeft=liang::evaluate(temperature,10132500,xl,parameters).lnphi;
        const auto phiRight=liang::evaluate(temperature,10132500,xr,parameters).lnphi;
        double bulkTc=0,bulkPc=0;
        for(size_t k=0;k<n;k++) {
            bulkTc+=x[k]*parameters[k].Tc;bulkPc+=x[k]*parameters[k].Pc;
        }
        std::vector<double> dilute(n),corrected(n),mass(n),binary(n*n);
        transport->stage=4;transport->getMixDiffCoeffs(dilute.data());
        transport->stage=5;
        for(bool bulk:{false,true}) {
            transport->bulkTakahashi=bulk;
            transport->getMixDiffCoeffs(corrected.data());
            transport->getMixDiffCoeffsMass(mass.data());
            transport->getBinaryDiffCoeffs(n,binary.data());
            std::vector<double> errors(n),jx(n),jy(n),extra(n);
            double sumX=0,sumY=0,sumExtra=0,scaleX=0,scaleY=0,scaleDriving=0;
            for(size_t k=0;k<n;k++) {
                double denominator=0;
                for(size_t other=0;other<n;other++) {
                    const double d=binary[k+n*other];
                    if(!(d>0 && std::isfinite(d)))throw std::runtime_error("Invalid binary D");
                    maxSymmetry=std::max(maxSymmetry,std::abs(d/binary[other+n*k]-1));
                    if(other!=k)denominator+=x[other]/d;
                }
                const double expected=(1-y[k])/denominator;
                errors[k]=std::abs(expected/corrected[k]-1);
                maxError=std::max(maxError,errors[k]);checks++;
                jx[k]=-gas->density()*gas->molecularWeight(k)/gas->meanMolecularWeight()
                      *corrected[k]*(xr[k]-xl[k])/dx;
                jy[k]=-gas->density()*mass[k]*(yr[k]-yl[k])/dx;
                extra[k]=-gas->density()*gas->molecularWeight(k)/gas->meanMolecularWeight()
                         *corrected[k]*x[k]*(phiRight[k]-phiLeft[k])/dx;
                if(!std::isfinite(extra[k]))throw std::runtime_error("Nonfinite driving-force flux");
                sumExtra+=extra[k];scaleDriving+=std::abs(jx[k]+extra[k]);
                sumX+=jx[k];sumY+=jy[k];scaleX+=std::abs(jx[k]);scaleY+=std::abs(jy[k]);
            }
            double correctedSumX=0,correctedSumY=0,correctedSumDriving=0;
            for(size_t k=0;k<n;k++) {
                // Match Flow1D's left-node mass-correction convention.
                jx[k]-=yl[k]*sumX;jy[k]-=yl[k]*sumY;
                extra[k]-=yl[k]*sumExtra;
                correctedSumX+=jx[k];correctedSumY+=jy[k];
                correctedSumDriving+=jx[k]+extra[k];
            }
            maxFluxError=std::max({maxFluxError,
                std::abs(correctedSumX)/std::max(scaleX,1e-100),
                std::abs(correctedSumY)/std::max(scaleY,1e-100),
                std::abs(correctedSumDriving)/std::max(scaleDriving,1e-100)});
            for(size_t k=0;k<n;k++)
                out<<target<<','<<temperature<<','<<(bulk?"bulk":"pair")<<','<<names[k]
                   <<','<<x[k]<<','<<y[k]<<','<<dilute[k]<<','<<corrected[k]<<','<<mass[k]
                   <<','<<errors[k]<<','<<jx[k]<<','<<jy[k]<<','<<correctedSumX
                   <<','<<correctedSumY<<','<<bulkTc<<','<<bulkPc
                   <<','<<jx[k]+extra[k]<<','<<extra[k]<<','<<correctedSumDriving<<'\n';
        }
    }
    std::cout<<std::setprecision(16)<<"checks="<<checks
        <<" maximum_reconstruction_relative_error="<<maxError
        <<" maximum_binary_asymmetry="<<maxSymmetry
        <<" maximum_relative_net_diffusive_mass_flux="<<maxFluxError<<'\n';
    if(maxError>1e-10 || maxSymmetry>1e-12 || maxFluxError>1e-12)
        throw std::runtime_error("Diffusion audit failed");
} catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
