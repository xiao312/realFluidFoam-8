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
    Info << "End" << endl;
    return 0;
}
