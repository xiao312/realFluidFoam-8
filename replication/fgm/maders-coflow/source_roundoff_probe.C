// Replays the actual first-step pure-fuel trace; strict API stays strict.
#include "fgmTableReader.H"
#include <iostream>
#include <stdexcept>
#include <limits>
#include <cmath>
int main(int argc,char** argv)
{
    if(argc!=2)return 2;
    Foam::fgm::fgmTableReader reader(argv[1]);
    const double trace=1.3446198218333e-172;
    bool strictRefused=false;
    try {reader.advanceSource(1,.87636884163194,trace,5.9999952e-8);}
    catch(const std::out_of_range&) {strictRefused=true;}
    if(!strictRefused)return 3;
    for(double value:{trace,-trace,32*std::numeric_limits<double>::epsilon(),
                      -32*std::numeric_limits<double>::epsilon()})
    {
        const double projected=reader.projectSourceRoundoff(1,value);
        if(projected!=0)return 4;
        const auto result=reader.advanceSource(1,.87636884163194,projected,5.9999952e-8);
        if(result.progress!=0 || result.outwardBoundary || result.elapsed!=5.9999952e-8)return 5;
    }
    for(double value:{1e-8,-1e-8,128*std::numeric_limits<double>::epsilon(),
                      std::numeric_limits<double>::quiet_NaN()})
    {
        bool refused=false;
        try {reader.projectSourceRoundoff(1,value);}
        catch(const std::exception&) {refused=true;}
        if(!refused)return 6;
    }
    if(reader.projectSourceRoundoff(1,0)!=0)return 7;
    std::cout<<"PASS actual-reader strict rejection; trace projection; material/nonfinite refusal; zero-source advance\n";
    return 0;
}
