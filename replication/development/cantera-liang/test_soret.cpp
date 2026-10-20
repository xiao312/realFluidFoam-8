#include "SoretCompatibleFlow.h"
#include "TotalEnthalpyFlow.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/transport/TransportFactory.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
using namespace Cantera;

void require(bool condition,const std::string& message) {
    if(!condition)throw std::runtime_error(message);
}
double relative(const std::vector<double>& a,const std::vector<double>& b) {
    double error=0,scale=1e-100;
    for(size_t k=0;k<a.size();k++) {
        error=std::max(error,std::abs(a[k]-b[k]));
        scale=std::max({scale,std::abs(a[k]),std::abs(b[k])});
    }
    return error/scale;
}
class CoefficientProbe : public liang::StagedTransport {
public:
    std::vector<double> independent(bool project) {
        const auto& w=m_thermo->molecularWeights();
        std::vector<double> x(m_nsp),y(m_nsp),mu(m_nsp),dm(m_nsp),binary(m_nsp*m_nsp);
        m_thermo->getMoleFractions(x.data());m_thermo->getMassFractions(y.data());
        getSpeciesViscosities(mu.data());getMixDiffCoeffs(dm.data());
        // Deliberately request the dilute matrix even for the Case 5 control.
        GasTransport::getBinaryDiffCoeffs(m_nsp,binary.data());
        std::vector<double> a(m_nsp),raw(m_nsp);
        for(size_t k=0;k<m_nsp;k++) {
            if(y[k]<Tiny)continue;
            double sum=0;
            for(size_t j=0;j<m_nsp;j++)if(j!=k) {
                double wilke=std::pow(1+std::sqrt(mu[k]/mu[j])*std::pow(w[j]/w[k],.25),2)
                    /std::sqrt(8*(1+w[k]/w[j]));
                sum+=std::max(Tiny,x[j])*wilke;
            }
            a[k]=3.75*mu[k]/w[k]/(1+1.065*sum/std::max(Tiny,x[k]));
        }
        for(size_t k=0;k<m_nsp;k++) {
            double sum=0;
            for(size_t j=0;j<m_nsp;j++)if(j!=k) {
                double ap[9],bp[9],cp[9];
                getCollisionIntegralPolynomial(k,j,ap,bp,cp);
                require(!CKMode(),"Probe requires native nine-term collision fits");
                const double logReduced=std::log(Boltzmann*m_thermo->temperature()/m_epsilon(k,j));
                double c=cp[8];
                for(int n=7;n>=0;n--)c=c*logReduced+cp[n];
                sum+=(1.2*c-1)/(binary[k+m_nsp*j]*(w[k]+w[j]))*(y[k]*a[j]-y[j]*a[k]);
            }
            raw[k]=dm[k]*w[k]*m_thermo->meanMolecularWeight()*sum;
        }
        if(project) {
            double sum=std::accumulate(raw.begin(),raw.end(),0.);
            for(size_t k=0;k<m_nsp;k++)raw[k]-=y[k]*sum;
        }
        return raw;
    }
};

template<class Base>
class FlowProbe : public liang::SoretCompatibleFlow<Base> {
public:
    using liang::SoretCompatibleFlow<Base>::SoretCompatibleFlow;
    std::vector<double> face(double left,double right,const std::vector<double>& y,bool soret) {
        this->setFreeFlow();this->setPressure(100*OneAtm);
        double grid[]={0,.001,.002};this->setupGrid(3,grid);
        std::vector<double> state(3*this->nComponents(),0.);
        for(size_t j=0;j<3;j++) {
            state[this->index(c_offset_T,j)]=j==0?left:right;
            state[this->index(c_offset_U,j)]=.1;
            for(size_t k=0;k<y.size();k++)state[this->index(c_offset_Y+k,j)]=y[k];
        }
        this->enableSoret(soret);
        this->_finalize(state.data());
        require(this->withSoret()==soret,"Finalize changed the Soret flag");
        this->updateProperties(npos,state.data(),0,2);
        std::vector<double> out(y.size());
        for(size_t k=0;k<y.size();k++)out[k]=this->m_flux(k,0);
        return out;
    }
};

template<class Flow>
void fluxChecks(Flow& flow,const std::vector<double>& y) {
    auto uniform=flow.face(900,900,y,true);
    auto off=flow.face(600,1200,y,false);
    auto forward=flow.face(600,1200,y,true);
    auto reverse=flow.face(1200,600,y,true);
    double scale=0,net=0;
    for(size_t k=0;k<y.size();k++) {
        require(std::abs(uniform[k])<1e-15,"Uniform-temperature thermal flux");
        require(std::abs(off[k])<1e-15,"Uniform-composition ordinary flux");
        scale=std::max(scale,std::abs(forward[k]));net+=forward[k];
        reverse[k]=-reverse[k];
    }
    require(scale>1e-12,"Soret flux was not exercised");
    require(relative(forward,reverse)<1e-12,"Temperature-gradient reversal");
    require(std::abs(net)<1e-11*scale,"Thermal mass-flux closure");
}

void manualChecks(const std::shared_ptr<Solution>& sol,CoefficientProbe& transport,
                  liang::SrkPhase& gas,const std::filesystem::path& inputs) {
    // Independently evaluated source-formula fixtures; no flame target enters.
    const double temperatures[]={298.,1000.,3000.};
    const double qExpected[]={-.4231890148511275,-.47590044927061853,-.4927708434650581};
    const double wellDepth=60.87807487100754;
    const size_t light=gas.speciesIndex("H2"),partner=gas.speciesIndex("N2"),n=gas.nSpecies();
    // SrkPhase::stage controls calorics; populated parameters always activate
    // its EOS. Use an actual ideal phase for the ideal pressure-invariance check.
    auto idealSolution=newSolution((inputs/"ideal.yaml").string(),"","liang-staged");
    auto& idealGas=*idealSolution->thermo();
    auto& idealTransport=dynamic_cast<CoefficientProbe&>(*idealSolution->transport());
    idealTransport.manualSoret=true;idealTransport.stage=4;
    transport.manualSoret=true;transport.stage=4;
    double maximum=0;
    std::vector<double> binaryY;
    for(size_t row=0;row<3;row++) {
        const auto ratios=liang::lightSpeciesCollisionRatios(std::log(temperatures[row]/wellDepth));
        const double q=liang::lightSpeciesPairFactor(ratios,2.016,28.014);
        require(std::abs(q-qExpected[row])<1e-13,"Published manual pair fixture");
        require(liang::lightSpeciesPairFactor(ratios,2.016,2.016)==0,"Self-pair limit");
        require(std::abs(q+liang::lightSpeciesPairFactor(ratios,28.014,2.016))<1e-15,
                "Pair permutation");
        std::vector<double> first;
        for(double pressure:{OneAtm,100*OneAtm}) {
            idealGas.setState_TPX(temperatures[row],pressure,"H2:0.01,N2:0.99");
            std::vector<double> dt(n),matrix(n*n),y(n),x(n),expected(n,0.);
            idealGas.getMassFractions(y.data());idealGas.getMoleFractions(x.data());
            idealTransport.getThermalDiffCoeffs(dt.data());
            idealTransport.getBinaryDiffCoeffs(n,matrix.data());
            const double dm=(1-y[light])*matrix[light+n*partner]/x[partner];
            const double raw=idealGas.density()*dm*idealGas.molecularWeight(light)/idealGas.meanMolecularWeight()
                             *x[light]*x[partner]*qExpected[row];
            expected[light]=raw;
            for(size_t k=0;k<n;k++)expected[k]-=y[k]*raw;
            maximum=std::max(maximum,relative(dt,expected));
            require(dt[light]<0 && dt[partner]>0,"Published hotward sign");
            if(pressure==OneAtm)first=dt;
            else maximum=std::max(maximum,relative(first,dt));
            binaryY=y;
        }
    }
    require(maximum<1e-10,"Manual binary coefficient/pressure qualification: "+std::to_string(maximum));
    // Density scaling and selected corrected diffusivity are independent choices.
    gas.stage=4;
    gas.setState_TPX(1000,100*OneAtm,"H2:0.01,N2:0.99");
    for(int stage:{4,5}) {
        transport.stage=stage;
        std::vector<double> dt(n),matrix(n*n),y(n),expected(n,0.);
        gas.getMassFractions(y.data());transport.getThermalDiffCoeffs(dt.data());
        transport.getBinaryDiffCoeffs(n,matrix.data());
        const double dm=(1-y[light])*matrix[light+n*partner]/.99;
        const double raw=gas.density()*dm*gas.molecularWeight(light)/gas.meanMolecularWeight()
                         *.01*.99*qExpected[1];
        expected[light]=raw;
        for(size_t k=0;k<n;k++)expected[k]-=y[k]*raw;
        require(relative(dt,expected)<1e-10,"Selected-stage manual coefficient");
    }
    gas.setState_TPX(1000,100*OneAtm,"N2:1");
    std::vector<double> absent(n);transport.getThermalDiffCoeffs(absent.data());
    require(std::all_of(absent.begin(),absent.end(),[](double value){return value==0;}),
            "Absent-light-species limit");
    FlowProbe<Flow1D> flow(sol,"flow");fluxChecks(flow,binaryY);
    require(flow.face(600,1200,binaryY,true)[light]>0,"Native hotward thermal mass flux");
    FlowProbe<liang::TotalEnthalpyFlow> enthalpy(sol,false);fluxChecks(enthalpy,binaryY);
    transport.manualSoret=false;
    std::cout<<std::setprecision(16)<<"manual_soret_binary_error "<<maximum
             <<" selected_stage_and_native_flux_checks passed\n";
}

int main(int argc,char** argv) {
try {
    require(argc==3,"Usage: test-soret INPUTS SOLVED_PROFILE");
    std::filesystem::path inputs=argv[1];
    std::ifstream table(inputs/"species.txt");
    std::vector<liang::Species> parameters;std::vector<std::string> names;
    liang::Species item;std::string name;
    while(table>>name>>item.Tc>>item.Pc>>item.Vc>>item.W>>item.omega>>item.eos) {
        names.push_back(name);parameters.push_back(item);
    }
    require(names.size()==53,"Expected 53 named GRI species");
    ThermoFactory::factory()->reg("liang-srk",[](){auto* g=new liang::SrkPhase;g->stage=1;return g;});
    TransportFactory::factory()->reg("liang-staged",[&](){
        auto* tr=new CoefficientProbe;tr->parameters=parameters;tr->stage=4;
        tr->denseIncrementOnly=true;tr->boundedTakahashi=true;tr->table2=true;return tr;});
    auto sol=newSolution((inputs/"srk.yaml").string(),"","liang-staged");
    auto* gas=dynamic_cast<liang::SrkPhase*>(sol->thermo().get());
    auto* tr=dynamic_cast<CoefficientProbe*>(sol->transport().get());
    require(gas && tr,"Missing diagnostic adapters");gas->parameters=parameters;gas->stage=4;
    auto ideal=newSolution((inputs/"ideal.yaml").string(),"","mixture-averaged");
    std::ifstream profile(argv[2]);std::string line;std::getline(profile,line);
    auto fields=[](const std::string& text) {
        std::stringstream in(text);std::string value;std::vector<std::string> out;
        while(std::getline(in,value,',')){if(!value.empty()&&value.back()=='\r')value.pop_back();out.push_back(value);}
        return out;
    };
    auto header=fields(line);
    require(header.size()==60 || header.size()==58,"Profile width");
    const size_t offset=header.size()-53;
    for(size_t k=0;k<53;k++)
        require(header[k+offset]==(offset==7?"Y_":"")+names[k],"Profile species order");
    std::vector<std::vector<double>> rows;
    while(std::getline(profile,line)) {
        auto values=fields(line);require(values.size()==header.size(),"Profile row width");
        std::vector<double> row;for(const auto& v:values)row.push_back(std::stod(v));rows.push_back(row);
    }
    require(rows.size()>10,"Insufficient profile states");
    double maxError=0,maxPressure=0,maxStock=0,maxProjection=0;
    size_t checked=0;
    std::vector<double> testY;
    for(double target:{298.,400.,600.,900.,1200.,1500.,1800.,2100.}) {
        const auto& row=*std::min_element(rows.begin(),rows.end(),[&](const auto& a,const auto& b){
            return std::abs(a[1]-target)<std::abs(b[1]-target);});
        std::vector<double> y(row.begin()+offset,row.end());
        for(auto& value:y)value=std::max(0.,value);
        double sum=std::accumulate(y.begin(),y.end(),0.);for(auto& value:y)value/=sum;
        std::vector<double> low;
        for(double p:{OneAtm,100*OneAtm}) {
            gas->setState_TPY(row[1],p,y.data());
            ideal->thermo()->setState_TPY(row[1],p,y.data());
            tr->stage=4;
            std::vector<double> dt4(53),stock(53),d4(53),d5(53),dt5(53);
            tr->getThermalDiffCoeffs(dt4.data());
            maxError=std::max(maxError,relative(dt4,tr->independent(true)));
            ideal->transport()->getThermalDiffCoeffs(stock.data());
            maxStock=std::max(maxStock,relative(dt4,stock));
            if(p==OneAtm)low=dt4;
            else maxPressure=std::max(maxPressure,relative(low,dt4));
            auto raw=tr->independent(false);tr->getMixDiffCoeffs(d4.data());
            tr->stage=5;tr->getMixDiffCoeffs(d5.data());tr->getThermalDiffCoeffs(dt5.data());
            maxError=std::max(maxError,relative(dt5,tr->independent(true)));
            for(size_t k=0;k<53;k++)raw[k]*=d5[k]/d4[k];
            double total=std::accumulate(raw.begin(),raw.end(),0.);
            for(size_t k=0;k<53;k++)raw[k]-=y[k]*total;
            maxProjection=std::max(maxProjection,relative(dt5,raw));checked++;
        }
        if(target==1200)testY=y;
    }
    require(std::max({maxError,maxPressure,maxStock,maxProjection})<1e-10,"Coefficient qualification failed");
    tr->stage=5;
    FlowProbe<Flow1D> flow(sol,"flow");fluxChecks(flow,testY);
    FlowProbe<liang::TotalEnthalpyFlow> enthalpy(sol,false);fluxChecks(enthalpy,testY);
    // Native mixture transport must retain its original finalize path too.
    FlowProbe<Flow1D> stockFlow(ideal,"flow");fluxChecks(stockFlow,testY);
    manualChecks(sol,*tr,*gas,inputs);
    std::cout<<std::setprecision(16)<<"states "<<checked<<" coefficient_error "<<maxError
        <<" pressure_error "<<maxPressure<<" stock_error "<<maxStock
        <<" projection_error "<<maxProjection<<" native_and_custom_flux_checks passed\n";
} catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
