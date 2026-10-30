#include "source_ode.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char** argv)
{
    try
    {
        if (argc != 5)
            throw std::invalid_argument("Usage: source_ode_probe SOURCE_CSV DENSITY INITIAL_C DURATION");
        std::ifstream input(argv[1]);
        if (!input) throw std::runtime_error("Cannot open source CSV");
        std::string line;
        std::getline(input, line);
        if (line.find("C,eta,Sc_kg_m3_s,") != 0)
            throw std::runtime_error("CSV header differs from the source_ode.py contract");
        std::vector<double> progress, source;
        while (std::getline(input, line))
        {
            if (line.empty()) continue;
            std::stringstream row(line);
            std::string c, eta, sc;
            if (!std::getline(row, c, ',') || !std::getline(row, eta, ',') || !std::getline(row, sc, ','))
                throw std::runtime_error("Incomplete source CSV row");
            progress.push_back(std::stod(c));
            source.push_back(std::stod(sc));
        }
        const forgeFgm::FixedStateSource model(progress, source);
        const auto result = model.advance(std::stod(argv[2]), std::stod(argv[3]), std::stod(argv[4]));
        std::cout << std::setprecision(17) << "{\"C\":" << result.progress
                  << ",\"elapsed_s\":" << result.elapsed << ",\"segments\":" << result.crossedSegments
                  << ",\"outward_boundary\":" << (result.outwardBoundary ? "true" : "false") << "}\n";
        return result.outwardBoundary ? 5 : 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
