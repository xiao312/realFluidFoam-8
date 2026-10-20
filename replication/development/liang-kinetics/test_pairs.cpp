#include "PairTransport.h"
#include "cantera/base/Solution.h"
#include "cantera/transport/TransportFactory.h"
#include <iostream>

int main(int argc,char** argv) {
try {
    if(argc!=3)throw std::runtime_error("Usage: test-pairs MECHANISM PAIRS");
    const auto pairs=kinetics_control::readPairs(argv[2]);
    Cantera::TransportFactory::factory()->reg("test-author-pairs",[&](){
        auto* t=new kinetics_control::PairTransport;t->pairs=pairs;return t;});
    auto corrected=Cantera::newSolution(argv[1],"","test-author-pairs");
    auto original=Cantera::newSolution(argv[1],"","mixture-averaged");
    auto gas=corrected->thermo();const size_t n=gas->nSpecies();
    std::vector<double> binary(n*n),mixture(n),x(n);
    size_t checks=0;double largestError=0;
    for(double temperature:{298.,500.,1000.,2000.,2500.}) {
        for(double pressure:{101325.,10132500.}) {
            for(auto solution:{corrected,original})
                solution->thermo()->setState_TPX(temperature,pressure,"CH4:1,O2:2,N2:7.52,H2:0.1");
            corrected->transport()->getBinaryDiffCoeffs(n,binary.data());
            for(const auto& pair:pairs) {
                const size_t i=gas->speciesIndex(pair.first),j=gas->speciesIndex(pair.second);
                double exponent=0;
                for(size_t k=0;k<4;k++)
                    exponent+=pair.coefficients[k]*std::pow(std::log(temperature),int(k));
                const double expected=1e-4*101325/pressure*std::exp(exponent);
                largestError=std::max(largestError,std::abs(binary[i+n*j]/expected-1));
                if(binary[i+n*j]!=binary[j+n*i])throw std::runtime_error("Pair symmetry failure");
                checks++;
            }
            gas->getMoleFractions(x.data());
            corrected->transport()->getMixDiffCoeffs(mixture.data());
            for(size_t i=0;i<n;i++) {
                double denominator=0;
                for(size_t j=0;j<n;j++)if(i!=j)denominator+=x[j]/binary[i+n*j];
                const double expected=(gas->meanMolecularWeight()-x[i]*gas->molecularWeight(i))
                    /(gas->meanMolecularWeight()*denominator);
                largestError=std::max(largestError,std::abs(mixture[i]/expected-1));checks++;
            }
            const double lambda=corrected->transport()->thermalConductivity();
            const double reference=original->transport()->thermalConductivity();
            largestError=std::max(largestError,std::abs(lambda/reference-1));checks++;
        }
    }
    auto* transport=dynamic_cast<kinetics_control::PairTransport*>(corrected->transport().get());
    if(largestError>1e-12 || transport->pairUpdates==0)
        throw std::runtime_error("Author-pair transport verification failed");
    std::cout<<"PASS checks "<<checks<<" largest_relative_error "<<largestError
             <<" pairs "<<pairs.size()<<" updates "<<transport->pairUpdates<<std::endl;
} catch(const std::exception& error) {std::cerr<<error.what()<<std::endl;return 1;}
}
