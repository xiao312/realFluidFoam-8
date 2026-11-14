#include "fvCFD.H"
#include "psiReactionThermo.H"
#include "mixedFvPatchFields.H"
#include <fstream>
#include <iomanip>

int main(int argc,char *argv[])
{
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    if(runTime.value()!=0) FatalErrorInFunction<<"Fresh time zero required"<<exit(FatalError);
    autoPtr<psiReactionThermo> model(psiReactionThermo::New(mesh));
    psiReactionThermo& thermo=model();
    IOdictionary input(IOobject("contactInput",runTime.constant(),mesh,IOobject::MUST_READ,IOobject::NO_WRITE));
    if(input.lookupOrDefault<Switch>("densityInversion",false))
    {
        volScalarField target(IOobject("rhoTarget","0",mesh,IOobject::MUST_READ,IOobject::NO_WRITE),mesh);
        scalarField low(mesh.nCells(),65),high(mesh.nCells(),1200);
        for(label iteration=0;iteration<48;++iteration)
        {
            forAll(low,i)thermo.T()[i]=.5*(low[i]+high[i]);
            thermo.T().boundaryFieldRef()[0] == thermo.T()[0];
            thermo.T().boundaryFieldRef()[1] == thermo.T()[mesh.nCells()-1];
            thermo.he() == thermo.he(thermo.p(),thermo.T());
            thermo.correct();
            const tmp<volScalarField> density=thermo.rho();
            forAll(low,i)
            {
                if(density()[i]>target[i])low[i]=thermo.T()[i];
                else high[i]=thermo.T()[i];
            }
        }
        const tmp<volScalarField> density=thermo.rho();
        scalar maximum=0;
        forAll(low,i)maximum=max(maximum,mag(density()[i]-target[i])/target[i]);
        Info<<"CONTACT_DENSITY_INITIALIZATION maxRelative="<<maximum<<endl;
        if(maximum>1e-8)FatalErrorInFunction<<"Density initialization failed"<<exit(FatalError);
        for(label patch=0;patch<2;++patch)
        {
            mixedFvPatchScalarField& boundary=refCast<mixedFvPatchScalarField>(thermo.T().boundaryFieldRef()[patch]);
            boundary.refValue()=thermo.T().boundaryField()[patch];
        }
    }
    thermo.T().write();thermo.he().write();
    volScalarField density(IOobject("rho","0",mesh,IOobject::NO_READ,IOobject::AUTO_WRITE),thermo.rho());
    density.write();
    std::ofstream out((runTime.path()/"initial-thermo.csv").c_str());
    out<<std::setprecision(17)<<"x,T,p,rho\n";
    forAll(density,i)out<<mesh.C()[i].x()<<','<<thermo.T()[i]<<','<<thermo.p()[i]<<','<<density[i]<<'\n';
    Info<<"CONTACT_INITIALIZATION_COMPLETE time=0"<<endl;
}
