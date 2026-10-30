// Small executable verification of the actual C++ reader. Run after building
// against the frozen custom combustion library; not physical flame evidence.
#include "fgmTableReader.H"
#include "IOstreams.H"
#include <cmath>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 4) return 2; // MODE V1_TABLE V2_TABLE
    const std::string mode(argv[1]);
    Foam::scalarField Y;
    Foam::scalar Sc, Q, T;
    if (mode == "negative")
    {
        Foam::fgm::fgmTableReader table(argv[3]);
        table.lookup(0, 0.001, Y, Sc, Q, T);
        return 3; // Strict zero-span refusal must have terminated first.
    }
    if (mode != "positive") return 2;
    Foam::fgm::fgmTableReader legacy(argv[2]);
    legacy.lookup(0.5, 0.5, Y, Sc, Q, T);
    if (std::abs(Y[0] - 0.4) > 1e-12 || std::abs(legacy.sourceOfC(Sc) - 3500) > 1e-10) return 4;
    Foam::fgm::fgmTableReader mapped(argv[3]);
    mapped.lookup(0.25, 0.125, Y, Sc, Q, T);
    if (std::abs(Y[0] - 0.125) > 1e-12 || std::abs(mapped.sourceOfC(Sc) - 0.05) > 1e-12) return 5;
    mapped.lookup(0, 0, Y, Sc, Q, T);
    if (Y[0] != 0 || Sc != 0) return 6;
    Foam::fgm::fgmTableReader clipped(argv[3], Foam::fgm::fgmTableReader::CLAMP_TO_BOUNDS);
    clipped.lookup(0.25, 0.3, Y, Sc, Q, T);
    if (std::abs(Y[0] - 0.25) > 1e-12 || clipped.clipCount() != 1
        || std::abs(clipped.maxProgressExcursion() - 0.05) > 1e-12) return 7;
    Foam::Info<< "reader-v1-v2-positive-ok: legacy, raw-source, zero-span, counted-clipping" << Foam::endl;
    return 0;
}
