#include "zRoundoffDecision.H"
#include <iostream>
#include <iomanip>

int main()
{
    const double e=std::numeric_limits<double>::epsilon();
    const double inputs[]={0,1,-64*e,1+64*e,0.25};
    const double expected[]={0,1,0,1,0.25};
    for (unsigned i=0;i<5;++i)
        if (forgeZRoundoff::projected(inputs[i])!=expected[i]) return 1;
    const double invalid[]={-65*e,1+65*e,1+4.6458263902593444e-9,
        std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()};
    for (double value:invalid)
    {
        double state=value;
        bool refused=false;
        try { forgeZRoundoff::requireRange(value,value,0); state=0; }
        catch (const std::runtime_error&) { refused=true; }
        if (!refused || (std::isnan(value) ? !std::isnan(state) : state!=value)) return 2;
    }
    bool invalidWeightRefused=false;
    try { forgeZRoundoff::requireRange(0,1,1); }
    catch (const std::runtime_error&) { invalidWeightRefused=true; }
    if (!invalidWeightRefused) return 3;
    std::cout << std::setprecision(17) << "Z_ROUNDOFF_PROBE allowed=5 refused=6 limit="
        << forgeZRoundoff::limit() << " materialStateUnchanged=1\n";
    return 0;
}
