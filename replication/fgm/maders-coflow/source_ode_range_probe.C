#include "fgmSourceOde.H"
#include <cfenv>
#include <iostream>
#include <iomanip>
int main()
{
    feenableexcept(FE_DIVBYZERO|FE_INVALID|FE_OVERFLOW);
    const forgeFgm::FixedStateSource tiny({0,1},{1e-310,1});
    const auto result=tiny.advance(1,0,1e-7);
    const long double expected=1e-310L*std::expm1(1e-7L);
    if(result.outwardBoundary || result.elapsed!=1e-7 ||
       std::abs((long double)result.progress-expected)>1e-322L)return 2;
    const forgeFgm::FixedStateSource negative({-1,0},{-1,-1e-310});
    const auto reverse=negative.advance(1,0,1e-7);
    if(reverse.outwardBoundary || std::abs(reverse.progress+result.progress)>1e-322)return 3;
    const forgeFgm::FixedStateSource stiff({0,1},{1e-300,1e10});
    const auto event=stiff.advance(1,0,1e-7);
    if(!event.outwardBoundary || event.progress!=1 || !(event.elapsed>0 && event.elapsed<1e-7))return 4;
    const forgeFgm::FixedStateSource zero({0,1},{0,0});
    if(zero.advance(1,.5,1).progress!=.5)return 5;
    std::cout<<std::setprecision(17)<<"PASS source arithmetic with FPE traps; tiny progress="<<result.progress
             <<" eventTime="<<event.elapsed<<"\n";
}
