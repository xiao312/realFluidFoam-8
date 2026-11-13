// Actual reader/kernel replay; fixed Z and rho, no transport or thermo feedback.
#include "fgmTableReader.H"
#include <iostream>
#include <iomanip>
#include <cstdlib>
int main(int argc,char**argv)
{
    if(argc!=6)return 2;
    Foam::fgm::fgmTableReader table(argv[1],Foam::fgm::fgmTableReader::CLAMP_TO_BOUNDS);
    const double z=std::stod(argv[2]),c=std::stod(argv[3]),rho=std::stod(argv[4]),dt=std::stod(argv[5]);
    const auto result=table.advanceSource(z,rho,c,dt);
    std::cout<<std::setprecision(17)<<"SOURCE_REPLAY {\"C_final\":"<<result.progress
      <<",\"elapsed_s\":"<<result.elapsed<<",\"crossings\":"<<result.crossedSegments
      <<",\"outward_boundary\":"<<(result.outwardBoundary?"true":"false")<<"}"<<std::endl;
    return 0;
}
