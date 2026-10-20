#include "HydrogenTransport.h"
#include "cantera/base/Solution.h"
#include "cantera/transport/TransportFactory.h"
#include <iostream>
int main(int argc,char** argv) {
try {
    if(argc!=2)throw std::runtime_error("Usage: test-pairs INPUT");
    const std::string input=argv[1];
    auto pairs=hydrogen::readPairs(input+"/pairs.txt");
    std::ifstream table(input+"/species.txt");std::vector<liang::Species> parameters;
    liang::Species row;std::string name;
    while(table>>name>>row.Tc>>row.Pc>>row.Vc>>row.W>>row.omega>>row.eos)parameters.push_back(row);
    Cantera::TransportFactory::factory()->reg("hydrogen-test",[&](){
        auto* t=new hydrogen::Transport;t->pairs=pairs;t->parameters=parameters;t->stage=1;return t;
    });
    auto sol=Cantera::newSolution(input+"/ideal.yaml","","hydrogen-test");
    auto gas=sol->thermo();size_t n=gas->nSpecies(),checks=0;
    std::vector<double> d(n*n),mix(n),x(n);
    for(double T:{298.,500.,1000.,2000.,2500.})for(double p:{101325.,10132500.}) {
        gas->setState_TPX(T,p,"H2:2,O2:1,N2:3.761904761904762");
        sol->transport()->getBinaryDiffCoeffs(n,d.data());
        for(auto& pair:pairs) {
            size_t i=gas->speciesIndex(pair.first),j=gas->speciesIndex(pair.second);
            double logD=0;for(size_t k=0;k<4;k++)logD+=pair.d[k]*std::pow(std::log(T),int(k));
            double exact=std::exp(logD)*1e-4*101325/p;
            if(std::abs(d[i+n*j]/exact-1)>1e-12 || d[i+n*j]!=d[j+n*i])
                throw std::runtime_error("Author pair formula or symmetry mismatch");
            checks++;
        }
        sol->transport()->getMixDiffCoeffs(mix.data());gas->getMoleFractions(x.data());
        for(size_t k=0;k<n;k++) {
            double denom=0;for(size_t j=0;j<n;j++)if(k!=j)denom+=x[j]/d[k+n*j];
            const double exact=(gas->meanMolecularWeight()-x[k]*gas->molecularWeight(k))
                               /(gas->meanMolecularWeight()*denom);
            if(std::abs(mix[k]/exact-1)>1e-12)throw std::runtime_error("Mixture reduction mismatch");
            checks++;
        }
    }
    std::cout<<"PASS "<<checks<<" binary/mixture checks; author pairs="<<pairs.size()<<'\n';
}catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
