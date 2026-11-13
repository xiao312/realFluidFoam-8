// Actual-reader replay of job127801087; does not replace a clean-start CFD run.
#include "fgmTableReader.H"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
int main(int argc,char** argv)
{
    if(argc!=2)return 2;
    using Foam::fgm::fgmTableReader;
    fgmTableReader strict(argv[1]);
    fgmTableReader bounded(argv[1],fgmTableReader::CLAMP_TO_BOUNDS);
    const double Z=.14312663723114,C=.17343764148411,rho=.15948475089795,dt=4.7124470511563e-5;
    bool refused=false;
    try {strict.projectSourceRoundoff(Z,C);}
    catch(const std::out_of_range&) {refused=true;}
    if(!refused)return 3;
    std::vector<double> coordinates,sources;
    bounded.sourceCurve(Z,coordinates,sources);
    const double projected=bounded.boundSourceProgress(Z,C);
    if(projected!=coordinates.back() || !(C>projected))return 4;
    const auto result=bounded.advanceSource(Z,rho,projected,dt);
    if(!std::isfinite(result.progress) || result.progress<coordinates.front()
       || result.progress>coordinates.back())return 5;
    for(double z:{0.,1.,-1e-8,1.+1e-8})
    {
        const double c=bounded.boundSourceProgress(z,1e-7);
        const auto edge=bounded.advanceSource(z,1,c,dt);
        if(!std::isfinite(edge.progress))return 6;
    }
    bool invalid=false;
    try {bounded.boundSourceProgress(Z,std::numeric_limits<double>::quiet_NaN());}
    catch(const std::exception&) {invalid=true;}
    if(!invalid)return 7;
    const auto outward=forgeFgm::FixedStateSource({0.,1.},{1.,1.}).advance(1.,.99,1.);
    if(!outward.outwardBoundary || outward.progress!=1. || outward.elapsed>=1.)return 8;
    std::cout.precision(17);
    std::cout<<"PASS actual-reader failed-state replay C="<<C<<" bounded="<<projected
             <<" correction="<<projected-C<<" outward="<<result.outwardBoundary
             <<"; strict diagnostic retained; finite endpoint holding; invalid input rejected\n";
    return 0;
}
