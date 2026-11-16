#include "pressureDampingFactor.H"
#include <vector>
#include <iostream>
#include <limits>

int main()
{
    const std::vector<double> base{2,1}, neutral{1.5,1.25}, bad{-2,3};
    if (Foam::pressureDensityDampingFactor(base,base)!=1) return 1;
    if (Foam::pressureDensityDampingFactor(base,neutral)!=1) return 2;
    const double factor=Foam::pressureDensityDampingFactor(base,bad);
    const double a=base[0]+factor*(bad[0]-base[0]);
    const double b=base[1]+factor*(bad[1]-base[1]);
    // Volumes1 and2: a conservative transfer has initial/final total mass4.
    if (std::abs(factor-.45)>1e-14 || a<=0 || b<=0 || std::abs(a+2*b-4)>1e-14) return 3;
    bool invalidBase=false,invalidTrial=false;
    try { Foam::pressureDensityDampingFactor(std::vector<double>{0,1},bad); }
    catch (const std::invalid_argument&) { invalidBase=true; }
    try { Foam::pressureDensityDampingFactor(base,std::vector<double>{std::numeric_limits<double>::quiet_NaN(),1}); }
    catch (const std::invalid_argument&) { invalidTrial=true; }
    if (!invalidBase || !invalidTrial) return 4;
    std::cout<<"pressure-damping-factor checks=5 alpha="<<factor
        <<" retainedDensities="<<a<<','<<b<<" mass=4 scientificAcceptance=0\n";
    return 0;
}
