#include "fgmTableReader.H"
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv)
{
    try
    {
        if (argc != 6 && argc != 7)
            throw std::invalid_argument("Usage: fgmSourceStepProbe TABLE Z RHO C DT [expect-event]");
        const bool expectEvent = argc == 7;
        if (expectEvent && std::string(argv[6]) != "expect-event")
            throw std::invalid_argument("Unknown probe mode");
        Foam::fgm::fgmTableReader table
        (
            Foam::fileName(argv[1]), Foam::fgm::fgmTableReader::ERROR_ON_BOUNDS
        );
        const double z = std::stod(argv[2]), rho = std::stod(argv[3]);
        const double oldC = std::stod(argv[4]), dt = std::stod(argv[5]);
        std::vector<double> coordinates, sources;
        table.sourceCurve(z, coordinates, sources);
        const auto direct = table.advanceSource(z, rho, oldC, dt);
        if (expectEvent)
        {
            if (!direct.outwardBoundary) throw std::runtime_error("Expected outward event was not observed");
            std::cout << std::setprecision(17) << "{\"expected_event\":true,\"C\":" << direct.progress
                      << ",\"elapsed\":" << direct.elapsed << ",\"requested\":" << dt << "}\n";
            return 0;
        }
        if (direct.outwardBoundary) throw std::runtime_error("Unexpected source coverage event");
        const double scale = std::max(1e-12, coordinates.back()-coordinates.front());
        const auto half = table.advanceSource(z, rho, oldC, .5*dt);
        if (half.outwardBoundary) throw std::runtime_error("First half reached source coverage boundary");
        const double rate = rho*(half.progress-oldC)/dt;
        const std::vector<double> originalCoordinates(coordinates), originalSources(sources);
        double maxDifference = 0;
        for (int outerCount = 1; outerCount <= 3; ++outerCount)
        {
            double candidate = oldC;
            for (int outer = 0; outer < outerCount; ++outer)
            {
                // Fresh Euler transport solve from the unchanged old state each outer.
                const double transported = (rho*oldC + dt*rate)/rho;
                const auto result = table.advanceSource(z, rho, transported, .5*dt);
                if (result.outwardBoundary) throw std::runtime_error("Second half reached source coverage boundary");
                candidate = result.progress;
            }
            maxDifference = std::max(maxDifference, std::abs(candidate-direct.progress)/scale);
        }
        if (coordinates != originalCoordinates || sources != originalSources)
            throw std::runtime_error("Source integration modified its input arrays");
        double lookupError = 0;
        for (std::size_t i = 0; i < coordinates.size(); ++i)
        {
            Foam::scalarField y;
            Foam::scalar sc, q, t;
            table.lookup(z, coordinates[i], y, sc, q, t);
            lookupError = std::max(lookupError, std::abs(sc-sources[i])/std::max(1.0,std::abs(sources[i])));
        }
        if (maxDifference > 1e-10 || lookupError > 1e-10)
            throw std::runtime_error("Source/transport restart or table source-curve mismatch");
        std::cout << std::setprecision(17) << "{\"C\":" << direct.progress
                  << ",\"dt\":" << dt << ",\"outer_counts\":[1,2,3],\"max_Cspan_error\":" << maxDifference
                  << ",\"lookup_error\":" << lookupError << ",\"immutable_inputs\":true}\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
