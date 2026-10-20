#include "NonidealDiffusionFlow.h"
#include "StagedTransport.h"
#include "DiagnosticOptions.h"
#include "cantera/thermo/ThermoFactory.h"
#include <filesystem>
#include <fstream>
#include <iostream>

class AuditFlow : public liang::NonidealDiffusionFlow {
public:
    using NonidealDiffusionFlow::NonidealDiffusionFlow;
    double check(double leftT,double rightT) {
        const double grid[]={0,1e-6,2e-6};setupGrid(3,grid);setPressure(10132500);
        std::vector<double> state(nComponents()*3,0),yl(m_nsp),yr(m_nsp),xl(m_nsp),xr(m_nsp);
        m_thermo->setState_TPX(leftT,m_press,"CH4:.10,O2:.19,N2:.71");
        m_thermo->getMassFractions(yl.data());m_thermo->getMoleFractions(xl.data());
        m_thermo->setState_TPX(rightT,m_press,"CH4:.08,O2:.16,N2:.71,H2O:.03,CO2:.02");
        m_thermo->getMassFractions(yr.data());m_thermo->getMoleFractions(xr.data());
        for(size_t j=0;j<3;j++) {
            state[index(Cantera::c_offset_T,j)]=j?rightT:leftT;
            for(size_t k=0;k<m_nsp;k++)Y(state.data(),k,j)=j?yr[k]:yl[k];
        }
        updateThermo(state.data(),0,2);updateTransport(state.data(),0,2);
        Cantera::Flow1D::updateDiffFluxes(state.data(),0,2);
        std::vector<double> stock(m_nsp);
        for(size_t k=0;k<m_nsp;k++)stock[k]=m_flux(k,0);
        updateDiffFluxes(state.data(),0,2);
        std::vector<double> actual(m_nsp);
        for(size_t k=0;k<m_nsp;k++)actual[k]=m_flux(k,0);

        // Independent assembly from unweighted public transport coefficients.
        setGasAtMidpoint(state.data(),0);
        std::vector<double> d(m_nsp),xm(m_nsp),expected(m_nsp);
        m_trans->getMixDiffCoeffs(d.data());m_thermo->getMoleFractions(xm.data());
        const double rho=m_thermo->density(),w=m_thermo->meanMolecularWeight();
        const auto* srk=dynamic_cast<const liang::SrkPhase*>(m_thermo);
        std::vector<double> a(m_nsp,0),b(m_nsp,0);
        if(srk && srk->stage>=2) {
            a=liang::evaluate(.5*(leftT+rightT),m_press,xl,srk->parameters).lnphi;
            b=liang::evaluate(.5*(leftT+rightT),m_press,xr,srk->parameters).lnphi;
        }
        double total=0,scale=0;
        for(size_t k=0;k<m_nsp;k++) {
            expected[k]=-rho*m_wt[k]/w*d[k]
                *((xr[k]-xl[k])+xm[k]*(b[k]-a[k]))/1e-6;
            total+=expected[k];scale+=std::abs(expected[k]);
        }
        double error=0,net=0,change=0;
        for(size_t k=0;k<m_nsp;k++) {
            expected[k]-=yl[k]*total;net+=actual[k];
            error=std::max(error,std::abs(actual[k]-expected[k])/scale);
            change+=std::abs(actual[k]-stock[k]);
        }
        if(error>1e-12 || std::abs(net)/scale>1e-12)
            throw std::runtime_error("Actual Flow1D nonideal flux differs from independent assembly");
        if(!srk && actual!=stock)throw std::runtime_error("Ideal flow changed");
        return change/scale;
    }
};

int main(int argc,char** argv) {
try {
    if(argc!=2)throw std::runtime_error("Usage: test-diffusion-flow INPUTS");
    for(const char* text:{"nonideal-driving,mass-gradient","nonideal-driving,total-enthalpy"}) {
        bool rejected=false;
        try {liang::DiagnosticOptions invalid(text);} catch(const std::exception&) {rejected=true;}
        if(!rejected)throw std::runtime_error("Unsupported coupled diagnostic accepted");
    }
    std::filesystem::path input=argv[1];std::ifstream table(input/"species.txt");
    std::vector<liang::Species> parameters;std::vector<std::string> names;
    liang::Species row;std::string name;
    while(table>>name>>row.Tc>>row.Pc>>row.Vc>>row.W>>row.omega>>row.eos) {
        parameters.push_back(row);names.push_back(name);
    }
    if(parameters.size()!=53)throw std::runtime_error("Expected 53 species");
    Cantera::ThermoFactory::factory()->reg("liang-srk",[](){
        auto* gas=new liang::SrkPhase;gas->stage=1;return gas;
    });
    size_t checks=0;
    for(int stage:{1,4,5}) {
        auto solution=Cantera::newSolution((input/(stage==1?"ideal.yaml":"srk.yaml")).string(),
                                           "",stage==1?"mixture-averaged":"none");
        auto gas=solution->thermo();
        if(gas->speciesNames()!=names)throw std::runtime_error("Species order");
        if(auto* srk=dynamic_cast<liang::SrkPhase*>(gas.get())) {
            srk->parameters=parameters;srk->stage=stage;srk->setState_TP(298,10132500);
            auto transport=std::make_shared<liang::StagedTransport>();
            transport->parameters=parameters;transport->stage=stage;
            transport->boundedTakahashi=true;transport->table2=true;
            transport->denseIncrementOnly=true;transport->init(gas.get());solution->setTransport(transport);
        }
        AuditFlow flow(solution);flow.setFreeFlow();
        for(auto temperatures:{std::pair<double,double>{400,400},{400,450},{1200,1500},{1800,2000}}) {
            const double change=flow.check(temperatures.first,temperatures.second);
            if(stage!=1 && !(change>0))throw std::runtime_error("Nonideal option inactive");
            std::cout<<"stage="<<stage<<" left_T="<<temperatures.first
                <<" right_T="<<temperatures.second<<" relative_flux_change="<<change<<'\n';checks++;
        }
    }
    std::cout<<"PASS: "<<checks<<" actual Flow1D flux, ideal identity and mass-correction checks\n";
} catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
