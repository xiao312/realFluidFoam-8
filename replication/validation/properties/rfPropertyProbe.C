// Evaluate the actual registered library, including its enthalpy inversion.
#include "fvCFD.H"
#include "psiReactionThermo.H"
#include <fstream>
#include <iomanip>
#include <cmath>

int main(int argc, char *argv[])
{
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    autoPtr<psiReactionThermo> model(psiReactionThermo::New(mesh));
    psiReactionThermo& thermo = model();
    std::ofstream output((runTime.path()/"properties.csv").c_str());
    output << std::setprecision(16)
        << "p_atm,T_requested_K,T_K,rho_kg_m3,Cp_J_kg_K,mu_Pa_s,kappa_W_m_K,he_J_kg,inversion_relative_error\n";
    const scalar pressures[] = {1, 50, 100, 200, 300};
    for (const scalar pressure : pressures)
    {
        for (label temperature = 180; temperature <= 620; temperature += 10)
        {
            thermo.p() = dimensionedScalar("p", dimPressure, pressure*101325.0);
            thermo.T() = dimensionedScalar("T", dimTemperature, temperature);
            thermo.he() = thermo.he(thermo.p(), thermo.T());
            // Force a nontrivial inversion instead of providing the exact answer.
            thermo.T().primitiveFieldRef() = scalar(temperature + 0.5);
            thermo.correct();
            const scalar T = thermo.T()[0];
            const scalar rho = thermo.rho()()[0];
            const scalar cp = thermo.Cp()()[0];
            const scalar mu = thermo.mu()()[0];
            const scalar kappa = thermo.kappa()()[0];
            const scalar error = mag(T-temperature)/temperature;
            if (!std::isfinite(rho+cp+mu+kappa+T) || min(rho,min(cp,min(mu,kappa))) <= 0 || error > 1e-6)
            {
                FatalErrorInFunction << "Invalid property/inversion at "
                    << pressure << " atm, " << temperature << " K" << exit(FatalError);
            }
            output << pressure << ',' << temperature << ',' << T << ',' << rho
                << ',' << cp << ',' << mu << ',' << kappa << ',' << thermo.he()[0]
                << ',' << error << '\n';
        }
    }
    output.close();
    if (!output) return 1;
    Info << "PASS: 225 finite property states and enthalpy inversions" << nl;
    return 0;
}
