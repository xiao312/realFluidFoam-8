#include "fgmMappedSource.H"
#include <iostream>
#include <cfenv>
int main()
{
    feenableexcept(FE_INVALID|FE_DIVBYZERO|FE_OVERFLOW);
    const std::vector<double> eta{0,.25,.5,.75,1};
    const std::vector<double> ordinary{0,.1,.2,.3,.4}, rate{0,2,3,2,0};
    const auto a=forgeFgm::FixedStateSource(ordinary,rate).advance(2,.1,.001);
    const auto b=forgeFgm::advanceMappedSource(ordinary,eta,rate,2,.1,.001);
    if(a.progress!=b.progress||a.elapsed!=b.elapsed||a.outwardBoundary!=b.outwardBoundary)return 2;
    const double unit=std::numeric_limits<double>::denorm_min();
    const std::vector<double> tiny{0,0,unit,2*unit,2*unit}, zero(5,0);
    const auto cold=forgeFgm::advanceMappedSource(tiny,eta,zero,1181.27902984,0,5.9995200384e-10);
    if(cold.progress!=0||cold.outwardBoundary||cold.elapsed!=5.9995200384e-10)return 3;
    const std::vector<double> tinyRate(5,unit);
    const auto forward=forgeFgm::advanceMappedSource(tiny,eta,tinyRate,1,0,1);
    const std::vector<double> negative(5,-unit);
    const auto reverse=forgeFgm::advanceMappedSource(tiny,eta,negative,1,2*unit,1);
    if(forward.progress!=unit||reverse.progress!=unit)return 4;
    const double next=std::nextafter(1.,2.);
    const std::vector<double> offset{1,1,1,next,next};
    const auto stationary=forgeFgm::advanceMappedSource(offset,eta,zero,1,1,1);
    if(stationary.progress!=1||stationary.elapsed!=1)return 5;
    bool refused=false;
    try{forgeFgm::advanceMappedSource({0,0,-1,1,1},eta,zero,1,0,1);}
    catch(const std::invalid_argument&){refused=true;}
    if(!refused)return 6;
    std::cout<<"MAPPED_SOURCE normalParity=1 capturedCold=1 signedSubnormal=1 offsetCollapse=1 invalidRefused=1 PASS\n";
}
