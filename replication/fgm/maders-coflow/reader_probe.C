// Verify the actual OF8 table reader against independently generated physical nodes.
#include "fgmTableReader.H"
#include "IOstreams.H"
#include <fstream>
#include <cmath>
#include <algorithm>

int main(int argc, char** argv)
{
    if (argc != 3) return 2;
    Foam::fgm::fgmTableReader table(argv[1]);
    std::ifstream expected(argv[2]);
    int species = 0, nodes = 0;
    if (!(expected >> species >> nodes) || species < 1 || nodes < 1) return 3;
    double worst = 0;
    for (int node = 0; node < nodes; ++node)
    {
        double z, c, sc, q, t;
        if (!(expected >> z >> c >> sc >> q >> t)) return 4;
        Foam::scalarField y;
        Foam::scalar gotSc, gotQ, gotT;
        table.lookup(z, c, y, gotSc, gotQ, gotT);
        if (int(y.size()) != species) return 5;
        const double got[] = {gotSc, gotQ, gotT};
        const double reference[] = {sc, q, t};
        for (int k=0;k<3;++k)
        {
            const double error=std::abs(got[k]-reference[k])/std::max(1.,std::abs(reference[k]));
            if (!std::isfinite(error) || error > 1e-10) return 6;
            worst=std::max(worst,error);
        }
        if (std::abs(table.sourceOfC(gotSc)-sc) > 1e-10*std::max(1.,std::abs(sc))) return 7;
        for (int k=0;k<species;++k)
        {
            double value;
            if (!(expected >> value) || std::abs(y[k]-value) > 1e-12) return 8;
        }
    }
    Foam::Info<< "weighted-reader-physical-parity nodes=" << nodes
        << " species=" << species << " worstScaledError=" << worst << Foam::endl;
    return 0;
}
