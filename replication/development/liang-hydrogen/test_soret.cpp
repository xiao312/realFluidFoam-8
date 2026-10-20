#include "HydrogenTransport.h"
#include "../cantera-liang/SoretCompatibleFlow.h"
#include "../cantera-liang/TotalEnthalpyFlow.h"
#include "cantera/thermo/ThermoFactory.h"
#include "cantera/transport/TransportFactory.h"
#include <iomanip>
#include <iostream>
#include <numeric>
using namespace Cantera;

void require(bool condition,const std::string& message) {
    if(!condition)throw std::runtime_error(message);
}
double relative(const std::vector<double>& a,const std::vector<double>& b) {
    double difference=0,scale=1e-100;
    require(a.size()==b.size(),"Vector size mismatch");
    for(size_t k=0;k<a.size();k++) {
        difference=std::max(difference,std::abs(a[k]-b[k]));
        scale=std::max({scale,std::abs(a[k]),std::abs(b[k])});
    }
    return difference/scale;
}
class Probe : public hydrogen::Transport {
public:
    liang::CollisionRatios collision(size_t first,size_t second,double temperature) {
        return manualCollisionRatios(first,second,temperature);
    }
};
template<class Base>
class FaceProbe : public liang::SoretCompatibleFlow<Base> {
public:
    using liang::SoretCompatibleFlow<Base>::SoretCompatibleFlow;
    std::vector<double> flux(double left,double right,const std::vector<double>& y,bool enabled) {
        this->setFreeFlow();this->setPressure(100*OneAtm);
        const double grid[]={0,.001,.002};this->setupGrid(3,grid);
        std::vector<double> state(3*this->nComponents(),0.);
        for(size_t j=0;j<3;j++) {
            state[this->index(c_offset_T,j)]=j?right:left;
            state[this->index(c_offset_U,j)]=.1;
            for(size_t k=0;k<y.size();k++)state[this->index(c_offset_Y+k,j)]=y[k];
        }
        this->enableSoret(enabled);this->_finalize(state.data());
        require(this->withSoret()==enabled,"Finalize changed Soret flag");
        this->updateProperties(npos,state.data(),0,2);
        std::vector<double> result(y.size());
        for(size_t k=0;k<y.size();k++)result[k]=this->m_flux(k,0);
        return result;
    }
};
template<class Flow>
void faceChecks(Flow& flow,const std::vector<double>& y,size_t light) {
    auto forward=flow.flux(600,1200,y,true),reverse=flow.flux(1200,600,y,true);
    auto uniform=flow.flux(900,900,y,true),off=flow.flux(600,1200,y,false);
    require(forward[light]>1e-12,"Light species does not diffuse toward hotter gas");
    for(size_t k=0;k<y.size();k++) {
        reverse[k]=-reverse[k];
        require(std::abs(uniform[k])+std::abs(off[k])<1e-14,"Unexpected uniform-state flux");
    }
    require(relative(forward,reverse)<1e-12,"Gradient reversal failed");
    require(std::abs(std::accumulate(forward.begin(),forward.end(),0.))<1e-10*forward[light],
            "Native thermal mass closure failed");
}

int main(int argc,char** argv) {
try {
    require(argc==3,"Usage: test-soret INPUTS FIXTURES.csv");
    const std::string input=argv[1];
    const auto pairs=hydrogen::readPairs(input+"/pairs.txt");
    const auto collisions=hydrogen::readCollisionPairs(input+"/collision-pairs.txt");
    std::ifstream table(input+"/species.txt");std::vector<liang::Species> parameters;
    liang::Species item;std::string name;
    while(table>>name>>item.Tc>>item.Pc>>item.Vc>>item.W>>item.omega>>item.eos)
        parameters.push_back(item);
    require(parameters.size()==13,"Expected thirteen Burke species");
    ThermoFactory::factory()->reg("liang-srk",[](){auto* g=new liang::SrkPhase;g->stage=1;return g;});
    TransportFactory::factory()->reg("hydrogen-soret-test",[&](){
        auto* tr=new Probe;tr->pairs=pairs;tr->collisionPairs=collisions;
        tr->parameters=parameters;tr->stage=1;tr->manualSoret=true;
        tr->boundedTakahashi=true;tr->table2=true;tr->denseIncrementOnly=true;return tr;
    });
    auto ideal=newSolution(input+"/ideal.yaml","","hydrogen-soret-test");
    auto real=newSolution(input+"/srk.yaml","","hydrogen-soret-test");
    auto& srk=dynamic_cast<liang::SrkPhase&>(*real->thermo());
    srk.parameters=parameters;srk.stage=3;
    auto& gas=*ideal->thermo();auto& tr=dynamic_cast<Probe&>(*ideal->transport());
    const size_t n=gas.nSpecies();
    std::ifstream fixtures(argv[2]);std::string line;std::getline(fixtures,line);
    require(line=="first,second,T_K,Astar,Bstar,Cstar,q","Unexpected fixture schema");
    size_t count=0;double maxCoefficientError=0,maxCollisionError=0;
    while(std::getline(fixtures,line)) {
        std::replace(line.begin(),line.end(),',',' ');
        std::istringstream row(line);std::string first,second;double T,a,b,c,q;
        require(bool(row>>first>>second>>T>>a>>b>>c>>q),"Malformed independent fixture");
        const size_t light=gas.speciesIndex(first),partner=gas.speciesIndex(second);
        require(light<n && partner<n,"Unknown fixture species");
        const auto value=tr.collision(light,partner,T),swapped=tr.collision(partner,light,T);
        maxCollisionError=std::max(maxCollisionError,relative({value.a,value.b,value.c},{a,b,c}));
        require(relative({value.a,value.b,value.c},{swapped.a,swapped.b,swapped.c})<1e-14,
                "Collision lookup is not symmetric");
        const double calculated=liang::lightSpeciesPairFactor(value,gas.molecularWeight(light),
                                                             gas.molecularWeight(partner));
        require(std::abs(calculated-q)<1e-12,"Independent pair-factor fixture failed");
        std::vector<double> low;
        for(auto solution:{ideal,real})for(int stage:{1,5})for(double pressure:{OneAtm,100*OneAtm}) {
            if(solution==real && stage==1)continue;
            auto& phase=*solution->thermo();auto& transport=dynamic_cast<Probe&>(*solution->transport());
            transport.stage=stage;transport.manualSoret=true;
            phase.setState_TPX(T,pressure,first+":0.01,"+second+":0.99");
            std::vector<double> y(n),matrix(n*n),dt(n),expected(n),ordinary(n),without(n);
            phase.getMassFractions(y.data());transport.getThermalDiffCoeffs(dt.data());
            transport.getBinaryDiffCoeffs(n,matrix.data());transport.getMixDiffCoeffs(ordinary.data());
            // Independent binary reduction from the actual selected-stage matrix.
            const double dm=(1-y[light])*matrix[light+n*partner]/.99;
            const double raw=phase.density()*dm*phase.molecularWeight(light)/phase.meanMolecularWeight()
                             *.01*.99*q;
            expected[light]=raw;
            for(size_t k=0;k<n;k++)expected[k]-=y[k]*raw;
            maxCoefficientError=std::max(maxCoefficientError,relative(dt,expected));
            const double lambda=transport.thermalConductivity(),mu=transport.viscosity();
            transport.manualSoret=false;transport.getMixDiffCoeffs(without.data());
            require(ordinary==without && lambda==transport.thermalConductivity()
                    && mu==transport.viscosity(),"Thermal option changed ordinary transport");
            transport.manualSoret=true;
            if(solution==ideal && stage==1) {
                if(pressure==OneAtm)low=dt;
                else require(relative(dt,low)<1e-12,"Ideal dilute pressure invariance failed");
            }
        }
        count++;
    }
    require(count==15 && maxCollisionError<1e-12 && maxCoefficientError<1e-10,
            "Independent fixture coverage or accuracy failed");
    gas.setState_TPX(900,100*OneAtm,"H2:0.01,N2:0.99");
    std::vector<double> y(n);gas.getMassFractions(y.data());tr.stage=1;
    for(bool manual:{false,true}) {
        tr.manualSoret=manual;
        dynamic_cast<Probe&>(*real->transport()).manualSoret=manual;
        FaceProbe<Flow1D> normal(ideal,"flow");faceChecks(normal,y,gas.speciesIndex("H2"));
        FaceProbe<liang::TotalEnthalpyFlow> enthalpy(real,false);
        faceChecks(enthalpy,y,gas.speciesIndex("H2"));
    }
    for(auto solution:{ideal,real}) {
        auto& phase=*solution->thermo();auto& transport=dynamic_cast<Probe&>(*solution->transport());
        phase.setState_TPX(1000,100*OneAtm,"N2:1");
        std::vector<double> dt(n);transport.getThermalDiffCoeffs(dt.data());
        require(std::all_of(dt.begin(),dt.end(),[](double v){return v==0;}),"Absent-light limit failed");
    }
    // A truncated, duplicate or nonfinite sidecar must not become a partial override.
    std::ifstream rawFile(input+"/collision-pairs.txt");
    std::string raw((std::istreambuf_iterator<char>(rawFile)),{});
    for(const auto& bad:std::vector<std::string>{
            raw.substr(0,raw.find('\n')),raw+raw.substr(0,raw.find('\n'))+"\n","H2 N2 nan\n"}) {
        bool failed=false;
        try {std::istringstream stream(bad);hydrogen::parseCollisionPairs(stream);}
        catch(const std::exception&) {failed=true;}
        require(failed,"Malformed collision sidecar was accepted");
    }
    for(bool unknown:{false,true}) {
        Probe invalid;invalid.parameters=parameters;invalid.pairs=pairs;
        invalid.collisionPairs=collisions;
        if(unknown)invalid.collisionPairs[0].first="UNKNOWN_SPECIES";
        else invalid.pairs.pop_back();
        bool failed=false;
        try {invalid.init(&gas);}
        catch(const std::exception&) {failed=true;}
        require(failed,"Invalid pair inventory was accepted");
    }
    std::cout<<std::setprecision(16)<<"PASS fixtures "<<count<<" collision_error "<<maxCollisionError
             <<" coefficient_error "<<maxCoefficientError
             <<" pressure_ordinary_transport_native_flux_and_parser_checks passed\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
