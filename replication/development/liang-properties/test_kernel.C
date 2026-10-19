#include "ElyHanley.H"
#include <cassert>
#include <iostream>
int main() {
    using namespace rfElyHanley;
    Species s={referenceTc,referenceZc*R*referenceTc/referenceVc,referenceVc,referenceW,referenceOmega,3.5};
    for(double T:{120.,300.,1000.}) for(double V:{.05,.5,50.}) {
        const double k=conductivity(T,V,{s},{1},{V});
        const double expected=referenceConductivity(referenceW/V*1e-3,T)
            +referenceViscosity(T)/referenceW*1.32*R;
        assert(std::abs(k/expected-1)<1e-12);
        const double split=conductivity(T,V,{s,s},{.2,.8},{V,V});
        assert(std::abs(split/k-1)<1e-12);
    }
    bool caught=false;
    try {conductivity(300,1,{s},{.9},{1});}catch(const std::domain_error&){caught=true;}
    assert(caught);
    std::cout<<"PASS: reference-fluid limit, species splitting and invalid input rejection\n";
}
