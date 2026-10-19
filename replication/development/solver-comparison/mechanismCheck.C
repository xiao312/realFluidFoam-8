#include "cantera/base/Solution.h"
#include "cantera/thermo/ThermoPhase.h"
#include "cantera/kinetics/Kinetics.h"
#include <iostream>
int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    auto solution = Cantera::newSolution(argv[1], "");
    auto gas = solution->thermo();
    gas->setState_TPX(298, 10132500, "CH4:1.1, O2:2, N2:7.523809523809524");
    std::cout.precision(17);
    std::cout << gas->nSpecies() << ' ' << solution->kinetics()->nReactions()
              << ' ' << gas->density() << ' ' << gas->cp_mass() << '\n';
    return (gas->nSpecies() == 53 && solution->kinetics()->nReactions() == 325) ? 0 : 1;
}
