// Reuses the guarded initialization pattern from realFluidG2ThermoProbe.C.
// Uses the selected OF8 thermodynamics, not an external NASA implementation.
#include "fvCFD.H"
#include "psiReactionThermo.H"
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>

int main(int argc, char** argv)
{
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    if (runTime.value()!=0 || !std::getenv("SLURM_JOB_ID"))
        FatalErrorInFunction << "Initialization requires admitted fresh time-zero compute" << exit(FatalError);
    autoPtr<psiReactionThermo> model(psiReactionThermo::New(mesh));
    psiReactionThermo& thermo=model();
    if (thermo.type().find("smooke")==std::string::npos)
        FatalErrorInFunction << "Expected the selected Smooke thermodynamic package" << exit(FatalError);
    basicSpecieMixture& composition=thermo.composition();
    volScalarField chemical(IOobject("initChemicalEnthalpy",runTime.timeName(),mesh),mesh,
        dimensionedScalar("zero",dimEnergy/dimMass,0));
    forAll(composition.Y(),i)
        chemical+=dimensionedScalar("Hf",dimEnergy/dimMass,composition.Hf(i))*composition.Y()[i];
    volScalarField Ha(IOobject("Ha",runTime.timeName(),mesh,IOobject::MUST_READ,IOobject::AUTO_WRITE),mesh);
    Ha==thermo.he(thermo.p(),thermo.T())+chemical;
    const tmp<volScalarField> cp=thermo.Cp(),mu=thermo.mu(),kappa=thermo.kappa();
    scalar worstMu=0,worstKappa=0;
    forAll(Ha,i)
    {
        const scalar t=thermo.T()[i];
        const scalar expectedMu=1.67e-8*cp()[i]*std::pow(t/298.,.51);
        const scalar expectedKappa=2.58e-5*cp()[i]*std::pow(t/298.,.69);
        if(!std::isfinite(Ha[i]) || !std::isfinite(mu()[i]) || !std::isfinite(kappa()[i]) || !(expectedMu>0) || !(expectedKappa>0))
            FatalErrorInFunction << "Invalid physical initialization state" << exit(FatalError);
        worstMu=max(worstMu,mag(mu()[i]/expectedMu-1));
        worstKappa=max(worstKappa,mag(kappa()[i]/expectedKappa-1));
    }
    if(worstMu>1e-12 || worstKappa>1e-12)
        FatalErrorInFunction << "Selected transport differs from declared Smooke functions" << exit(FatalError);
    if(!Ha.write())FatalErrorInFunction << "Failed to write Ha" << exit(FatalError);
    IOdictionary marker(IOobject("fgmHaInitialization",runTime.constant(),mesh,IOobject::NO_READ,IOobject::AUTO_WRITE));
    marker.add("preparedTime",scalar(0));
    marker.add("preparedRank",Pstream::myProcNo());
    marker.add("preparedRanks",Pstream::nProcs());
    marker.add("thermoType",thermo.subDict("thermoType"));
    if(!marker.regIOobject::write())FatalErrorInFunction << "Failed to write initialization marker" << exit(FatalError);
    std::ofstream report((runTime.path()/"maders-runtime-initialization.csv").c_str());
    report<<std::setprecision(17)<<"cells,Tmin_K,Tmax_K,HaMin_J_kg,HaMax_J_kg,muMaxRelativeError,kappaMaxRelativeError\n"
        <<Ha.size()<<','<<min(thermo.T()).value()<<','<<max(thermo.T()).value()<<','
        <<min(Ha).value()<<','<<max(Ha).value()<<','<<worstMu<<','<<worstKappa<<'\n';
    report.close();
    if(!report)return 3;
    Info<<"Maders runtime Ha and Smooke initialization verified at timezero"<<endl;
    return 0;
}
