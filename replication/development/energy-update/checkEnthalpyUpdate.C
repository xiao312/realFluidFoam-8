#include "fvCFD.H"
#include "CurrentSpeciesEnthalpy.H"
#include <fstream>
#include <iomanip>
using namespace Foam;

int main(int argc, char* argv[])
{
    argList::addBoolOption("legacy", "Check the unchanged library cache");
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    autoPtr<psiReactionThermo> thermo(psiReactionThermo::New(mesh));
    const bool legacy = args.optionFound("legacy");
    std::ofstream out((runTime.path()/(legacy?"legacy-enthalpy.csv":"refreshed-enthalpy.csv")).c_str());
    out << std::setprecision(17) << "stage,species,patch,cell,T_K,value_J_kg,expected_J_kg\n";
    label failures=0, samples=0;
    scalar maximumError=0;
    for (label stage=0; stage<3; ++stage)
    {
        if (stage)
        {
            volScalarField target(thermo->T());
            target += dimensionedScalar("increment", dimTemperature, stage==1?100:-50);
            thermo->he() = thermo->he(thermo->p(), target);
            thermo->correct();
        }
        forAll(thermo->composition().species(), species)
        {
            tmp<volScalarField> values = legacy ? thermo->hei(species)
                : currentSpeciesEnthalpy(thermo(), species);
            auto check = [&](label patch, label cell, scalar p, scalar T, scalar actual)
            {
                const scalar expected=thermo->composition().HE(species,p,T);
                const scalar error=mag(actual-expected);
                maximumError=max(maximumError,error);
                if (!std::isfinite(actual) || error>1e-6+1e-10*mag(expected)) ++failures;
                ++samples;
                out << stage << ',' << species << ',' << patch << ',' << cell << ','
                    << T << ',' << actual << ',' << expected << '\n';
            };
            forAll(thermo->T(), cell)
                check(-1,cell,thermo->p()[cell],thermo->T()[cell],values()[cell]);
            forAll(thermo->T().boundaryField(), patch)
                forAll(thermo->T().boundaryField()[patch], face)
                    check(patch,face,thermo->p().boundaryField()[patch][face],
                          thermo->T().boundaryField()[patch][face],values().boundaryField()[patch][face]);
        }
    }
    Info << "ENTHALPY_CHECK samples=" << samples << " failures=" << failures
         << " maxError_J_kg=" << maximumError << endl;
    return failures?1:0;
}
