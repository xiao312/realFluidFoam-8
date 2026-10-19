#include "TakahashiTable.h"
#include <iostream>
#include <stdexcept>
namespace Cantera {double takahashiCorrectionFactor(double,double);}
int main(int argc,char**) {
    bool corrected=argc==1;
    double pr=3,tr=2;
    double expected=1.05*(1-.502100*std::pow(tr,-2.39031))*(1-.602907*std::pow(tr,-6.19043));
    auto value=[&](double p,double t){return Cantera::takahashiCorrectionFactor(p,t)
        +(corrected?liang::takahashiTable2Delta(p,t):0);};
    double actual=value(pr,tr);
    std::cout<<"Pr=3 Tr=2 expected="<<expected<<" actual="<<actual<<'\n';
    if(std::abs(expected-actual)>1e-12)return 1;
    for(double p:{.1,1.,2.5,4.,5.})for(double t:{1.,2.,5.})
        if(value(p,t)!=Cantera::takahashiCorrectionFactor(p,t))throw std::runtime_error("Unrelated row changed");
    for(double p:{2.5,3.,4.})
        if(std::abs(value(p+1e-8,2)-value(p-1e-8,2))>1e-7)throw std::runtime_error("Pressure interpolation discontinuity");
}
