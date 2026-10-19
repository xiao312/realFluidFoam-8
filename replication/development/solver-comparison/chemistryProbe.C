#include "fvCFD.H"
#include "psiReactionThermo.H"
#include "BasicChemistryModel.H"
#include <fstream>
#include <iomanip>

using namespace Foam;

int main(int argc, char *argv[])
{
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    autoPtr<psiReactionThermo> thermo(psiReactionThermo::New(mesh));
    autoPtr<BasicChemistryModel<psiReactionThermo>> chemistry
        (BasicChemistryModel<psiReactionThermo>::New(thermo()));
    const auto& names = thermo->composition().species();
    const auto& Y = thermo->composition().Y();
    const volScalarField rho(thermo->rho());
    const volScalarField cp(thermo->Cp());
    const volScalarField kappa(thermo->kappa());
    std::ofstream out((runTime.path()/"chemistry-probe.csv").c_str());
    out << std::setprecision(17);
    out << "state,interval_s,species,T_K,p_Pa,rho_kg_m3,Cp_J_kg_K,kappa_W_m_K,Y_initial,RR_kg_m3_s,Y_after\n";
    const scalar intervals[] = {0, 1e-9, 5e-9, 5e-8, 5e-7};
    for (const scalar dt : intervals)
    {
        if (dt == 0) chemistry->calculate();
        else chemistry->solve(dt);
        // solve() returns averaged RR without modifying the flow's T or Y.
        forAll(rho, cell)
        {
            forAll(names, species)
            {
                const scalar rate = chemistry->RR(species)[cell];
                out << cell << ',' << dt << ',' << names[species] << ','
                    << thermo->T()[cell] << ',' << thermo->p()[cell] << ','
                    << rho[cell] << ',' << cp[cell] << ',' << kappa[cell] << ','
                    << Y[species][cell] << ',' << rate << ','
                    << Y[species][cell]+dt*rate/rho[cell] << '\n';
            }
        }
    }
#ifdef NATIVE_THERMO
    // Independent cache check after chemistry measurements, on a disposable case.
    const scalarField initialT(thermo->T().primitiveField());
    List<scalarField> initialH(names.size());
    forAll(names, i) initialH[i] = thermo->hei(i)().primitiveField();
    volScalarField targetT(thermo->T());
    targetT += dimensionedScalar("increment", dimTemperature, 100);
    thermo->he() = thermo->he(thermo->p(), targetT);
    thermo->correct();
    std::ofstream cache((runTime.path()/"enthalpy-cache.csv").c_str());
    cache << std::setprecision(17);
    cache << "state,species,T_before_K,T_after_K,cached_before_J_kg,cached_after_J_kg,expected_after_J_kg\n";
    forAll(names, i)
    {
        tmp<volScalarField> values = thermo->hei(i);
        forAll(rho, cell)
        {
            cache << cell << ',' << names[i] << ',' << initialT[cell] << ','
                  << thermo->T()[cell] << ',' << initialH[i][cell] << ','
                  << values()[cell] << ',' << thermo->composition().HE
                     (i, thermo->p()[cell], thermo->T()[cell]) << '\n';
        }
    }
#endif
    Info << "End" << endl;
    return 0;
}
