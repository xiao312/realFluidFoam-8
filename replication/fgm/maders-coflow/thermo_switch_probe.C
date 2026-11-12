// Actual selected OF8 thermodynamics; no field write or coefficient adjustment.
#include "fvCFD.H"
#include "psiReactionThermo.H"
#include <cmath>
#include <cstdlib>
#include <iostream>
int main(int argc,char** argv)
{
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    std::cout.precision(17);
    if(runTime.value()!=0 || !std::getenv("SLURM_JOB_ID"))return 2;
    autoPtr<psiReactionThermo> model(psiReactionThermo::New(mesh));
    psiReactionThermo& thermo=model();
    auto& ys=thermo.composition().Y();
    forAll(ys,i)ys[i][0]=thermo.composition().species()[i]=="N2" ? 1 : 0;
    scalar worstFirst=0,worstSecond=0;
    for(const scalar target:{999.9998,1000.0002,1000.001})
    {
        volScalarField desired(thermo.T());desired[0]=target;
        const scalar held=thermo.he(thermo.p(),desired)()[0];
        thermo.he()[0]=held;thermo.T()[0]=target<1000 ? 1000.01 : 999.99;
        thermo.correct();
        const scalar firstT=thermo.T()[0];
        const scalar firstError=mag(thermo.he(thermo.p(),thermo.T())()[0]-held);
        thermo.correct();
        const scalar secondError=mag(thermo.he(thermo.p(),thermo.T())()[0]-held);
        if(thermo.he()[0]!=held)return 3;
        worstFirst=max(worstFirst,firstError);worstSecond=max(worstSecond,secondError);
        std::cout<< "NASA_SWITCH target="<<target<<" firstT="<<firstT
            <<" firstError_J_kg="<<firstError<<" secondT="<<thermo.T()[0]
            <<" secondError_J_kg="<<secondError<<" storedHUnchanged=1"<<std::endl;
    }
    if(!(worstFirst>.1) || worstSecond>1e-6)return 4;
    std::cout<<"PASS runtime inversion refinement reproduces switch residual and removes it at unchanged h"<<std::endl;
    return 0;
}
